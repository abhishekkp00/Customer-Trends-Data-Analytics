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

# Expected labels for binary / ordinal fields; anything else is flagged.
EXPECTED_LABELS = {
    "gender": {"Male", "Female"},
    "subscription_status": {"Yes", "No"},
    "discount_applied": {"Yes", "No"},
    "age_group": {"Young Adult", "Adult", "Middle-aged", "Senior"},
}

AGE_GROUP_ORDER = ["Young Adult", "Adult", "Middle-aged", "Senior"]

# Customer segmentation by the `previous_purchases` field. This is the single
# definition used by the dashboard; Q7 in sql/customer_behavior_sql_queries.sql
# uses the same thresholds.
#   New:       previous_purchases <= NEW_MAX_PREVIOUS_PURCHASES
#   Returning: up to RETURNING_MAX_PREVIOUS_PURCHASES
#   Loyal:     more than RETURNING_MAX_PREVIOUS_PURCHASES
# "New" means a very short recorded history, not necessarily a first-time
# buyer. Zero is included in New so the segmentation covers every row.
NEW_MAX_PREVIOUS_PURCHASES = 1
RETURNING_MAX_PREVIOUS_PURCHASES = 10
SEGMENT_ORDER = ["New", "Returning", "Loyal"]
SEGMENT_RULES = {
    "New": f"0-{NEW_MAX_PREVIOUS_PURCHASES} previous purchases",
    "Returning": f"{NEW_MAX_PREVIOUS_PURCHASES + 1}-{RETURNING_MAX_PREVIOUS_PURCHASES} previous purchases",
    "Loyal": f"More than {RETURNING_MAX_PREVIOUS_PURCHASES} previous purchases",
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
    "accent": "#F59E0B",
    "muted": "#94A3B8",
}
CATEGORY_COLORS = [
    "#4F46E5", "#0EA5E9", "#10B981", "#F59E0B", "#EC4899",
    "#8B5CF6", "#14B8A6", "#F97316",
]
