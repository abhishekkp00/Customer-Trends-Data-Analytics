"""Data quality tab: reconciliation with the database and validation results."""
from __future__ import annotations

import streamlit as st

from analytics.data_loader import DataQualityReport
from components.kpi_cards import fmt_int


def render(report: DataQualityReport, database_rows: int | None) -> None:
    columns = st.columns(4)
    columns[0].metric("Rows loaded", fmt_int(report.row_count))
    columns[1].metric("Rows in database (COUNT)", fmt_int(database_rows) if database_rows is not None else "n/a")
    columns[2].metric("Customer IDs unique", "Yes" if report.customer_id_unique else "No")
    columns[3].metric("Duplicate rows", fmt_int(report.duplicate_rows))
    if report.warnings:
        for warning in report.warnings:
            st.warning(warning)
    else:
        st.success("No schema or data-quality issues detected.")
    st.caption("The dashboard reads the already-cleaned `customer` table read-only; "
               "it never repeats or alters the cleaning pipeline.")
