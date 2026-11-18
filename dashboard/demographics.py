"""Customer demographics tab: gender, age group and location."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from analytics import metrics
from components import charts
from components.kpi_cards import fmt_int, fmt_money, fmt_pct
from dashboard.styles import show_finding


def render(df: pd.DataFrame) -> None:
    genders = metrics.gender_summary(df)
    age_groups = metrics.age_group_summary(df)
    left, right = st.columns(2)
    charts.show_chart(
        charts.donut(genders, "gender", "customers", "Customers by gender", "Customers"),
        "demographics_gender_donut", left)
    charts.show_chart(
        charts.vbar(age_groups, "age_group", "customers", "Customers by age group", "Age group", "Customers"),
        "demographics_age_customers", right)
    if not age_groups.empty:
        largest = age_groups.sort_values("customers", ascending=False).iloc[0]
        share = metrics.pct(largest["customers"], age_groups["customers"].sum())
        show_finding(
            f"**{largest['age_group']}** is the largest age group with {fmt_int(largest['customers'])} customers "
            f"({fmt_pct(share)}). Age groups are quartiles of age, so sizes are similar by design.")

    left, right = st.columns(2)
    charts.show_chart(
        charts.vbar(age_groups, "age_group", "total_amount", "Purchase amount by age group",
                    "Age group", "Total purchase amount (USD)", prefix="$"),
        "demographics_age_amount", left)
    charts.show_chart(
        charts.vbar(genders, "gender", "avg_amount", "Average purchase amount by gender",
                    "Gender", "Avg purchase per record (USD)", prefix="$", fmt=",.2f"),
        "demographics_gender_avg", right)
    if len(genders) > 1:
        highest, lowest = genders.sort_values("avg_amount", ascending=False).iloc[[0, -1]].to_dict("records")
        show_finding(
            f"Average purchase per record: **{highest['gender']} {fmt_money(highest['avg_amount'], 2)}** vs "
            f"{lowest['gender']} {fmt_money(lowest['avg_amount'], 2)}. "
            f"Total amount differs mostly because of record counts "
            f"({fmt_int(highest['records'])} vs {fmt_int(lowest['records'])}).")

    locations = metrics.location_summary(df)
    shown = st.slider("Locations to show", 5, 30, 12, key="loc_n") if len(locations) > 5 else len(locations)
    charts.show_chart(
        charts.hbar(locations.head(shown), "customers", "location",
                    f"Top {min(shown, len(locations))} locations by customers", "Customers",
                    hover_cols={"total_amount": "Total amount ($)"}),
        "demographics_locations")
    if not locations.empty:
        top = locations.iloc[0]
        show_finding(f"**{top['location']}** has the most customers ({fmt_int(top['customers'])}); "
                     f"{len(locations)} locations are in the current selection.")
