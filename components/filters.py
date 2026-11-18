"""Sidebar filters. An empty selection means "all values"."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from config import settings

_KEY_PREFIX = "flt_"


def filter_key(column: str) -> str:
    return f"{_KEY_PREFIX}{column}"


def apply_filters(df: pd.DataFrame, selections: dict[str, list[str]]) -> pd.DataFrame:
    """Filter ``df``: AND across columns, OR within a column. Pure function."""
    mask = pd.Series(True, index=df.index)
    for column, values in selections.items():
        if values:
            mask &= df[column].isin(values)
    return df[mask]


def _sorted_options(df: pd.DataFrame, column: str) -> list[str]:
    values = df[column].dropna().unique().tolist()
    if column == "age_group":
        return [v for v in settings.AGE_GROUP_ORDER if v in values] + sorted(set(values) - set(settings.AGE_GROUP_ORDER))
    if column == "frequency_of_purchases":
        known = [v for v in settings.FREQUENCY_ORDER if v in values]
        return known + sorted(set(values) - set(known))
    return sorted(values)


def _reset_filters() -> None:
    for column, _ in settings.FILTER_SPECS:
        st.session_state[filter_key(column)] = []


def render_sidebar_filters(df: pd.DataFrame) -> dict[str, list[str]]:
    """Draw the filter widgets and return the current selections."""
    st.sidebar.header("Filters")
    st.sidebar.caption("Leave a filter empty to include all values. Every KPI, chart and insight updates.")
    st.sidebar.button("Reset all filters", on_click=_reset_filters, width="stretch",
                      key="reset_filters_btn")

    selections: dict[str, list[str]] = {}
    for column, label in settings.FILTER_SPECS:
        selections[column] = st.sidebar.multiselect(
            label,
            options=_sorted_options(df, column),
            key=filter_key(column),
            placeholder="All",
        )
    return selections


def describe_active_filters(selections: dict[str, list[str]]) -> list[str]:
    labels = dict(settings.FILTER_SPECS)
    out = []
    for column, values in selections.items():
        if values:
            shown = ", ".join(values[:3]) + (f" +{len(values) - 3} more" if len(values) > 3 else "")
            out.append(f"{labels[column]}: {shown}")
    return out
