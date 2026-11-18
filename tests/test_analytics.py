"""Tests for KPI calculations and analytical functions (no database needed)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from analytics import insights, metrics
from analytics.data_loader import assign_customer_segment, prepare_dataframe, validate_dataframe
from components.filters import apply_filters
from config import settings


def make_df(rows: list[dict]) -> pd.DataFrame:
    base = dict(
        customer_id=1, age=30, gender="Male", item_purchased="Blouse", category="Clothing",
        purchase_amount=100, location="Kentucky", size="M", color="Red", season="Winter",
        review_rating=4.0, subscription_status="No", shipping_type="Express", discount_applied="No",
        previous_purchases=5, payment_method="Cash", frequency_of_purchases="Monthly",
        purchase_frequency_days=30, age_group="Adult",
    )
    return prepare_dataframe(pd.DataFrame([{**base, **r, "customer_id": i + 1} for i, r in enumerate(rows)]))


@pytest.fixture
def small() -> pd.DataFrame:
    return make_df([
        dict(purchase_amount=100, age=20, subscription_status="Yes", discount_applied="Yes", review_rating=5.0,
             previous_purchases=1, category="Clothing", gender="Female"),
        dict(purchase_amount=50, age=40, subscription_status="No", discount_applied="No", review_rating=3.0,
             previous_purchases=5, category="Clothing", gender="Male"),
        dict(purchase_amount=200, age=60, subscription_status="No", discount_applied="Yes", review_rating=np.nan,
             previous_purchases=20, category="Footwear", item_purchased="Sandals", gender="Male"),
        dict(purchase_amount=50, age=30, subscription_status="Yes", discount_applied="No", review_rating=4.0,
             previous_purchases=10, category="Footwear", item_purchased="Sandals", gender="Female"),
    ])


def test_kpis(small):
    k = metrics.compute_kpis(small)
    assert k["total_purchase_amount"] == 400
    assert k["total_records"] == 4
    assert k["unique_customers"] == 4
    assert k["avg_purchase_per_record"] == 100
    assert k["avg_age"] == 37.5
    assert k["avg_rating"] == pytest.approx(4.0)           # NaN ignored: (5+3+4)/3
    assert k["subscription_rate"] == 50.0
    assert k["discount_rate"] == 50.0


def test_unique_customers_differs_from_records_when_ids_repeat(small):
    dup = pd.concat([small, small.iloc[[0]]], ignore_index=True)
    k = metrics.compute_kpis(dup)
    assert k["total_records"] == 5 and k["unique_customers"] == 4
    assert k["avg_spend_per_customer"] == pytest.approx(500 / 4)
    assert k["avg_purchase_per_record"] == pytest.approx(500 / 5)


def test_empty_dataframe_does_not_divide_by_zero(small):
    k = metrics.compute_kpis(small.iloc[0:0])
    assert k["total_records"] == 0 and k["unique_customers"] == 0
    assert k["avg_purchase_per_record"] is None and k["subscription_rate"] is None
    assert metrics.group_summary(small.iloc[0:0], "category").empty
    assert metrics.discount_rate_by(small.iloc[0:0], "category").empty


def test_safe_divide_and_pct():
    assert metrics.safe_divide(1, 0) is None
    assert metrics.safe_divide(1, float("nan")) is None
    assert metrics.pct(1, 4) == 25.0 and metrics.pct(1, 0) is None


def test_segment_boundaries():
    s = assign_customer_segment(pd.Series([0, 1, 2, 10, 11, 50]))
    assert s.tolist() == ["New", "New", "Returning", "Returning", "Loyal", "Loyal"]


def test_group_summary_share_sums_to_100(small):
    g = metrics.category_summary(small)
    assert g["share_of_amount_pct"].sum() == pytest.approx(100)
    assert g.set_index("category").loc["Footwear", "total_amount"] == 250


def test_discount_rate_uses_group_denominator(small):
    d = metrics.discount_rate_by(small, "category").set_index("category")
    assert d.loc["Clothing", "discount_rate_pct"] == 50.0
    assert d.loc["Footwear", "discount_rate_pct"] == 50.0
    assert metrics.discount_rate_by(small, "category", min_records=3).empty


def test_top_products_and_ranking_validation(small):
    top = metrics.top_products(small, "total_amount", n=1)
    assert top.loc[0, "item_purchased"] == "Sandals"
    with pytest.raises(ValueError):
        metrics.top_products(small, "bogus")


def test_top_products_per_category(small):
    t = metrics.top_products_per_category(small, 1)
    assert set(t["category"]) == {"Clothing", "Footwear"} and (t["rank"] == 1).all()


def test_apply_filters_and_or_semantics(small):
    out = apply_filters(small, {"gender": ["Male"], "category": ["Footwear", "Clothing"]})
    assert len(out) == 2
    assert len(apply_filters(small, {"gender": []})) == 4          # empty = all
    assert apply_filters(small, {"gender": ["Male"], "category": ["Nope"]}).empty


def test_validate_flags_problems(small):
    report = validate_dataframe(small.drop(columns=["customer_segment"]))
    assert report.is_usable and report.customer_id_unique
    bad = pd.concat([small, small.iloc[[0]]], ignore_index=True)
    bad.loc[0, "gender"] = "Other"
    r = validate_dataframe(bad.drop(columns=["customer_segment"]))
    assert not r.customer_id_unique and r.duplicate_customer_ids == 1
    assert r.unexpected_labels["gender"] == ["Other"]
    assert r.missing_values == {"review_rating": 1}   # the one NaN rating is reported
    missing = validate_dataframe(small.drop(columns=["age"]))
    assert missing.missing_columns == ["age"] and not missing.is_usable


def test_insights_insufficient_data_message(small):
    out = insights.generate_insights(small)           # only 4 records
    assert all(not i.supported and "records" in i.message for i in out)


def test_insights_computed_from_data():
    rows = ([dict(subscription_status="Yes", purchase_amount=80, previous_purchases=20, discount_applied="Yes",
                  category="Clothing", payment_method="Cash", shipping_type="Express")] * 20 +
            [dict(subscription_status="No", purchase_amount=60, previous_purchases=5, discount_applied="No",
                  category="Footwear", item_purchased="Sandals", payment_method="PayPal", shipping_type="Standard")] * 20 +
            [dict(subscription_status="No", purchase_amount=40, previous_purchases=1, discount_applied="No",
                  category="Footwear", item_purchased="Sandals", payment_method="Cash", shipping_type="Standard")] * 12)
    df = make_df(rows)
    seg = insights.highest_spending_segment(df)
    assert seg.supported and "Loyal" in seg.finding and "$80" in seg.metric
    gap = insights.subscriber_spend_gap(df)
    assert gap.supported and "$80" in gap.metric and "$52" in gap.metric   # non-subs: 1680/32 = 52.5
    assert insights.highest_discount_category(df).finding.count("Clothing") == 1
    assert "Cash" in insights.top_payment_method(df).finding
    assert "Standard" in insights.top_shipping_option(df).finding
    pop = insights.most_popular_category(df)
    assert "Footwear" in pop.finding                   # 32 records vs 20
