"""Discounts tab: usage, spend comparison and discount dependence."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from analytics import metrics
from components import charts
from components.kpi_cards import fmt_int, fmt_money
from config import settings
from dashboard.styles import show_finding


def render(df: pd.DataFrame) -> None:
    st.caption("Discount and promo-code fields were identical in the source data, so only discount status is "
               "analysed. Comparisons below are associations, not proof that discounts change spending.")
    status = metrics.discount_status_summary(df)
    left, right = st.columns(2)
    charts.show_chart(
        charts.donut(status, "discount_applied", "records", "Share of records with a discount", "Records"),
        "discounts_donut", left)
    charts.show_chart(
        charts.box(df, "discount_applied", "purchase_amount", "Purchase amount: discounted vs not",
                   "Discount applied", "Purchase amount (USD)", prefix="$"),
        "discounts_amount_box", right)
    if {"Yes", "No"} <= set(status["discount_applied"]):
        by_status = status.set_index("discount_applied")
        show_finding(
            f"Average purchase per record: {fmt_money(by_status.loc['Yes', 'avg_amount'], 2)} with a discount vs "
            f"{fmt_money(by_status.loc['No', 'avg_amount'], 2)} without. Discounts may have been offered "
            "selectively, so this does not show a causal effect.")

    by_category = metrics.discount_rate_by(df, "category", 1)
    left, right = st.columns(2)
    charts.show_chart(
        charts.hbar(by_category, "discount_rate_pct", "category", "Discount dependence by category",
                    "Records with discount (%)", suffix="%", fmt=".1f", hover_cols={"records": "Records"}),
        "discounts_by_category", left)
    product_count = right.slider("Products to show", 5, 25, 10, key="disc_n")
    by_product = metrics.discount_rate_by(df, "item_purchased", settings.MIN_GROUP_SIZE).head(product_count)
    charts.show_chart(
        charts.hbar(by_product, "discount_rate_pct", "item_purchased",
                    f"Top {len(by_product)} products by discount usage", "Records with discount (%)",
                    suffix="%", fmt=".1f", color=settings.PALETTE["accent"], hover_cols={"records": "Records"}),
        "discounts_by_product", right)
    right.caption(f"Products with fewer than {settings.MIN_GROUP_SIZE} records are excluded.")
    if not by_category.empty:
        top = by_category.iloc[0]
        show_finding(f"**{top['category']}** has the highest discount share ({top['discount_rate_pct']:.1f}% "
                     f"of {fmt_int(top['records'])} records).")
