"""Customer Intelligence | Shopping Behavior & Business Insights.

Run with:  streamlit run app.py
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from analytics import metrics
from analytics.data_loader import DataQualityReport, load_customer_data
from components.filters import apply_filters, describe_active_filters, render_sidebar_filters
from config import settings
from dashboard import data_quality, demographics, discounts, insights, overview, products, purchasing, subscriptions
from dashboard.styles import inject_styles, show_hero
from database.connection import DatabaseError, check_connection, create_readonly_engine
from database.queries import count_customer_rows

st.set_page_config(page_title="Customer Intelligence | Shopping Behavior", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")

TAB_LABELS = [
    "Executive Overview", "Customer Demographics", "Product & Category", "Subscription & Segments",
    "Discounts", "Shipping & Payment", "Insights & Recommendations", "Data Quality",
]


@st.cache_resource(show_spinner=False)
def get_engine():
    """One pooled, read-only engine per server process."""
    engine = create_readonly_engine()
    check_connection(engine)
    return engine


@st.cache_data(ttl=settings.CACHE_TTL_SECONDS, show_spinner="Loading customer data from Neon...")
def load_data() -> tuple[pd.DataFrame, DataQualityReport, int | None]:
    engine = get_engine()
    df, report = load_customer_data(engine)
    return df, report, count_customer_rows(engine)


def refresh_data() -> None:
    load_data.clear()
    st.cache_resource.clear()  # also rebuilds the engine (recovers from a dropped connection)


def load_data_or_stop() -> tuple[pd.DataFrame, DataQualityReport, int | None]:
    try:
        return load_data()
    except DatabaseError as exc:
        st.error(f"Could not load data: {exc}")
        st.info("Fix the issue, then press **Refresh data from database** in the sidebar.")
    except Exception as exc:  # last resort; never leak connection details
        st.error(f"Unexpected error while loading data ({type(exc).__name__}). Check the server logs.")
    st.stop()


def main() -> None:
    inject_styles()
    show_hero(settings.APP_TITLE,
              "Interactive analysis of customer purchases from Neon PostgreSQL. "
              "Use the sidebar filters - every KPI, chart and insight updates.")

    st.sidebar.title("Customer Intelligence")
    st.sidebar.button("Refresh data from database", on_click=refresh_data, width="stretch",
                      key="refresh_btn", help="Clears the cache and re-reads the customer table.")

    customers, report, database_rows = load_data_or_stop()

    selections = render_sidebar_filters(customers)
    filtered = apply_filters(customers, selections)

    st.sidebar.divider()
    st.sidebar.metric("Records matching filters", f"{len(filtered):,} / {len(customers):,}")

    active_filters = describe_active_filters(selections)
    if active_filters:
        st.caption("Active filters - " + " | ".join(active_filters))

    if filtered.empty:
        st.warning("No records match the current filters. Adjust or reset the filters in the sidebar.")
        st.stop()

    tabs = st.tabs(TAB_LABELS)
    with tabs[0]:
        overview.render(filtered, metrics.compute_kpis(customers))
    with tabs[1]:
        demographics.render(filtered)
    with tabs[2]:
        products.render(filtered)
    with tabs[3]:
        subscriptions.render(filtered)
    with tabs[4]:
        discounts.render(filtered)
    with tabs[5]:
        purchasing.render(filtered)
    with tabs[6]:
        insights.render(filtered)
    with tabs[7]:
        data_quality.render(report, database_rows)


main()
