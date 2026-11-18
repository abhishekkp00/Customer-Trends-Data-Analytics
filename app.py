"""Customer Intelligence | Shopping Behavior & Business Insights.

Run with:  streamlit run app.py
"""
from __future__ import annotations

import itertools
import pandas as pd
import streamlit as st

from analytics import insights as ins
from analytics import metrics as m
from analytics.data_loader import DataQualityReport, database_row_count, load_customer_data
from components import charts as ch
from components.filters import apply_filters, describe_active_filters, render_sidebar_filters
from components.kpi_cards import fmt_int, fmt_money, fmt_pct, render_kpis
from config import settings
from database.connection import DatabaseError, check_connection, create_readonly_engine

st.set_page_config(page_title="Customer Intelligence | Shopping Behavior", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")

CSS = """
<style>
.block-container {padding-top: 1.6rem; max-width: 1500px;}
.hero {background: linear-gradient(120deg,#312E81 0%,#4F46E5 55%,#0EA5E9 100%);
       padding: 1.4rem 1.8rem; border-radius: 16px; color: #fff; margin-bottom: 1rem;}
.hero h1 {font-size: 1.7rem; margin: 0; color: #fff; font-weight: 700; padding: 0;}
.hero p {margin: .35rem 0 0 0; opacity: .9; font-size: .95rem;}
.kpi-card {background: var(--secondary-background-color); border: 1px solid rgba(148,163,184,.35);
           border-left: 5px solid #4F46E5; border-radius: 12px; padding: .85rem 1rem; margin-bottom: .8rem;
           min-height: 138px; transition: transform .15s ease, box-shadow .15s ease;}
.kpi-card:hover {transform: translateY(-2px); box-shadow: 0 6px 18px rgba(79,70,229,.18);}
.kpi-label {font-size: .78rem; text-transform: uppercase; letter-spacing: .05em; opacity: .75; font-weight: 600;}
.kpi-value {font-size: 1.85rem; font-weight: 700; line-height: 1.25; margin: .15rem 0;}
.kpi-help {font-size: .78rem; opacity: .7; line-height: 1.3;}
.kpi-sub {font-size: .74rem; margin-top: .3rem; color: #0EA5E9; font-weight: 600;}
.finding {border-left: 4px solid #F59E0B; background: rgba(245,158,11,.10); padding: .6rem .9rem;
          border-radius: 8px; font-size: .92rem; margin: .2rem 0 1rem 0;}
.insight {border: 1px solid rgba(148,163,184,.35); border-radius: 12px; padding: 1rem 1.2rem; margin-bottom: 1rem;
          background: var(--secondary-background-color);}
.insight h4 {margin: 0 0 .5rem 0;}
.insight .lbl {font-weight: 700; color: #4F46E5;}
.insight p {margin: .25rem 0; font-size: .92rem;}
@media (max-width: 900px) {.hero h1 {font-size: 1.25rem;} .kpi-value {font-size: 1.45rem;} .kpi-card {min-height: 0;}}
</style>
"""


# --------------------------------------------------------------------------- #
# Data access (cached)
# --------------------------------------------------------------------------- #
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
    return df, report, database_row_count(engine)


def refresh_data() -> None:
    load_data.clear()
    st.cache_resource.clear()  # also rebuilds the engine (recovers from a dropped connection)


_chart_counter = itertools.count()


def plot(container, fig, **_ignored) -> None:
    """Render a Plotly figure with a unique, rerun-stable key (the counter
    is reset at the start of every script run)."""
    container.plotly_chart(fig, width="stretch", key=f"chart_{next(_chart_counter)}")


def finding(text: str) -> None:
    st.markdown(f'<div class="finding"><b>Key finding:</b> {text}</div>', unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Sections
# --------------------------------------------------------------------------- #
def section_overview(df: pd.DataFrame, full_kpis: dict) -> None:
    kpis = m.compute_kpis(df)
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
    c1, c2 = st.columns(2)
    plot(c1, ch.histogram(df, "purchase_amount", "How much do customers spend per record?",
                                 "Purchase amount (USD)", prefix="$"))
    plot(c2, ch.treemap(m.category_summary(df), ["category"], "total_amount",
                               "Where does the purchase amount come from?"))


def section_demographics(df: pd.DataFrame) -> None:
    g, a = m.gender_summary(df), m.age_group_summary(df)
    c1, c2 = st.columns(2)
    plot(c1, ch.donut(g, "gender", "customers", "Customers by gender", "Customers"))
    plot(c2, ch.vbar(a, "age_group", "customers", "Customers by age group",
                            "Age group", "Customers"))
    if not a.empty:
        top = a.sort_values("customers", ascending=False).iloc[0]
        finding(f"**{top['age_group']}** is the largest age group with {fmt_int(top['customers'])} customers "
                f"({fmt_pct(m.pct(top['customers'], a['customers'].sum()))}). Age groups are quartiles of age, so sizes are similar by design.")
    c3, c4 = st.columns(2)
    plot(c3, ch.vbar(a, "age_group", "total_amount", "Purchase amount by age group",
                            "Age group", "Total purchase amount (USD)", prefix="$"))
    plot(c4, ch.vbar(g, "gender", "avg_amount", "Average purchase amount by gender",
                            "Gender", "Avg purchase per record (USD)", prefix="$", fmt=",.2f"))
    if len(g) > 1:
        hi, lo = g.sort_values("avg_amount", ascending=False).iloc[[0, -1]].to_dict("records")
        finding(f"Average purchase per record: **{hi['gender']} {fmt_money(hi['avg_amount'], 2)}** vs "
                f"{lo['gender']} {fmt_money(lo['avg_amount'], 2)}. "
                f"Total amount differs mostly because of record counts ({fmt_int(hi['records'])} vs {fmt_int(lo['records'])}).")
    loc = m.location_summary(df)
    n = st.slider("Locations to show", 5, 30, 12, key="loc_n") if len(loc) > 5 else len(loc)
    plot(st, ch.hbar(loc.head(n), "customers", "location", f"Top {min(n, len(loc))} locations by customers",
                            "Customers", hover_cols={"total_amount": "Total amount ($)"}))
    if not loc.empty:
        t = loc.iloc[0]
        finding(f"**{t['location']}** has the most customers ({fmt_int(t['customers'])}); "
                f"{len(loc)} locations are in the current selection.")


def section_products(df: pd.DataFrame) -> None:
    cat = m.category_summary(df)
    c1, c2 = st.columns(2)
    plot(c1, ch.hbar(cat, "total_amount", "category", "Purchase amount by category",
                            "Total purchase amount (USD)", prefix="$"))
    plot(c2, ch.hbar(cat, "avg_amount", "category", "Average purchase amount by category",
                            "Avg purchase per record (USD)", prefix="$", fmt=",.2f"))
    if not cat.empty:
        top = cat.iloc[0]
        finding(f"**{top['category']}** contributes the most recorded purchase amount: {fmt_money(top['total_amount'])} "
                f"({fmt_pct(top['share_of_amount_pct'])} of the selection).")
    plot(st, ch.treemap(m.product_summary(df), ["category", "item_purchased"], "total_amount",
                               "Category contribution to purchase amount (click a category to drill into products)"),
                    width="stretch")

    st.subheader("Product ranking")
    f1, f2, f3, f4 = st.columns([2, 1, 1, 2])
    metric_labels = {"Most purchased (records)": "records", "Total purchase amount": "total_amount",
                     "Average purchase amount": "avg_amount", "Average rating": "avg_rating"}
    metric_label = f1.selectbox("Rank products by", list(metric_labels), key="prod_metric")
    top_n = f2.slider("Show top", 3, 20, 10, key="prod_n")
    min_rec = f3.number_input("Min records", 1, 200, settings.MIN_GROUP_SIZE, key="prod_min",
                              help="Hide products with too few records for a fair comparison.")
    cats = f4.multiselect("Limit to categories", sorted(df["category"].unique()), key="prod_cats", placeholder="All")
    sub = df[df["category"].isin(cats)] if cats else df
    metric = metric_labels[metric_label]
    ranked = m.top_products(sub, metric, top_n, int(min_rec))
    fmt = ",.2f" if metric in ("avg_amount", "avg_rating") else ",.0f"
    prefix = "$" if "amount" in metric else ""
    ranked = ranked.assign(label=ranked["item_purchased"] + " (" + ranked["category"] + ")")
    plot(st, ch.hbar(ranked, metric, "label", f"Top {len(ranked)} products - {metric_label.lower()}",
                            metric_label, fmt=fmt, prefix=prefix,
                            hover_cols={"records": "Records", "avg_rating": "Avg rating"}))
    if metric == "avg_rating":
        st.caption("Rating differences between products are often small - check the axis values before drawing conclusions.")
    show = ranked[["item_purchased", "category", "records", "total_amount", "avg_amount", "avg_rating"]].rename(columns={
        "item_purchased": "Product", "category": "Category", "records": "Records",
        "total_amount": "Total amount ($)", "avg_amount": "Avg amount ($)", "avg_rating": "Avg rating"})
    st.dataframe(show.style.background_gradient(subset=["Records", "Total amount ($)", "Avg rating"], cmap="Blues")
                 .format({"Total amount ($)": "${:,.0f}", "Avg amount ($)": "${:,.2f}", "Avg rating": "{:.2f}"}),
                 width="stretch", hide_index=True)

    c3, c4 = st.columns(2)
    plot(c3, ch.popularity_scatter(m.product_summary(sub),
                                          "Product popularity vs rating (bubble = total purchase amount)"),
                    width="stretch")
    plot(c4, ch.box(df.dropna(subset=["review_rating"]), "category", "review_rating",
                           "Review rating distribution by category", "Category", "Review rating (out of 5)"),
                    width="stretch")
    t3 = m.top_products_per_category(df, 3)
    if not t3.empty:
        with st.expander("Top 3 products in each category (by records)"):
            st.dataframe(t3[["category", "rank", "item_purchased", "records"]].rename(columns={
                "category": "Category", "rank": "Rank", "item_purchased": "Product", "records": "Records"}),
                width="stretch", hide_index=True)


def section_segments(df: pd.DataFrame) -> None:
    with st.expander("Segmentation rules (read first)", expanded=False):
        st.markdown(
            "Customers are segmented by the **previous purchases** field (same rule as SQL Q7):\n\n"
            + "\n".join(f"- **{k}** - {v}" for k, v in settings.SEGMENT_RULES.items())
            + "\n\n> 'New' means a customer with a **very short recorded history** (0-1 previous purchases), "
              "not necessarily a first-time buyer. Thresholds are a business convention, not a statistical result.")
    sub, seg = m.subscription_summary(df), m.segment_summary(df)
    c1, c2, c3 = st.columns(3)
    plot(c1, ch.donut(sub, "subscription_status", "customers", "Customers by subscription",
                             "Customers", height=330))
    plot(c2, ch.vbar(sub, "subscription_status", "avg_amount", "Avg purchase by subscription",
                            "Subscribed", "Avg purchase per record (USD)", prefix="$", fmt=",.2f", height=330),
                    width="stretch")
    plot(c3, ch.vbar(sub, "subscription_status", "total_amount", "Total purchase by subscription",
                            "Subscribed", "Total purchase amount (USD)", prefix="$", height=330),
                    width="stretch")
    if {"Yes", "No"} <= set(sub["subscription_status"]):
        s = sub.set_index("subscription_status")
        finding(f"Subscribers average {fmt_money(s.loc['Yes', 'avg_amount'], 2)} per record vs "
                f"{fmt_money(s.loc['No', 'avg_amount'], 2)} for non-subscribers; subscribers are "
                f"{fmt_pct(m.pct(s.loc['Yes', 'records'], s['records'].sum()))} of records.")
    c4, c5 = st.columns(2)
    plot(c4, ch.vbar(seg, "customer_segment", "customers", "Customers by segment",
                            "Segment", "Customers"))
    plot(c5, ch.vbar(seg, "customer_segment", "avg_amount", "Average purchase by segment",
                            "Segment", "Avg purchase per record (USD)", prefix="$", fmt=",.2f"),
                    width="stretch")
    sbs = m.subscription_by_segment(df)
    if not sbs.empty:
        plot(st, ch.vbar(sbs, "customer_segment", "subscription_rate_pct", "Subscription rate by segment",
                                "Segment", "Subscribed (% of segment records)", suffix="%", fmt=".1f"),
                        width="stretch")
        finding("Subscription rate is computed within each segment, so segments of different sizes are comparable.")


def section_discounts(df: pd.DataFrame) -> None:
    st.caption("Discount and promo-code fields were identical in the source data, so only discount status is analysed. "
               "Comparisons below are associations, not proof that discounts change spending.")
    d = m.discount_status_summary(df)
    c1, c2 = st.columns(2)
    plot(c1, ch.donut(d, "discount_applied", "records", "Share of records with a discount",
                             "Records"))
    plot(c2, ch.box(df, "discount_applied", "purchase_amount", "Purchase amount: discounted vs not",
                           "Discount applied", "Purchase amount (USD)", prefix="$"))
    if {"Yes", "No"} <= set(d["discount_applied"]):
        s = d.set_index("discount_applied")
        finding(f"Average purchase per record: {fmt_money(s.loc['Yes', 'avg_amount'], 2)} with a discount vs "
                f"{fmt_money(s.loc['No', 'avg_amount'], 2)} without. Discounts may have been offered selectively, so this does not show a causal effect.")
    by_cat = m.discount_rate_by(df, "category", 1)
    c3, c4 = st.columns(2)
    plot(c3, ch.hbar(by_cat, "discount_rate_pct", "category", "Discount dependence by category",
                            "Records with discount (%)", suffix="%", fmt=".1f",
                            hover_cols={"records": "Records"}))
    n = c4.slider("Products to show", 5, 25, 10, key="disc_n")
    by_prod = m.discount_rate_by(df, "item_purchased", settings.MIN_GROUP_SIZE).head(n)
    plot(c4, ch.hbar(by_prod, "discount_rate_pct", "item_purchased", f"Top {len(by_prod)} products by discount usage",
                            "Records with discount (%)", suffix="%", fmt=".1f", color=ch.P["accent"],
                            hover_cols={"records": "Records"}))
    c4.caption(f"Products with fewer than {settings.MIN_GROUP_SIZE} records are excluded.")
    if not by_cat.empty:
        finding(f"**{by_cat.iloc[0]['category']}** has the highest discount share ({by_cat.iloc[0]['discount_rate_pct']:.1f}% "
                f"of {fmt_int(by_cat.iloc[0]['records'])} records).")


def section_shipping_payment(df: pd.DataFrame) -> None:
    ship, pay, freq = m.shipping_summary(df), m.payment_summary(df), m.frequency_summary(df)
    c1, c2 = st.columns(2)
    plot(c1, ch.hbar(ship, "records", "shipping_type", "Shipping method preference", "Records"),
                    width="stretch")
    plot(c2, ch.hbar(ship, "avg_amount", "shipping_type", "Average purchase by shipping type",
                            "Avg purchase per record (USD)", prefix="$", fmt=",.2f"))
    if not ship.empty:
        t = ship.iloc[0]
        finding(f"**{t['shipping_type']}** is the most common option ({fmt_pct(m.pct(t['records'], ship['records'].sum()))} of records).")
    c3, c4 = st.columns(2)
    plot(c3, ch.donut(pay, "payment_method", "records", "Payment method distribution", "Records"),
                    width="stretch")
    plot(c4, ch.hbar(pay, "total_amount", "payment_method", "Purchase amount by payment method",
                            "Total purchase amount (USD)", prefix="$"))
    if not pay.empty:
        t = pay.iloc[0]
        finding(f"**{t['payment_method']}** is used most often ({fmt_pct(m.pct(t['records'], pay['records'].sum()))} of records).")
    c5, c6 = st.columns(2)
    plot(c5, ch.vbar(freq, "frequency_of_purchases", "records", "Purchase frequency distribution",
                            "Self-reported purchase frequency", "Records", height=380))
    plot(c6, ch.heatmap(df.pivot_table(index="payment_method", columns="shipping_type",
                                              values="customer_id", aggfunc="count", observed=True)
                               if not df.empty else pd.DataFrame(),
                               "Payment method x shipping type (records)", "Records",
                               x_label="Shipping type", y_label="Payment method", height=380),
                    width="stretch")
    st.caption("Purchase frequency is the customer's stated buying cadence (not derived from dates).")


def section_insights(df: pd.DataFrame) -> None:
    st.caption("Generated live from the current filters. Findings with too little data are not shown.")
    for item in ins.generate_insights(df):
        if not item.supported:
            st.markdown(f'<div class="insight"><h4>{item.title}</h4><p>ℹ️ {item.message}</p></div>',
                        unsafe_allow_html=True)
            continue
        st.markdown(
            f"""<div class="insight"><h4>{item.title}</h4>
            <p><span class="lbl">What the data shows:</span> {item.finding}</p>
            <p><span class="lbl">Metric &amp; comparison:</span> {item.metric}</p>
            <p><span class="lbl">Why it matters:</span> {item.why_it_matters}</p>
            <p><span class="lbl">Recommendation:</span> {item.recommendation}</p>
            <p><span class="lbl">Caveat:</span> {item.caveat}</p></div>""",
            unsafe_allow_html=True)


def section_data_quality(report: DataQualityReport, db_rows: int | None, df_full: pd.DataFrame) -> None:
    c = st.columns(4)
    c[0].metric("Rows loaded", fmt_int(report.row_count))
    c[1].metric("Rows in database (COUNT)", fmt_int(db_rows) if db_rows is not None else "n/a")
    c[2].metric("Customer IDs unique", "Yes" if report.customer_id_unique else "No")
    c[3].metric("Duplicate rows", fmt_int(report.duplicate_rows))
    if report.warnings:
        for w in report.warnings:
            st.warning(w)
    else:
        st.success("No schema or data-quality issues detected.")
    st.caption("The dashboard reads the already-cleaned `customer` table read-only; it never repeats or alters the cleaning pipeline.")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    global _chart_counter
    _chart_counter = itertools.count()
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(f'<div class="hero"><h1>{settings.APP_TITLE}</h1>'
                '<p>Interactive analysis of customer purchases from Neon PostgreSQL. '
                'Use the sidebar filters - every KPI, chart and insight updates.</p></div>',
                unsafe_allow_html=True)

    st.sidebar.title("Customer Intelligence")
    st.sidebar.button("Refresh data from database", on_click=refresh_data, width="stretch",
                      key="refresh_btn", help="Clears the cache and re-reads the customer table.")

    try:
        df_full, report, db_rows = load_data()
    except DatabaseError as exc:
        st.error(f"Could not load data: {exc}")
        st.info("Fix the issue, then press **Refresh data from database** in the sidebar.")
        st.stop()
    except Exception as exc:  # last resort; never leak connection details
        st.error(f"Unexpected error while loading data ({type(exc).__name__}). Check the server logs.")
        st.stop()

    selections = render_sidebar_filters(df_full)
    df = apply_filters(df_full, selections)

    st.sidebar.divider()
    st.sidebar.metric("Records matching filters", f"{len(df):,} / {len(df_full):,}")

    active = describe_active_filters(selections)
    if active:
        st.caption("Active filters - " + " | ".join(active))

    if df.empty:
        st.warning("No records match the current filters. Adjust or reset the filters in the sidebar.")
        st.stop()

    full_kpis = m.compute_kpis(df_full)
    tabs = st.tabs(["Executive Overview", "Customer Demographics", "Product & Category",
                    "Subscription & Segments", "Discounts", "Shipping & Payment",
                    "Insights & Recommendations", "Data Quality"])
    with tabs[0]:
        section_overview(df, full_kpis)
    with tabs[1]:
        section_demographics(df)
    with tabs[2]:
        section_products(df)
    with tabs[3]:
        section_segments(df)
    with tabs[4]:
        section_discounts(df)
    with tabs[5]:
        section_shipping_payment(df)
    with tabs[6]:
        section_insights(df)
    with tabs[7]:
        section_data_quality(report, db_rows, df_full)


main()
