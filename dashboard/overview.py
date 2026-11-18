"""Executive overview tab: KPI cards and headline charts."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from analytics import metrics
from components import charts
from components.kpi_cards import fmt_money, render_kpis


def render(df: pd.DataFrame, full_kpis: dict) -> None:
    kpis = metrics.compute_kpis(df)
    render_kpis(kpis, full_kpis if len(df) != full_kpis["total_records"] else None)
    if kpis["unique_customers"] and kpis["unique_customers"] != kpis["total_records"]:
        st.info("Customer IDs repeat in this selection, so unique customers are fewer than records.")
    with st.expander("How to read these numbers"):
        st.markdown(
            "- **Records vs customers:** each row is one recorded purchase; customers are counted by distinct ID.\n"
            "- **Average per record** is total purchase amount / records. "
            f"Average spend per customer: **{fmt_money(kpis['avg_spend_per_customer'], 2)}**.\n"
            "- **Rates** use the selected records as denominator. Review rating ignores records without a rating.\n"
            "- The data has **no dates**, so there are no time trends or period-over-period comparisons. "
            "'All data' comparisons show the unfiltered value.")
    left, right = st.columns(2)
    charts.show_chart(
        charts.histogram(df, "purchase_amount", "How much do customers spend per record?",
                         "Purchase amount (USD)", prefix="$"),
        "overview_amount_histogram", left)
    charts.show_chart(
        charts.treemap(metrics.category_summary(df), ["category"], "total_amount",
                       "Where does the purchase amount come from?"),
        "overview_category_treemap", right)
