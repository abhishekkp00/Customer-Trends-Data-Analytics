"""Tests for KPI calculations, aggregations, filters and insights (no database needed)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from analytics import insights, metrics
from analytics.data_loader import assign_customer_segment, prepare_dataframe, validate_dataframe
from components.filters import apply_filters, describe_active_filters
from config import settings

SQL_FILE = Path(__file__).resolve().parent.parent / "sql" / "customer_behavior_sql_queries.sql"


def test_kpis(small):
    kpis = metrics.compute_kpis(small)
    assert kpis["total_purchase_amount"] == 400
    assert kpis["total_records"] == 4
    assert kpis["unique_customers"] == 4
    assert kpis["avg_purchase_per_record"] == 100
    assert kpis["avg_spend_per_customer"] == 100
    assert kpis["avg_age"] == 37.5
    assert kpis["avg_rating"] == pytest.approx(4.0)  # NaN ignored: (5+3+4)/3
    assert kpis["subscription_rate"] == 50.0
    assert kpis["discount_rate"] == 50.0


def test_unique_customers_differs_from_records_when_ids_repeat(small):
    duplicated = pd.concat([small, small.iloc[[0]]], ignore_index=True)
    kpis = metrics.compute_kpis(duplicated)
    assert kpis["total_records"] == 5 and kpis["unique_customers"] == 4
    assert kpis["avg_spend_per_customer"] == pytest.approx(500 / 4)
    assert kpis["avg_purchase_per_record"] == pytest.approx(500 / 5)


def test_empty_dataframe_does_not_divide_by_zero(small):
    empty = small.iloc[0:0]
    kpis = metrics.compute_kpis(empty)
    assert kpis["total_records"] == 0 and kpis["unique_customers"] == 0
    assert kpis["avg_purchase_per_record"] is None and kpis["subscription_rate"] is None
    assert set(kpis) == set(metrics.KPI_NAMES)
    assert metrics.group_summary(empty, "category").empty
    assert metrics.discount_rate_by(empty, "category").empty
    assert metrics.subscription_by_segment(empty).empty
    assert metrics.payment_shipping_matrix(empty).empty
    assert metrics.top_products_per_category(empty).empty


def test_all_ratings_missing_gives_none_not_nan(make_df):
    df = make_df([dict(review_rating=np.nan), dict(review_rating=np.nan)])
    assert metrics.compute_kpis(df)["avg_rating"] is None


def test_safe_divide_and_pct():
    assert metrics.safe_divide(1, 0) is None
    assert metrics.safe_divide(1, float("nan")) is None
    assert metrics.pct(1, 4) == 25.0 and metrics.pct(1, 0) is None


def test_segment_boundaries():
    segments = assign_customer_segment(pd.Series([0, 1, 2, 10, 11, 50]))
    assert segments.tolist() == ["New", "New", "Returning", "Returning", "Loyal", "Loyal"]


def test_segment_sql_uses_the_same_thresholds_as_python():
    sql = " ".join(SQL_FILE.read_text().split())
    assert f"previous_purchases <= {settings.NEW_MAX_PREVIOUS_PURCHASES} THEN 'New'" in sql
    assert (f"previous_purchases BETWEEN {settings.NEW_MAX_PREVIOUS_PURCHASES + 1} "
            f"AND {settings.RETURNING_MAX_PREVIOUS_PURCHASES} THEN 'Returning'") in sql
    assert "ELSE 'Loyal'" in sql


def test_group_summary_share_sums_to_100(small):
    summary = metrics.category_summary(small)
    assert summary["share_of_amount_pct"].sum() == pytest.approx(100)
    assert summary.set_index("category").loc["Footwear", "total_amount"] == 250


def test_segment_summary_follows_canonical_order(small):
    assert metrics.segment_summary(small)["customer_segment"].tolist() == ["New", "Returning", "Loyal"]


def test_discount_rate_uses_group_denominator(small):
    rates = metrics.discount_rate_by(small, "category").set_index("category")
    assert rates.loc["Clothing", "discount_rate_pct"] == 50.0
    assert rates.loc["Footwear", "discount_rate_pct"] == 50.0
    assert metrics.discount_rate_by(small, "category", min_records=3).empty


def test_subscription_rate_by_segment(small):
    rates = metrics.subscription_by_segment(small).set_index("customer_segment")
    assert rates.loc["New", "subscription_rate_pct"] == 100.0
    assert rates.loc["Loyal", "subscription_rate_pct"] == 0.0


def test_payment_shipping_matrix_counts_records(small):
    matrix = metrics.payment_shipping_matrix(small)
    assert matrix.loc["Cash", "Express"] == 4


def test_top_products_and_ranking_validation(small):
    top = metrics.top_products(small, "total_amount", n=1)
    assert top.loc[0, "item_purchased"] == "Sandals"
    with pytest.raises(ValueError):
        metrics.top_products(small, "bogus")


def test_top_products_per_category(small):
    top = metrics.top_products_per_category(small, 1)
    assert set(top["category"]) == {"Clothing", "Footwear"} and (top["rank"] == 1).all()


def test_apply_filters_and_or_semantics(small):
    out = apply_filters(small, {"gender": ["Male"], "category": ["Footwear", "Clothing"]})
    assert len(out) == 2
    assert apply_filters(small, {"gender": ["Male"], "category": ["Nope"]}).empty


def test_empty_selections_mean_all_rows(small):
    assert len(apply_filters(small, {"gender": []})) == 4
    assert len(apply_filters(small, {})) == 4
    assert len(apply_filters(small, {column: [] for column, _ in settings.FILTER_SPECS})) == 4


def test_filtering_an_empty_frame_stays_empty(small):
    assert apply_filters(small.iloc[0:0], {"gender": ["Male"]}).empty


def test_describe_active_filters():
    selections = {"gender": [], "category": ["A", "B", "C", "D"]}
    assert describe_active_filters(selections) == ["Product category: A, B, C +1 more"]


def test_validate_flags_problems(small):
    raw = small.drop(columns=["customer_segment"])
    report = validate_dataframe(raw)
    assert report.is_usable and report.customer_id_unique
    bad = pd.concat([small, small.iloc[[0]]], ignore_index=True)
    bad.loc[0, "gender"] = "Other"
    report = validate_dataframe(bad.drop(columns=["customer_segment"]))
    assert not report.customer_id_unique and report.duplicate_customer_ids == 1
    assert report.unexpected_labels["gender"] == ["Other"]
    assert report.missing_values == {"review_rating": 1}  # the one NaN rating is reported
    missing = validate_dataframe(raw.drop(columns=["age"]))
    assert missing.missing_columns == ["age"] and not missing.is_usable


def test_validate_empty_table_is_not_usable(small):
    report = validate_dataframe(small.drop(columns=["customer_segment"]).iloc[0:0])
    assert not report.is_usable and report.row_count == 0


def test_validate_reports_bad_numbers(small):
    raw = small.drop(columns=["customer_segment"]).astype({"purchase_amount": "object"})
    raw.loc[0, "purchase_amount"] = "abc"
    raw.loc[1, "purchase_amount"] = -5
    raw.loc[2, "review_rating"] = 9
    report = validate_dataframe(raw)
    assert report.non_numeric_values == {"purchase_amount": 1}
    assert report.negative_amounts == 1
    assert report.rating_out_of_range == 1


def test_prepare_dataframe_does_not_mutate_input(small):
    raw = small.drop(columns=["customer_segment"])
    before = raw.copy()
    prepare_dataframe(raw)
    pd.testing.assert_frame_equal(raw, before)


def test_insights_insufficient_data_message(small):
    results = insights.generate_insights(small)  # only 4 records
    assert all(not item.supported and "records" in item.message for item in results)


def test_insights_on_empty_data_do_not_raise(small):
    results = insights.generate_insights(small.iloc[0:0])
    assert len(results) == len(insights.INSIGHT_BUILDERS)
    assert all(not item.supported for item in results)


def test_insights_computed_from_data(make_df):
    rows = ([dict(subscription_status="Yes", purchase_amount=80, previous_purchases=20, discount_applied="Yes",
                  category="Clothing", payment_method="Cash", shipping_type="Express")] * 20 +
            [dict(subscription_status="No", purchase_amount=60, previous_purchases=5, discount_applied="No",
                  category="Footwear", item_purchased="Sandals", payment_method="PayPal",
                  shipping_type="Standard")] * 20 +
            [dict(subscription_status="No", purchase_amount=40, previous_purchases=1, discount_applied="No",
                  category="Footwear", item_purchased="Sandals", payment_method="Cash",
                  shipping_type="Standard")] * 12)
    df = make_df(rows)
    segment = insights.highest_spending_segment(df)
    assert segment.supported and "Loyal" in segment.finding and "$80" in segment.metric
    gap = insights.subscriber_spend_gap(df)
    assert gap.supported and "$80" in gap.metric and "$52" in gap.metric  # non-subs: 1680/32 = 52.5
    assert insights.highest_discount_category(df).finding.count("Clothing") == 1
    assert "Cash" in insights.top_payment_method(df).finding
    assert "Standard" in insights.top_shipping_option(df).finding
    assert "Footwear" in insights.most_popular_category(df).finding  # 32 records vs 20
