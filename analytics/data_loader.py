"""Load the `customer` table from Neon and validate it.

Only SELECT statements are issued. The data is *not* cleaned here - the
table is already cleaned upstream (see the notebook). We only validate it and
add one derived field (`customer_segment`) that mirrors SQL query Q7.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from config import settings
from database.connection import DatabaseError, describe_db_error


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
    """Segment by previous purchases (same rule as SQL Q7).

    New: <= 1, Returning: 2-10, Loyal: > 10.
    """
    bins = [-np.inf, 1, 10, np.inf]
    return pd.cut(
        previous_purchases, bins=bins, labels=settings.SEGMENT_ORDER, right=True
    ).astype("object")


def validate_dataframe(df: pd.DataFrame) -> DataQualityReport:
    """Run schema and data-quality checks. Never mutates ``df``."""
    report = DataQualityReport(row_count=len(df))

    report.missing_columns = [c for c in settings.REQUIRED_COLUMNS if c not in df.columns]
    if report.missing_columns:
        return report

    nulls = df[settings.REQUIRED_COLUMNS].isna().sum()
    report.missing_values = {c: int(n) for c, n in nulls.items() if n > 0}
    report.duplicate_rows = int(df.duplicated().sum())
    report.duplicate_customer_ids = int(df["customer_id"].duplicated().sum())
    report.customer_id_unique = report.duplicate_customer_ids == 0

    for col in settings.NUMERIC_COLUMNS:
        coerced = pd.to_numeric(df[col], errors="coerce")
        bad = int((coerced.isna() & df[col].notna()).sum())
        if bad:
            report.non_numeric_values[col] = bad

    for col, allowed in settings.EXPECTED_LABELS.items():
        seen = set(df[col].dropna().astype(str).unique())
        extra = sorted(seen - allowed)
        if extra:
            report.unexpected_labels[col] = extra

    amounts = pd.to_numeric(df["purchase_amount"], errors="coerce")
    report.negative_amounts = int((amounts < 0).sum())
    ratings = pd.to_numeric(df["review_rating"], errors="coerce")
    report.rating_out_of_range = int(((ratings < 0) | (ratings > 5)).sum())

    # Human-readable warnings surfaced in the dashboard's data-quality panel.
    if report.row_count == 0:
        report.warnings.append("The customer table is empty.")
    if not report.customer_id_unique:
        report.warnings.append(
            f"{report.duplicate_customer_ids:,} duplicate customer IDs found - unique "
            "customer counts and record counts will differ."
        )
    if report.duplicate_rows:
        report.warnings.append(f"{report.duplicate_rows:,} fully duplicated rows found.")
    for col, n in report.missing_values.items():
        report.warnings.append(f"{n:,} missing values in `{col}`; they are excluded from averages.")
    for col, n in report.non_numeric_values.items():
        report.warnings.append(f"{n:,} non-numeric values in `{col}`.")
    for col, labels in report.unexpected_labels.items():
        report.warnings.append(f"Unexpected labels in `{col}`: {', '.join(labels)}.")
    if report.negative_amounts:
        report.warnings.append(f"{report.negative_amounts:,} negative purchase amounts found.")
    if report.rating_out_of_range:
        report.warnings.append(f"{report.rating_out_of_range:,} ratings outside the 0-5 range.")
    return report


def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Type-safe preparation (no cleaning): coerce dtypes, add segment."""
    out = df.copy()
    for col in settings.NUMERIC_COLUMNS:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    for col in settings.CATEGORICAL_COLUMNS:
        out[col] = out[col].astype("string").astype("object")
    out["customer_segment"] = assign_customer_segment(out["previous_purchases"])
    return out


def load_customer_data(engine: Engine) -> tuple[pd.DataFrame, DataQualityReport]:
    """Read the whole customer table (read-only) and validate it.

    Raises DatabaseError with a user-safe message on any failure.
    """
    table = settings.TABLE_NAME
    try:
        insp = inspect(engine)
        if not insp.has_table(table):
            raise DatabaseError(f"The `{table}` table was not found in the database.")
        db_columns = {c["name"] for c in insp.get_columns(table)}
        missing = [c for c in settings.REQUIRED_COLUMNS if c not in db_columns]
        if missing:
            raise DatabaseError(
                f"The `{table}` table is missing expected columns: {', '.join(missing)}."
            )
        cols = ", ".join(f'"{c}"' for c in settings.REQUIRED_COLUMNS)
        # Identifiers come from our own constants (never user input).
        query = text(f'SELECT {cols} FROM "{table}"')
        with engine.connect() as conn:
            df = pd.read_sql_query(query, conn)
    except DatabaseError:
        raise
    except SQLAlchemyError as exc:
        raise DatabaseError(describe_db_error(exc)) from None

    report = validate_dataframe(df)
    if not report.is_usable:
        raise DatabaseError("The customer table is empty or invalid.")
    return prepare_dataframe(df), report


def database_row_count(engine: Engine) -> Optional[int]:
    """Independent COUNT(*) for reconciliation; returns None on failure."""
    try:
        with engine.connect() as conn:
            return int(conn.execute(text(f'SELECT COUNT(*) FROM "{settings.TABLE_NAME}"')).scalar_one())
    except SQLAlchemyError:
        return None
