"""Subscription and customer segment tab."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from analytics import metrics
from components import charts
from components.kpi_cards import fmt_money, fmt_pct
from config import settings
from dashboard.styles import show_finding


def render(df: pd.DataFrame) -> None:
    with st.expander("Segmentation rules (read first)", expanded=False):
        rules = "\n".join(f"- **{name}** - {rule}" for name, rule in settings.SEGMENT_RULES.items())
        st.markdown(
            "Customers are segmented by the **previous purchases** field (same rule as SQL Q7):\n\n"
            + rules
            + "\n\n> 'New' means a customer with a **very short recorded history** "
              f"({settings.SEGMENT_RULES['New']}), "
              "not necessarily a first-time buyer. Thresholds are a business convention, not a statistical result.")

    subscriptions = metrics.subscription_summary(df)
    segments = metrics.segment_summary(df)
    first, second, third = st.columns(3)
    charts.show_chart(
        charts.donut(subscriptions, "subscription_status", "customers", "Customers by subscription",
                     "Customers", height=330),
        "subscriptions_donut", first)
    charts.show_chart(
        charts.vbar(subscriptions, "subscription_status", "avg_amount", "Avg purchase by subscription",
                    "Subscribed", "Avg purchase per record (USD)", prefix="$", fmt=",.2f", height=330),
        "subscriptions_avg", second)
    charts.show_chart(
        charts.vbar(subscriptions, "subscription_status", "total_amount", "Total purchase by subscription",
                    "Subscribed", "Total purchase amount (USD)", prefix="$", height=330),
        "subscriptions_total", third)
    if {"Yes", "No"} <= set(subscriptions["subscription_status"]):
        by_status = subscriptions.set_index("subscription_status")
        subscriber_share = metrics.pct(by_status.loc["Yes", "records"], by_status["records"].sum())
        show_finding(
            f"Subscribers average {fmt_money(by_status.loc['Yes', 'avg_amount'], 2)} per record vs "
            f"{fmt_money(by_status.loc['No', 'avg_amount'], 2)} for non-subscribers; subscribers are "
            f"{fmt_pct(subscriber_share)} of records.")

    left, right = st.columns(2)
    charts.show_chart(
        charts.vbar(segments, "customer_segment", "customers", "Customers by segment", "Segment", "Customers"),
        "segments_customers", left)
    charts.show_chart(
        charts.vbar(segments, "customer_segment", "avg_amount", "Average purchase by segment",
                    "Segment", "Avg purchase per record (USD)", prefix="$", fmt=",.2f"),
        "segments_avg", right)
    rate_by_segment = metrics.subscription_by_segment(df)
    if not rate_by_segment.empty:
        charts.show_chart(
            charts.vbar(rate_by_segment, "customer_segment", "subscription_rate_pct",
                        "Subscription rate by segment", "Segment", "Subscribed (% of segment records)",
                        suffix="%", fmt=".1f"),
            "segments_subscription_rate")
        show_finding("Subscription rate is computed within each segment, "
                     "so segments of different sizes are comparable.")
