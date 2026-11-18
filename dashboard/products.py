"""Product and category tab: contribution, product ranking, popularity vs rating."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from analytics import metrics
from components import charts
from components.kpi_cards import fmt_money, fmt_pct
from config import settings
from dashboard.styles import show_finding

RANKING_METRICS = {
    "Most purchased (records)": "records",
    "Total purchase amount": "total_amount",
    "Average purchase amount": "avg_amount",
    "Average rating": "avg_rating",
}
PRODUCT_TABLE_COLUMNS = {
    "item_purchased": "Product", "category": "Category", "records": "Records",
    "total_amount": "Total amount ($)", "avg_amount": "Avg amount ($)", "avg_rating": "Avg rating",
}


def render(df: pd.DataFrame) -> None:
    categories = metrics.category_summary(df)
    left, right = st.columns(2)
    charts.show_chart(
        charts.hbar(categories, "total_amount", "category", "Purchase amount by category",
                    "Total purchase amount (USD)", prefix="$"),
        "products_category_amount", left)
    charts.show_chart(
        charts.hbar(categories, "avg_amount", "category", "Average purchase amount by category",
                    "Avg purchase per record (USD)", prefix="$", fmt=",.2f"),
        "products_category_avg", right)
    if not categories.empty:
        top = categories.iloc[0]
        show_finding(f"**{top['category']}** contributes the most recorded purchase amount: "
                     f"{fmt_money(top['total_amount'])} ({fmt_pct(top['share_of_amount_pct'])} of the selection).")
    charts.show_chart(
        charts.treemap(metrics.product_summary(df), ["category", "item_purchased"], "total_amount",
                       "Category contribution to purchase amount (click a category to drill into products)"),
        "products_treemap")

    st.subheader("Product ranking")
    scoped = _render_ranking(df)

    left, right = st.columns(2)
    charts.show_chart(
        charts.popularity_scatter(metrics.product_summary(scoped),
                                  "Product popularity vs rating (bubble = total purchase amount)"),
        "products_popularity_scatter", left)
    charts.show_chart(
        charts.box(df.dropna(subset=["review_rating"]), "category", "review_rating",
                   "Review rating distribution by category", "Category", "Review rating (out of 5)"),
        "products_rating_box", right)
    top_three = metrics.top_products_per_category(df, 3)
    if not top_three.empty:
        with st.expander("Top 3 products in each category (by records)"):
            table = top_three[["category", "rank", "item_purchased", "records"]].rename(columns={
                "category": "Category", "rank": "Rank", "item_purchased": "Product", "records": "Records"})
            st.dataframe(table, width="stretch", hide_index=True)


def _render_ranking(df: pd.DataFrame) -> pd.DataFrame:
    """Ranking controls, chart and table. Returns the records the ranking was based on."""
    col_metric, col_top, col_min, col_categories = st.columns([2, 1, 1, 2])
    metric_label = col_metric.selectbox("Rank products by", list(RANKING_METRICS), key="prod_metric")
    top_n = col_top.slider("Show top", 3, 20, 10, key="prod_n")
    min_records = col_min.number_input("Min records", 1, 200, settings.MIN_GROUP_SIZE, key="prod_min",
                                       help="Hide products with too few records for a fair comparison.")
    chosen = col_categories.multiselect("Limit to categories", sorted(df["category"].unique()),
                                        key="prod_cats", placeholder="All")
    scoped = df[df["category"].isin(chosen)] if chosen else df

    metric = RANKING_METRICS[metric_label]
    ranked = metrics.top_products(scoped, metric, top_n, int(min_records))
    ranked = ranked.assign(label=ranked["item_purchased"] + " (" + ranked["category"] + ")")
    charts.show_chart(
        charts.hbar(ranked, metric, "label", f"Top {len(ranked)} products - {metric_label.lower()}",
                    metric_label,
                    fmt=",.2f" if metric in ("avg_amount", "avg_rating") else ",.0f",
                    prefix="$" if "amount" in metric else "",
                    hover_cols={"records": "Records", "avg_rating": "Avg rating"}),
        "products_ranking")
    if metric == "avg_rating":
        st.caption("Rating differences between products are often small - check the axis values "
                   "before drawing conclusions.")
    table = ranked[list(PRODUCT_TABLE_COLUMNS)].rename(columns=PRODUCT_TABLE_COLUMNS)
    styled = (table.style
              .background_gradient(subset=["Records", "Total amount ($)", "Avg rating"], cmap="Blues")
              .format({"Total amount ($)": "${:,.0f}", "Avg amount ($)": "${:,.2f}", "Avg rating": "{:.2f}"}))
    st.dataframe(styled, width="stretch", hide_index=True)
    return scoped
