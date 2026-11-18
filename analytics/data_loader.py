"""Validate and prepare the customer table loaded from Neon.

The data is not cleaned here: the table is already cleaned upstream (see the
notebook). We only validate it and add one derived field, `customer_segment`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sqlalchemy import Engine

from config import settings
from database.connection import DatabaseError
from database.queries import fetch_customer_table


@dataclass
class DataQualityReport:
    """Result of validating the loaded table."""

    row_count: int = 0
    missing_columns: list[str] = field(default_factory=list)
    missing_values: dict[str, int] = field(default_factory=dict)
    duplicate_rows: int = 0
    duplicate_customer_ids: int = 0
    customer_id_unique: bool = True
    unexpected_labels: dict[str, list[str]] = field(default_factory=dict)
    non_numeric_values: dict[str, int] = field(default_factory=dict)
    negative_amounts: int = 0
    rating_out_of_range: int = 0
    warnings: list[str] = field(default_factory=list)

    @property
    def is_usable(self) -> bool:
        return not self.missing_columns and self.row_count > 0


def assign_customer_segment(previous_purchases: pd.Series) -> pd.Series:
    """Segment customers by previous purchases (rule defined in config.settings)."""
    bins = [
        -np.inf,
        settings.NEW_MAX_PREVIOUS_PURCHASES,
        settings.RETURNING_MAX_PREVIOUS_PURCHASES,
        np.inf,
    ]
    segments = pd.cut(previous_purchases, bins=bins, labels=settings.SEGMENT_ORDER, right=True)
    return segments.astype("object")


def validate_dataframe(df: pd.DataFrame) -> DataQualityReport:
    """Run schema and data-quality checks. Never mutates ``df``."""
    report = DataQualityReport(row_count=len(df))

    report.missing_columns = [c for c in settings.REQUIRED_COLUMNS if c not in df.columns]
    if report.missing_columns:
        return report

    null_counts = df[settings.REQUIRED_COLUMNS].isna().sum()
    report.missing_values = {c: int(n) for c, n in null_counts.items() if n > 0}
    report.duplicate_rows = int(df.duplicated().sum())
    report.duplicate_customer_ids = int(df["customer_id"].duplicated().sum())
    report.customer_id_unique = report.duplicate_customer_ids == 0

    for column in settings.NUMERIC_COLUMNS:
        coerced = pd.to_numeric(df[column], errors="coerce")
        bad = int((coerced.isna() & df[column].notna()).sum())
        if bad:
            report.non_numeric_values[column] = bad

    for column, allowed in settings.EXPECTED_LABELS.items():
        extra = sorted(set(df[column].dropna().astype(str).unique()) - allowed)
        if extra:
            report.unexpected_labels[column] = extra

    amounts = pd.to_numeric(df["purchase_amount"], errors="coerce")
    report.negative_amounts = int((amounts < 0).sum())
    ratings = pd.to_numeric(df["review_rating"], errors="coerce")
    report.rating_out_of_range = int(((ratings < 0) | (ratings > 5)).sum())

    report.warnings = _build_warnings(report)
    return report


def _build_warnings(report: DataQualityReport) -> list[str]:
    """Human-readable warnings shown in the data-quality tab."""
    warnings = []
    if report.row_count == 0:
        warnings.append("The customer table is empty.")
    if not report.customer_id_unique:
        warnings.append(
            f"{report.duplicate_customer_ids:,} duplicate customer IDs found - unique "
            "customer counts and record counts will differ."
        )
    if report.duplicate_rows:
        warnings.append(f"{report.duplicate_rows:,} fully duplicated rows found.")
    for column, n in report.missing_values.items():
        warnings.append(f"{n:,} missing values in `{column}`; they are excluded from averages.")
    for column, n in report.non_numeric_values.items():
        warnings.append(f"{n:,} non-numeric values in `{column}`.")
    for column, labels in report.unexpected_labels.items():
        warnings.append(f"Unexpected labels in `{column}`: {', '.join(labels)}.")
    if report.negative_amounts:
        warnings.append(f"{report.negative_amounts:,} negative purchase amounts found.")
    if report.rating_out_of_range:
        warnings.append(f"{report.rating_out_of_range:,} ratings outside the 0-5 range.")
    return warnings


def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce dtypes (no cleaning) and add the customer segment."""
    prepared = df.copy()
    for column in settings.NUMERIC_COLUMNS:
        prepared[column] = pd.to_numeric(prepared[column], errors="coerce")
    for column in settings.CATEGORICAL_COLUMNS:
        prepared[column] = prepared[column].astype("string").astype("object")
    prepared["customer_segment"] = assign_customer_segment(prepared["previous_purchases"])
    return prepared


def load_customer_data(engine: Engine) -> tuple[pd.DataFrame, DataQualityReport]:
    """Read the customer table (read-only), validate and prepare it.

    Raises DatabaseError with a user-safe message on any failure.
    """
    raw = fetch_customer_table(engine)
    report = validate_dataframe(raw)
    if not report.is_usable:
        raise DatabaseError("The customer table is empty or invalid.")
    return prepare_dataframe(raw), report
