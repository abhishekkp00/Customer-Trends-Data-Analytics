"""Read-only queries against the `customer` table.

Only SELECT statements are issued. Table and column names come from
``config.settings`` constants, never from user input.
"""
from __future__ import annotations

import pandas as pd
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from config import settings
from database.connection import DatabaseError, describe_db_error


def fetch_customer_table(engine: Engine) -> pd.DataFrame:
    """Read the required columns of the customer table.

    Raises DatabaseError with a user-safe message if the table or any
    required column is missing, or if the query fails.
    """
    table = settings.TABLE_NAME
    try:
        inspector = inspect(engine)
        if not inspector.has_table(table):
            raise DatabaseError(f"The `{table}` table was not found in the database.")
        db_columns = {column["name"] for column in inspector.get_columns(table)}
        missing = [c for c in settings.REQUIRED_COLUMNS if c not in db_columns]
        if missing:
            raise DatabaseError(
                f"The `{table}` table is missing expected columns: {', '.join(missing)}."
            )
        columns = ", ".join(f'"{c}"' for c in settings.REQUIRED_COLUMNS)
        with engine.connect() as connection:
            return pd.read_sql_query(text(f'SELECT {columns} FROM "{table}"'), connection)
    except DatabaseError:
        raise
    except SQLAlchemyError as exc:
        raise DatabaseError(describe_db_error(exc)) from None


def count_customer_rows(engine: Engine) -> int | None:
    """Independent COUNT(*) used to reconcile loaded rows; None on failure."""
    try:
        with engine.connect() as connection:
            query = text(f'SELECT COUNT(*) FROM "{settings.TABLE_NAME}"')
            return int(connection.execute(query).scalar_one())
    except SQLAlchemyError:
        return None
