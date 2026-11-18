"""KPI card rendering and number formatting."""
from __future__ import annotations

from typing import Optional

import streamlit as st

NA = "n/a"


def fmt_money(x: Optional[float], decimals: int = 0) -> str:
    return NA if x is None else f"${x:,.{decimals}f}"


def fmt_int(x: Optional[float]) -> str:
    return NA if x is None else f"{int(x):,}"


def fmt_pct(x: Optional[float], decimals: int = 1) -> str:
    return NA if x is None else f"{x:.{decimals}f}%"


def fmt_num(x: Optional[float], decimals: int = 1) -> str:
    return NA if x is None else f"{x:,.{decimals}f}"


def kpi_card(label: str, value: str, help_text: str, sub: str = "") -> None:
    """One KPI card: label, formatted value, short explanation."""
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    st.markdown(
        f"""<div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-help">{help_text}</div>{sub_html}
        </div>""",
        unsafe_allow_html=True,
    )


def render_kpis(kpis: dict, overall: dict | None = None) -> None:
    """Two rows of four cards. ``overall`` (unfiltered KPIs) gives context
    for averages and rates when a filter is active."""
    def vs(key: str, formatter, label: str = "all records") -> str:
        if overall is None or kpis.get(key) is None or overall.get(key) is None:
            return ""
        return f"All data: {formatter(overall[key])}"

    r1 = st.columns(4)
    with r1[0]:
        kpi_card("Total purchase amount", fmt_money(kpis["total_purchase_amount"]),
                 "Sum of purchase amounts (USD) across the selected records.",
                 vs("total_purchase_amount", fmt_money))
    with r1[1]:
        kpi_card("Transaction records", fmt_int(kpis["total_records"]),
                 "Number of recorded purchases (rows) selected.",
                 vs("total_records", fmt_int))
    with r1[2]:
        kpi_card("Unique customers", fmt_int(kpis["unique_customers"]),
                 "Distinct customer IDs. Equals records only if every ID appears once.",
                 vs("unique_customers", fmt_int))
    with r1[3]:
        kpi_card("Avg purchase per record", fmt_money(kpis["avg_purchase_per_record"], 2),
                 "Total purchase amount divided by records.",
                 vs("avg_purchase_per_record", lambda v: fmt_money(v, 2)))
    r2 = st.columns(4)
    with r2[0]:
        kpi_card("Average customer age", fmt_num(kpis["avg_age"]) + (" yrs" if kpis["avg_age"] is not None else ""),
                 "Mean age across selected records.",
                 vs("avg_age", lambda v: f"{v:.1f} yrs"))
    with r2[1]:
        kpi_card("Average review rating", (fmt_num(kpis["avg_rating"], 2) + " / 5") if kpis["avg_rating"] is not None else NA,
                 "Mean rating; records without a rating are excluded.",
                 vs("avg_rating", lambda v: f"{v:.2f}"))
    with r2[2]:
        kpi_card("Subscription rate", fmt_pct(kpis["subscription_rate"]),
                 "Share of selected records with an active subscription.",
                 vs("subscription_rate", fmt_pct))
    with r2[3]:
        kpi_card("Discount usage rate", fmt_pct(kpis["discount_rate"]),
                 "Share of selected records where a discount was applied.",
                 vs("discount_rate", fmt_pct))
