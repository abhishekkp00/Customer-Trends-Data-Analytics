"""Shipping and payment tab: shipping, payment method and purchase frequency."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from analytics import metrics
from components import charts
from components.kpi_cards import fmt_pct
from dashboard.styles import show_finding


def render(df: pd.DataFrame) -> None:
    shipping = metrics.shipping_summary(df)
    payments = metrics.payment_summary(df)
    frequency = metrics.frequency_summary(df)

    left, right = st.columns(2)
    charts.show_chart(
        charts.hbar(shipping, "records", "shipping_type", "Shipping method preference", "Records"),
        "purchasing_shipping_records", left)
    charts.show_chart(
        charts.hbar(shipping, "avg_amount", "shipping_type", "Average purchase by shipping type",
                    "Avg purchase per record (USD)", prefix="$", fmt=",.2f"),
        "purchasing_shipping_avg", right)
    if not shipping.empty:
        top = shipping.iloc[0]
        share = metrics.pct(top["records"], shipping["records"].sum())
        show_finding(f"**{top['shipping_type']}** is the most common option ({fmt_pct(share)} of records).")

    left, right = st.columns(2)
    charts.show_chart(
        charts.donut(payments, "payment_method", "records", "Payment method distribution", "Records"),
        "purchasing_payment_donut", left)
    charts.show_chart(
        charts.hbar(payments, "total_amount", "payment_method", "Purchase amount by payment method",
                    "Total purchase amount (USD)", prefix="$"),
        "purchasing_payment_amount", right)
    if not payments.empty:
        top = payments.iloc[0]
        share = metrics.pct(top["records"], payments["records"].sum())
        show_finding(f"**{top['payment_method']}** is used most often ({fmt_pct(share)} of records).")

    left, right = st.columns(2)
    charts.show_chart(
        charts.vbar(frequency, "frequency_of_purchases", "records", "Purchase frequency distribution",
                    "Self-reported purchase frequency", "Records", height=380),
        "purchasing_frequency", left)
    charts.show_chart(
        charts.heatmap(metrics.payment_shipping_matrix(df), "Payment method x shipping type (records)",
                       "Records", x_label="Shipping type", y_label="Payment method", height=380),
        "purchasing_payment_shipping_heatmap", right)
    st.caption("Purchase frequency is the customer's stated buying cadence (not derived from dates).")
