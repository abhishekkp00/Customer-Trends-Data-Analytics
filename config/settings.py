"""Central configuration: app text, expected schema and business rules."""
from __future__ import annotations

APP_TITLE = "Customer Intelligence | Shopping Behavior & Business Insights"
TABLE_NAME = "customer"
CACHE_TTL_SECONDS = 3600

# Columns the dashboard needs, with the kind of data expected.
NUMERIC_COLUMNS = [
    "customer_id",
    "age",
    "purchase_amount",
    "review_rating",
    "previous_purchases",
    "purchase_frequency_days",
]
CATEGORICAL_COLUMNS = [
    "gender",
    "item_purchased",
    "category",
    "location",
    "size",
    "color",
    "season",
    "subscription_status",
    "shipping_type",
    "discount_applied",
    "payment_method",
    "frequency_of_purchases",
    "age_group",
]
REQUIRED_COLUMNS = NUMERIC_COLUMNS + CATEGORICAL_COLUMNS

# Columns that must never contain nulls (review_rating is allowed a few: the
# cleaning step imputes them, but we do not rely on that).
NON_NULL_COLUMNS = [c for c in REQUIRED_COLUMNS if c != "review_rating"]

# Expected labels for binary / ordinal fields; anything else is flagged.
EXPECTED_LABELS = {
    "gender": {"Male", "Female"},
    "subscription_status": {"Yes", "No"},
    "discount_applied": {"Yes", "No"},
    "age_group": {"Young Adult", "Adult", "Middle-aged", "Senior"},
}

AGE_GROUP_ORDER = ["Young Adult", "Adult", "Middle-aged", "Senior"]

# Customer segmentation. Mirrors Q7 in customer_behavior_sql_queries.sql.
# NOTE: "New" means exactly one previous purchase, i.e. a customer with a
# very short recorded history - not a first-time buyer. 0 is treated as New
# as well so the segmentation is exhaustive if such rows ever appear.
SEGMENT_ORDER = ["New", "Returning", "Loyal"]
SEGMENT_RULES = {
    "New": "0-1 previous purchases",
    "Returning": "2-10 previous purchases",
    "Loyal": "More than 10 previous purchases",
}

# Frequency labels ordered from most to least frequent.
FREQUENCY_ORDER = [
    "Weekly",
    "Bi-Weekly",
    "Fortnightly",
    "Monthly",
    "Quarterly",
    "Every 3 Months",
    "Annually",
]

# Minimum records needed before the dashboard will state a finding.
MIN_RECORDS_FOR_INSIGHT = 30
# Minimum records per group when ranking groups by an average / rate.
MIN_GROUP_SIZE = 10

# Sidebar filters: (column, label)
FILTER_SPECS = [
    ("gender", "Gender"),
    ("age_group", "Age group"),
    ("category", "Product category"),
    ("item_purchased", "Product purchased"),
    ("season", "Season"),
    ("subscription_status", "Subscription status"),
    ("shipping_type", "Shipping type"),
    ("discount_applied", "Discount status"),
    ("payment_method", "Payment method"),
    ("frequency_of_purchases", "Purchase frequency"),
    ("location", "Location"),
]

# Colour palette (consistent across charts).
PALETTE = {
    "primary": "#4F46E5",
    "secondary": "#0EA5E9",
    "accent": "#F59E0B",
    "positive": "#10B981",
    "negative": "#EF4444",
    "muted": "#94A3B8",
}
CATEGORY_COLORS = [
    "#4F46E5", "#0EA5E9", "#10B981", "#F59E0B", "#EC4899",
    "#8B5CF6", "#14B8A6", "#F97316",
]
