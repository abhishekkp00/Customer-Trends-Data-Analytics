"""Dynamic business insights derived from the *filtered* data.

Nothing here is hardcoded: every number in an insight is computed from the
DataFrame passed in. When the data cannot support a finding the function
returns an Insight with ``supported=False`` and a clear message.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import pandas as pd

from analytics import metrics
from config import settings

NO_CAUSATION = (
    "This is an observed association in recorded data, not proof of cause and effect."
)
NO_DATES = "The data has no transaction dates, so no time trends can be assessed."


@dataclass
class Insight:
    title: str
    supported: bool
    finding: str = ""        # 1. What the data shows
    metric: str = ""         # 2. Relevant metric and comparison
    why_it_matters: str = "" # 3. Why a stakeholder should care
    recommendation: str = "" # 4. Practical recommendation
    caveat: str = ""         # 5. Limitation
    message: str = ""        # shown when not supported


def _unsupported(title: str, reason: str) -> Insight:
    return Insight(title=title, supported=False, message=reason)


def _money(x: float) -> str:
    return f"${x:,.0f}"


def _eligible(summary: pd.DataFrame, min_size: int) -> pd.DataFrame:
    return summary[summary["records"] >= min_size]


def _insufficient(df: pd.DataFrame) -> bool:
    return len(df) < settings.MIN_RECORDS_FOR_INSIGHT


def _insufficient_msg(df: pd.DataFrame) -> str:
    return (f"Only {len(df):,} records match the current filters; at least "
            f"{settings.MIN_RECORDS_FOR_INSIGHT} are needed to state a reliable finding.")


# --------------------------------------------------------------------------- #
def highest_spending_segment(df: pd.DataFrame) -> Insight:
    title = "Highest-spending customer segment"
    if _insufficient(df):
        return _unsupported(title, _insufficient_msg(df))
    seg = _eligible(metrics.segment_summary(df), settings.MIN_GROUP_SIZE)
    if len(seg) < 2:
        return _unsupported(title, "At least two customer segments with enough records are needed for a comparison.")
    top = seg.sort_values("avg_amount", ascending=False).iloc[0]
    low = seg.sort_values("avg_amount", ascending=True).iloc[0]
    overall = df["purchase_amount"].mean()
    diff_pct = metrics.pct(top["avg_amount"] - low["avg_amount"], low["avg_amount"])
    return Insight(
        title=title, supported=True,
        finding=f"The **{top['customer_segment']}** segment has the highest average purchase amount per record.",
        metric=(f"{_money(top['avg_amount'])} vs {_money(overall)} overall average and "
                f"{_money(low['avg_amount'])} for the lowest segment ({low['customer_segment']})"
                + (f" - a {diff_pct:+.1f}% gap." if diff_pct is not None else ".")),
        why_it_matters="Knowing which engagement tier spends most shows where retention effort pays back.",
        recommendation=("If the gap is material, test loyalty or early-engagement offers aimed at "
                        "moving customers toward the higher-spending tier."),
        caveat=(f"Segments are based on 'previous purchases' ({settings.SEGMENT_RULES['New']}; "
                f"{settings.SEGMENT_RULES['Returning']}; {settings.SEGMENT_RULES['Loyal']}). "
                "'New' means a short recorded history, not a first-time buyer. " + NO_CAUSATION),
    )


def most_popular_category(df: pd.DataFrame) -> Insight:
    title = "Most popular product category"
    if _insufficient(df):
        return _unsupported(title, _insufficient_msg(df))
    cat = metrics.category_summary(df)
    if cat.empty:
        return _unsupported(title, "No category data for the current selection.")
    top = cat.sort_values("records", ascending=False).iloc[0]
    share = metrics.pct(top["records"], cat["records"].sum())
    top_rev = cat.sort_values("total_amount", ascending=False).iloc[0]
    same = top_rev["category"] == top["category"]
    return Insight(
        title=title, supported=True,
        finding=f"**{top['category']}** has the most purchase records.",
        metric=(f"{int(top['records']):,} records ({share:.1f}% of all records); it "
                + ("also leads in total purchase amount " if same else
                   f"is not the top earner - {top_rev['category']} leads in purchase amount ")
                + f"({_money(top['total_amount'])} for {top['category']}, "
                  f"{_money(top_rev['total_amount'])} for {top_rev['category']})."),
        why_it_matters="Popular categories drive traffic and inventory pressure.",
        recommendation=("Prioritise stock availability and merchandising for this category; use it "
                        "as an anchor for cross-selling to lower-volume categories."),
        caveat="Counts reflect recorded purchases, not browsing or demand. " + NO_DATES,
    )


def top_rated_product(df: pd.DataFrame) -> Insight:
    title = "Highest-rated product"
    if _insufficient(df):
        return _unsupported(title, _insufficient_msg(df))
    prod = _eligible(metrics.product_summary(df), settings.MIN_GROUP_SIZE).dropna(subset=["avg_rating"])
    if len(prod) < 2:
        return _unsupported(title, f"Need at least two products with {settings.MIN_GROUP_SIZE}+ records to rank ratings.")
    top = prod.sort_values(["avg_rating", "records"], ascending=False).iloc[0]
    overall = df["review_rating"].mean()
    return Insight(
        title=title, supported=True,
        finding=f"**{top['item_purchased']}** ({top['category']}) has the highest average review rating among products with {settings.MIN_GROUP_SIZE}+ records.",
        metric=f"{top['avg_rating']:.2f} / 5 over {int(top['records']):,} records vs {overall:.2f} overall average.",
        why_it_matters="High-rated products are natural candidates for promotion and bundling.",
        recommendation="Feature this product in campaigns and study what makes it well-received.",
        caveat=("Ratings differences are often small (check the gap before acting) and the rating "
                "is per purchase record. " + NO_CAUSATION),
    )


def highest_discount_category(df: pd.DataFrame) -> Insight:
    title = "Category with the highest discount usage"
    if _insufficient(df):
        return _unsupported(title, _insufficient_msg(df))
    d = metrics.discount_rate_by(df, "category", min_records=settings.MIN_GROUP_SIZE)
    if len(d) < 2:
        return _unsupported(title, "At least two categories with enough records are needed.")
    top, low = d.iloc[0], d.iloc[-1]
    overall = metrics.yes_rate(df["discount_applied"])
    return Insight(
        title=title, supported=True,
        finding=f"**{top['category']}** records the highest share of discounted purchases.",
        metric=(f"{top['discount_rate_pct']:.1f}% of its {int(top['records']):,} records used a discount, "
                f"vs {overall:.1f}% overall and {low['discount_rate_pct']:.1f}% for {low['category']}."),
        why_it_matters="High discount dependence can erode margin if full-price demand exists.",
        recommendation="Review whether discounts in this category are needed, and test targeted rather than blanket offers.",
        caveat="Margins and prices before discount are not in the data. " + NO_CAUSATION,
    )


def subscriber_spend_gap(df: pd.DataFrame) -> Insight:
    title = "Subscribers vs non-subscribers"
    if _insufficient(df):
        return _unsupported(title, _insufficient_msg(df))
    s = metrics.subscription_summary(df).set_index("subscription_status")
    if not {"Yes", "No"} <= set(s.index) or (s.loc[["Yes", "No"], "records"] < settings.MIN_GROUP_SIZE).any():
        return _unsupported(title, "Both subscribers and non-subscribers (with enough records) are needed.")
    yes, no = s.loc["Yes", "avg_amount"], s.loc["No", "avg_amount"]
    diff = yes - no
    rel = metrics.pct(diff, no)
    direction = "higher" if diff > 0 else "lower" if diff < 0 else "the same"
    ratio_note = "" if rel is None else f" ({rel:+.1f}%)"
    return Insight(
        title=title, supported=True,
        finding=f"Subscribers' average purchase amount is {direction} than non-subscribers'.",
        metric=(f"{_money(yes)} (subscribers, n={int(s.loc['Yes','records']):,}) vs "
                f"{_money(no)} (non-subscribers, n={int(s.loc['No','records']):,}); "
                f"difference {diff:+,.2f} USD{ratio_note}."),
        why_it_matters="Shows whether the subscription programme is associated with higher basket value.",
        recommendation=("If the difference is meaningful, subscriber value and retention benefits can justify "
                        "promoting sign-ups; if negligible, judge the programme on retention rather than basket size."),
        caveat="Subscribers may differ from others in many ways, so this does not show subscription raises spend. " + NO_CAUSATION,
    )


def top_payment_method(df: pd.DataFrame) -> Insight:
    title = "Most frequently used payment method"
    if _insufficient(df):
        return _unsupported(title, _insufficient_msg(df))
    p = metrics.payment_summary(df)
    if p.empty:
        return _unsupported(title, "No payment data for the current selection.")
    top = p.iloc[0]
    share = metrics.pct(top["records"], p["records"].sum())
    runner = p.iloc[1] if len(p) > 1 else None
    extra = f"; next is {runner['payment_method']} at {metrics.pct(runner['records'], p['records'].sum()):.1f}%" if runner is not None else ""
    return Insight(
        title=title, supported=True,
        finding=f"**{top['payment_method']}** is the most used payment method.",
        metric=f"{int(top['records']):,} records, {share:.1f}% of the total{extra}.",
        why_it_matters="Payment friction affects checkout completion and processing cost.",
        recommendation="Make sure this method is fast and reliable at checkout; review fees on the most-used methods.",
        caveat="Differences between methods can be small; a leader is not necessarily a strong preference.",
    )


def top_shipping_option(df: pd.DataFrame) -> Insight:
    title = "Most common shipping option"
    if _insufficient(df):
        return _unsupported(title, _insufficient_msg(df))
    s = metrics.shipping_summary(df)
    if s.empty:
        return _unsupported(title, "No shipping data for the current selection.")
    top = s.iloc[0]
    share = metrics.pct(top["records"], s["records"].sum())
    best_avg = s.sort_values("avg_amount", ascending=False).iloc[0]
    return Insight(
        title=title, supported=True,
        finding=f"**{top['shipping_type']}** has the most records.",
        metric=(f"{int(top['records']):,} records ({share:.1f}%). Highest average purchase amount: "
                f"{best_avg['shipping_type']} at {_money(best_avg['avg_amount'])}."),
        why_it_matters="Shipping preferences shape logistics cost and customer experience.",
        recommendation="Align carrier capacity and delivery promises with the most-chosen option.",
        caveat="Shipping cost, delivery time and satisfaction are not in the data.",
    )


INSIGHT_BUILDERS: list[Callable[[pd.DataFrame], Insight]] = [
    highest_spending_segment,
    most_popular_category,
    top_rated_product,
    highest_discount_category,
    subscriber_spend_gap,
    top_payment_method,
    top_shipping_option,
]


def generate_insights(df: pd.DataFrame) -> list[Insight]:
    """Run every insight builder on the filtered data."""
    return [build(df) for build in INSIGHT_BUILDERS]
