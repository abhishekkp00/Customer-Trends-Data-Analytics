"""Pure, testable analytics functions. Every function takes a (filtered)
DataFrame and returns plain numbers / DataFrames; none touches the database
or Streamlit.

Terminology used throughout
---------------------------
* *record*    - one row of the table (a recorded purchase).
* *customer*  - a distinct ``customer_id``.
* *purchase amount* - ``purchase_amount`` in USD as recorded.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from config import settings


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def safe_divide(numerator: float, denominator: float) -> Optional[float]:
    """Return numerator/denominator, or None when the denominator is 0/NaN."""
    if denominator is None or pd.isna(denominator) or denominator == 0:
        return None
    return float(numerator) / float(denominator)


def pct(part: float, whole: float) -> Optional[float]:
    """Percentage (0-100) with a safe denominator."""
    ratio = safe_divide(part, whole)
    return None if ratio is None else ratio * 100.0


def yes_rate(series: pd.Series) -> Optional[float]:
    """Share of 'Yes' values among non-null entries, as a percentage."""
    valid = series.dropna()
    return pct((valid == "Yes").sum(), len(valid))


# --------------------------------------------------------------------------- #
# KPIs
# --------------------------------------------------------------------------- #
def compute_kpis(df: pd.DataFrame) -> dict[str, Optional[float]]:
    """Headline KPIs. Values are None when they cannot be computed."""
    n = len(df)
    if n == 0:
        return {k: None for k in (
            "total_purchase_amount", "total_records", "unique_customers",
            "avg_purchase_per_record", "avg_spend_per_customer", "avg_age",
            "avg_rating", "subscription_rate", "discount_rate")} | {"total_records": 0, "unique_customers": 0}

    total = float(df["purchase_amount"].sum())
    unique_customers = int(df["customer_id"].nunique())
    return {
        "total_purchase_amount": total,
        "total_records": n,
        "unique_customers": unique_customers,
        "avg_purchase_per_record": safe_divide(total, n),
        # Spend per distinct customer; differs from per-record only if IDs repeat.
        "avg_spend_per_customer": safe_divide(total, unique_customers),
        "avg_age": _mean_or_none(df["age"]),
        "avg_rating": _mean_or_none(df["review_rating"]),
        "subscription_rate": yes_rate(df["subscription_status"]),
        "discount_rate": yes_rate(df["discount_applied"]),
    }


def _mean_or_none(s: pd.Series) -> Optional[float]:
    s = s.dropna()
    return float(s.mean()) if len(s) else None


# --------------------------------------------------------------------------- #
# Generic group summaries
# --------------------------------------------------------------------------- #
def group_summary(df: pd.DataFrame, by: str | list[str]) -> pd.DataFrame:
    """Records, customers, total/avg purchase amount and share of total."""
    if df.empty:
        cols = ([by] if isinstance(by, str) else list(by)) + [
            "records", "customers", "total_amount", "avg_amount", "avg_rating", "share_of_amount_pct"]
        return pd.DataFrame(columns=cols)
    g = df.groupby(by, observed=True, dropna=False).agg(
        records=("customer_id", "size"),
        customers=("customer_id", "nunique"),
        total_amount=("purchase_amount", "sum"),
        avg_amount=("purchase_amount", "mean"),
        avg_rating=("review_rating", "mean"),
    ).reset_index()
    total = g["total_amount"].sum()
    g["share_of_amount_pct"] = (g["total_amount"] / total * 100) if total else np.nan
    return g


def _ordered(df: pd.DataFrame, col: str, order: list[str]) -> pd.DataFrame:
    """Sort rows by a canonical category order (unknown labels go last)."""
    rank = {v: i for i, v in enumerate(order)}
    return df.assign(_o=df[col].map(rank).fillna(len(order))).sort_values("_o").drop(columns="_o")


def age_group_summary(df: pd.DataFrame) -> pd.DataFrame:
    return _ordered(group_summary(df, "age_group"), "age_group", settings.AGE_GROUP_ORDER)


def gender_summary(df: pd.DataFrame) -> pd.DataFrame:
    return group_summary(df, "gender").sort_values("records", ascending=False)


def location_summary(df: pd.DataFrame) -> pd.DataFrame:
    return group_summary(df, "location").sort_values("customers", ascending=False)


def category_summary(df: pd.DataFrame) -> pd.DataFrame:
    return group_summary(df, "category").sort_values("total_amount", ascending=False)


def product_summary(df: pd.DataFrame) -> pd.DataFrame:
    return group_summary(df, ["category", "item_purchased"]).sort_values("records", ascending=False)


def subscription_summary(df: pd.DataFrame) -> pd.DataFrame:
    return group_summary(df, "subscription_status").sort_values("subscription_status", ascending=False)


def segment_summary(df: pd.DataFrame) -> pd.DataFrame:
    return _ordered(group_summary(df, "customer_segment"), "customer_segment", settings.SEGMENT_ORDER)


def shipping_summary(df: pd.DataFrame) -> pd.DataFrame:
    return group_summary(df, "shipping_type").sort_values("records", ascending=False)


def payment_summary(df: pd.DataFrame) -> pd.DataFrame:
    return group_summary(df, "payment_method").sort_values("records", ascending=False)


def frequency_summary(df: pd.DataFrame) -> pd.DataFrame:
    return _ordered(group_summary(df, "frequency_of_purchases"),
                    "frequency_of_purchases", settings.FREQUENCY_ORDER)


def discount_status_summary(df: pd.DataFrame) -> pd.DataFrame:
    return group_summary(df, "discount_applied").sort_values("discount_applied", ascending=False)


# --------------------------------------------------------------------------- #
# Discount analysis
# --------------------------------------------------------------------------- #
def discount_rate_by(df: pd.DataFrame, by: str, min_records: int = 1) -> pd.DataFrame:
    """Share of records with a discount applied, per group (denominator =
    the group's own record count). Sorted by rate, descending."""
    if df.empty:
        return pd.DataFrame(columns=[by, "records", "discounted_records", "discount_rate_pct"])
    g = df.groupby(by, observed=True).agg(
        records=("customer_id", "size"),
        discounted_records=("discount_applied", lambda s: int((s == "Yes").sum())),
    ).reset_index()
    g["discount_rate_pct"] = g["discounted_records"] / g["records"] * 100
    g = g[g["records"] >= min_records]
    return g.sort_values(["discount_rate_pct", "records"], ascending=[False, False]).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Products
# --------------------------------------------------------------------------- #
def top_products(df: pd.DataFrame, metric: str = "records", n: int = 10,
                 min_records: int = 1) -> pd.DataFrame:
    """Rank products by ``records``, ``total_amount``, ``avg_amount`` or ``avg_rating``."""
    allowed = {"records", "total_amount", "avg_amount", "avg_rating"}
    if metric not in allowed:
        raise ValueError(f"metric must be one of {sorted(allowed)}")
    s = product_summary(df)
    s = s[s["records"] >= min_records]
    return s.sort_values([metric, "records"], ascending=[False, False]).head(n).reset_index(drop=True)


def top_products_per_category(df: pd.DataFrame, n: int = 3) -> pd.DataFrame:
    """Top-N products by record count within each category (mirrors SQL Q8)."""
    s = product_summary(df)
    if s.empty:
        return s.assign(rank=pd.Series(dtype=int))
    s = s.sort_values(["category", "records", "item_purchased"], ascending=[True, False, True])
    s["rank"] = s.groupby("category").cumcount() + 1
    return s[s["rank"] <= n].reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Cross-tabs for heatmaps
# --------------------------------------------------------------------------- #
def pivot_avg(df: pd.DataFrame, index: str, columns: str, values: str = "purchase_amount") -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    return df.pivot_table(index=index, columns=columns, values=values, aggfunc="mean", observed=True)


def subscription_by_segment(df: pd.DataFrame) -> pd.DataFrame:
    """Subscription rate (%) and records per customer segment."""
    if df.empty:
        return pd.DataFrame(columns=["customer_segment", "records", "subscription_rate_pct"])
    g = df.groupby("customer_segment", observed=True).agg(
        records=("customer_id", "size"),
        subscribed=("subscription_status", lambda s: int((s == "Yes").sum())),
    ).reset_index()
    g["subscription_rate_pct"] = g["subscribed"] / g["records"] * 100
    return _ordered(g, "customer_segment", settings.SEGMENT_ORDER)
