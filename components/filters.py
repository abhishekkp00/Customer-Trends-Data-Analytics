"""Sidebar filters. An empty selection means "all values"."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from config import settings

KEY_PREFIX = "flt_"
CANONICAL_ORDER = {
    "age_group": settings.AGE_GROUP_ORDER,
    "frequency_of_purchases": settings.FREQUENCY_ORDER,
}


def filter_key(column: str) -> str:
    return f"{KEY_PREFIX}{column}"


def apply_filters(df: pd.DataFrame, selections: dict[str, list[str]]) -> pd.DataFrame:
    """Filter ``df``: AND across columns, OR within a column. Empty selections are ignored."""
    mask = pd.Series(True, index=df.index)
    for column, values in selections.items():
        if values:
            mask &= df[column].isin(values)
    return df[mask]


def describe_active_filters(selections: dict[str, list[str]]) -> list[str]:
    """One short line per filter that has a selection, e.g. 'Gender: Male'."""
    labels = dict(settings.FILTER_SPECS)
    descriptions = []
    for column, values in selections.items():
        if values:
            shown = ", ".join(values[:3]) + (f" +{len(values) - 3} more" if len(values) > 3 else "")
            descriptions.append(f"{labels[column]}: {shown}")
    return descriptions


def _sorted_options(df: pd.DataFrame, column: str) -> list[str]:
    values = df[column].dropna().unique().tolist()
    canonical = CANONICAL_ORDER.get(column, [])
    known = [v for v in canonical if v in values]
    return known + sorted(set(values) - set(known))


def _reset_filters() -> None:
    for column, _ in settings.FILTER_SPECS:
        st.session_state[filter_key(column)] = []


def render_sidebar_filters(df: pd.DataFrame) -> dict[str, list[str]]:
    """Draw the filter widgets and return the current selections."""
    st.sidebar.header("Filters")
    st.sidebar.caption("Leave a filter empty to include all values. Every KPI, chart and insight updates.")
    st.sidebar.button("Reset all filters", on_click=_reset_filters, width="stretch", key="reset_filters_btn")

    selections: dict[str, list[str]] = {}
    for column, label in settings.FILTER_SPECS:
        selections[column] = st.sidebar.multiselect(
            label,
            options=_sorted_options(df, column),
            key=filter_key(column),
            placeholder="All",
        )
    return selections
