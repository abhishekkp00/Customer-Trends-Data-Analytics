"""Shared test fixtures: synthetic customer data (no database, no CSV)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from analytics.data_loader import prepare_dataframe

BASE_ROW = dict(
    customer_id=1, age=30, gender="Male", item_purchased="Blouse", category="Clothing",
    purchase_amount=100, location="Kentucky", size="M", color="Red", season="Winter",
    review_rating=4.0, subscription_status="No", shipping_type="Express", discount_applied="No",
    previous_purchases=5, payment_method="Cash", frequency_of_purchases="Monthly",
    purchase_frequency_days=30, age_group="Adult",
)


def build_customer_table(rows: list[dict]) -> pd.DataFrame:
    """Raw table as stored in the database (before ``prepare_dataframe``)."""
    return pd.DataFrame([{**BASE_ROW, **row, "customer_id": i + 1} for i, row in enumerate(rows)])


@pytest.fixture
def make_df():
    """Factory: list of row overrides -> prepared customer DataFrame."""
    return lambda rows: prepare_dataframe(build_customer_table(rows))


@pytest.fixture
def small(make_df) -> pd.DataFrame:
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


@pytest.fixture
def dashboard_table() -> pd.DataFrame:
    """Raw 160-row table with enough variety for every tab and insight to render."""
    rng = np.random.default_rng(7)
    items = {"Clothing": ["Blouse", "Pants"], "Footwear": ["Sandals", "Sneakers"], "Accessories": ["Hat", "Scarf"]}
    rows = []
    for i in range(160):
        category = list(items)[i % 3]
        rows.append(dict(
            category=category,
            item_purchased=items[category][(i // 3) % 2],
            gender=["Male", "Female"][i % 2],
            age=int(rng.integers(18, 70)),
            age_group=["Young Adult", "Adult", "Middle-aged", "Senior"][i % 4],
            purchase_amount=int(rng.integers(20, 100)),
            review_rating=round(float(rng.uniform(2.5, 5)), 1),
            location=["Kentucky", "Montana", "Ohio", "Texas", "Utah", "Maine"][i % 6],
            season=["Winter", "Spring", "Summer", "Fall"][i % 4],
            subscription_status=["Yes", "No"][i % 5 == 0],
            discount_applied=["Yes", "No"][i % 3 == 0],
            shipping_type=["Express", "Standard", "Free Shipping"][i % 3],
            payment_method=["Cash", "PayPal", "Credit Card"][i % 3 if i % 2 else 0],
            previous_purchases=int(rng.integers(1, 50)),
            frequency_of_purchases=["Weekly", "Monthly", "Quarterly"][i % 3],
        ))
    return build_customer_table(rows)
