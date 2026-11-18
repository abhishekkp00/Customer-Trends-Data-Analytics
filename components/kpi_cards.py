"""KPI cards and number formatting."""
from __future__ import annotations

from typing import Callable

import streamlit as st

NA = "n/a"


def fmt_money(x: float | None, decimals: int = 0) -> str:
    return NA if x is None else f"${x:,.{decimals}f}"


def fmt_int(x: float | None) -> str:
    return NA if x is None else f"{int(x):,}"


def fmt_pct(x: float | None, decimals: int = 1) -> str:
    return NA if x is None else f"{x:.{decimals}f}%"


def fmt_num(x: float | None, decimals: int = 1) -> str:
    return NA if x is None else f"{x:,.{decimals}f}"


def _fmt_money_2dp(x: float | None) -> str:
    return fmt_money(x, 2)


def _fmt_years(x: float | None) -> str:
    return NA if x is None else f"{x:.1f} yrs"


def _fmt_rating_out_of_5(x: float | None) -> str:
    return NA if x is None else f"{x:,.2f} / 5"


def _fmt_rating(x: float | None) -> str:
    return fmt_num(x, 2)


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


# (label, KPI key, card formatter, help text, formatter for the "All data" line).
_CARD_ROWS: list[list[tuple[str, str, Callable, str, Callable]]] = [
    [
        ("Total purchase amount", "total_purchase_amount", fmt_money,
         "Sum of purchase amounts (USD) across the selected records.", fmt_money),
        ("Transaction records", "total_records", fmt_int,
         "Number of recorded purchases (rows) selected.", fmt_int),
        ("Unique customers", "unique_customers", fmt_int,
         "Distinct customer IDs. Equals records only if every ID appears once.", fmt_int),
        ("Avg purchase per record", "avg_purchase_per_record", _fmt_money_2dp,
         "Total purchase amount divided by records.", _fmt_money_2dp),
    ],
    [
        ("Average customer age", "avg_age", _fmt_years,
         "Mean age across selected records.", _fmt_years),
        ("Average review rating", "avg_rating", _fmt_rating_out_of_5,
         "Mean rating; records without a rating are excluded.", _fmt_rating),
        ("Subscription rate", "subscription_rate", fmt_pct,
         "Share of selected records with an active subscription.", fmt_pct),
        ("Discount usage rate", "discount_rate", fmt_pct,
         "Share of selected records where a discount was applied.", fmt_pct),
    ],
]


def render_kpis(kpis: dict, overall: dict | None = None) -> None:
    """Two rows of four cards. ``overall`` (unfiltered KPIs) adds an "All data"
    comparison line when a filter is active."""
    for row in _CARD_ROWS:
        for column, (label, key, card_format, help_text, compare_format) in zip(st.columns(4), row):
            comparable = overall is not None and kpis.get(key) is not None and overall.get(key) is not None
            comparison = f"All data: {compare_format(overall[key])}" if comparable else ""
            with column:
                kpi_card(label, card_format(kpis[key]), help_text, comparison)
