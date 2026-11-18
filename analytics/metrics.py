"""Pure analytics functions. Every function takes a (filtered) DataFrame and
returns plain numbers or DataFrames; none touches the database, Streamlit or
Plotly.

Terminology
-----------
* record: one row of the table (a recorded purchase).
* customer: a distinct ``customer_id``.
* purchase amount: ``purchase_amount`` in USD as recorded.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import settings

KPI_NAMES = (
    "total_purchase_amount", "total_records", "unique_customers",
    "avg_purchase_per_record", "avg_spend_per_customer", "avg_age",
    "avg_rating", "subscription_rate", "discount_rate",
)
PRODUCT_RANK_METRICS = {"records", "total_amount", "avg_amount", "avg_rating"}


def safe_divide(numerator: float, denominator: float) -> float | None:
    """Return numerator / denominator, or None when the denominator is 0 or NaN."""
    if denominator is None or pd.isna(denominator) or denominator == 0:
        return None
    return float(numerator) / float(denominator)


def pct(part: float, whole: float) -> float | None:
    """Percentage (0-100) with a safe denominator."""
    ratio = safe_divide(part, whole)
    return None if ratio is None else ratio * 100.0


def yes_rate(series: pd.Series) -> float | None:
    """Share of 'Yes' values among non-null entries, as a percentage."""
    valid = series.dropna()
    return pct((valid == "Yes").sum(), len(valid))


def _mean_or_none(series: pd.Series) -> float | None:
    values = series.dropna()
    return float(values.mean()) if len(values) else None


def compute_kpis(df: pd.DataFrame) -> dict[str, float | None]:
    """Headline KPIs. Values are None when they cannot be computed."""
    record_count = len(df)
    if record_count == 0:
        return {name: None for name in KPI_NAMES} | {"total_records": 0, "unique_customers": 0}

    total = float(df["purchase_amount"].sum())
    unique_customers = int(df["customer_id"].nunique())
    return {
        "total_purchase_amount": total,
        "total_records": record_count,
        "unique_customers": unique_customers,
        "avg_purchase_per_record": safe_divide(total, record_count),
        "avg_spend_per_customer": safe_divide(total, unique_customers),
        "avg_age": _mean_or_none(df["age"]),
        "avg_rating": _mean_or_none(df["review_rating"]),
        "subscription_rate": yes_rate(df["subscription_status"]),
        "discount_rate": yes_rate(df["discount_applied"]),
    }


def group_summary(df: pd.DataFrame, by: str | list[str]) -> pd.DataFrame:
    """Records, customers, total/avg purchase amount, avg rating and share of total."""
    if df.empty:
        group_columns = [by] if isinstance(by, str) else list(by)
        return pd.DataFrame(columns=group_columns + [
            "records", "customers", "total_amount", "avg_amount", "avg_rating", "share_of_amount_pct"])
    summary = df.groupby(by, observed=True, dropna=False).agg(
        records=("customer_id", "size"),
        customers=("customer_id", "nunique"),
        total_amount=("purchase_amount", "sum"),
        avg_amount=("purchase_amount", "mean"),
        avg_rating=("review_rating", "mean"),
    ).reset_index()
    total = summary["total_amount"].sum()
    summary["share_of_amount_pct"] = (summary["total_amount"] / total * 100) if total else np.nan
    return summary


def _in_canonical_order(summary: pd.DataFrame, column: str, order: list[str]) -> pd.DataFrame:
    """Sort rows by a canonical label order (unknown labels go last)."""
    rank = {label: i for i, label in enumerate(order)}
    sort_key = summary[column].map(rank).fillna(len(order))
    return summary.assign(_order=sort_key).sort_values("_order").drop(columns="_order")


def age_group_summary(df: pd.DataFrame) -> pd.DataFrame:
    return _in_canonical_order(group_summary(df, "age_group"), "age_group", settings.AGE_GROUP_ORDER)


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
    return _in_canonical_order(group_summary(df, "customer_segment"), "customer_segment", settings.SEGMENT_ORDER)


def shipping_summary(df: pd.DataFrame) -> pd.DataFrame:
    return group_summary(df, "shipping_type").sort_values("records", ascending=False)


def payment_summary(df: pd.DataFrame) -> pd.DataFrame:
    return group_summary(df, "payment_method").sort_values("records", ascending=False)


def frequency_summary(df: pd.DataFrame) -> pd.DataFrame:
    return _in_canonical_order(
        group_summary(df, "frequency_of_purchases"), "frequency_of_purchases", settings.FREQUENCY_ORDER)


def discount_status_summary(df: pd.DataFrame) -> pd.DataFrame:
    return group_summary(df, "discount_applied").sort_values("discount_applied", ascending=False)


def payment_shipping_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Record counts for every payment method x shipping type pair."""
    if df.empty:
        return pd.DataFrame()
    return df.pivot_table(index="payment_method", columns="shipping_type",
                          values="customer_id", aggfunc="count", observed=True)


def _yes_rate_by(df: pd.DataFrame, by: str, flag_column: str,
                 yes_count_name: str, rate_name: str) -> pd.DataFrame:
    """Records, count of 'Yes' flags and 'Yes' rate (%) per group.

    The denominator is the group's own record count.
    """
    if df.empty:
        return pd.DataFrame(columns=[by, "records", yes_count_name, rate_name])
    summary = df.groupby(by, observed=True).agg(
        records=("customer_id", "size"),
        **{yes_count_name: (flag_column, lambda s: int((s == "Yes").sum()))},
    ).reset_index()
    summary[rate_name] = summary[yes_count_name] / summary["records"] * 100
    return summary


def discount_rate_by(df: pd.DataFrame, by: str, min_records: int = 1) -> pd.DataFrame:
    """Share of records with a discount applied per group, sorted by rate (descending)."""
    summary = _yes_rate_by(df, by, "discount_applied", "discounted_records", "discount_rate_pct")
    summary = summary[summary["records"] >= min_records]
    return summary.sort_values(["discount_rate_pct", "records"], ascending=[False, False]).reset_index(drop=True)


def subscription_by_segment(df: pd.DataFrame) -> pd.DataFrame:
    """Subscription rate (%) and records per customer segment."""
    summary = _yes_rate_by(df, "customer_segment", "subscription_status", "subscribed", "subscription_rate_pct")
    return _in_canonical_order(summary, "customer_segment", settings.SEGMENT_ORDER)


def top_products(df: pd.DataFrame, metric: str = "records", n: int = 10,
                 min_records: int = 1) -> pd.DataFrame:
    """Rank products by ``records``, ``total_amount``, ``avg_amount`` or ``avg_rating``."""
    if metric not in PRODUCT_RANK_METRICS:
        raise ValueError(f"metric must be one of {sorted(PRODUCT_RANK_METRICS)}")
    summary = product_summary(df)
    summary = summary[summary["records"] >= min_records]
    return summary.sort_values([metric, "records"], ascending=[False, False]).head(n).reset_index(drop=True)


def top_products_per_category(df: pd.DataFrame, n: int = 3) -> pd.DataFrame:
    """Top-N products by record count within each category (mirrors SQL Q8)."""
    summary = product_summary(df)
    if summary.empty:
        return summary.assign(rank=pd.Series(dtype=int))
    summary = summary.sort_values(["category", "records", "item_purchased"], ascending=[True, False, True])
    summary["rank"] = summary.groupby("category").cumcount() + 1
    return summary[summary["rank"] <= n].reset_index(drop=True)
