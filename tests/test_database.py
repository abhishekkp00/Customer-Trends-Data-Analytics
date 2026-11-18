"""Tests for database access: URL handling, read-only setup, queries and error handling.

No test connects to Neon; queries run against an in-memory SQLite engine.
"""
from __future__ import annotations

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from analytics.data_loader import load_customer_data
from config import settings
from database import connection
from database.connection import DatabaseError, check_connection, describe_db_error, get_database_url
from database.queries import count_customer_rows, fetch_customer_table
from tests.conftest import build_customer_table

SECRET = "s3cret-pass"


@pytest.fixture
def sqlite_engine():
    return create_engine("sqlite://")


@pytest.fixture
def engine_with_table(sqlite_engine):
    build_customer_table([dict(purchase_amount=10), dict(purchase_amount=20)]).to_sql(
        settings.TABLE_NAME, sqlite_engine, index=False)
    return sqlite_engine


def test_missing_database_url_has_helpful_message(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(DatabaseError, match="DATABASE_URL is not set"):
        get_database_url()


@pytest.mark.parametrize("scheme", ["postgres://", "postgresql://"])
def test_url_is_pinned_to_psycopg_driver(monkeypatch, scheme):
    monkeypatch.setenv("DATABASE_URL", f"'{scheme}user:{SECRET}@host/db?sslmode=require'")
    assert get_database_url() == "postgresql+psycopg://user:s3cret-pass@host/db?sslmode=require"


def test_engine_sessions_are_read_only(monkeypatch):
    captured = {}
    monkeypatch.setenv("DATABASE_URL", f"postgresql://user:{SECRET}@host/db")
    monkeypatch.delenv("DB_RESOLVER_DNS", raising=False)
    monkeypatch.setattr(connection, "create_engine", lambda url, **kwargs: captured.update(kwargs) or object())
    connection.create_readonly_engine()
    assert "default_transaction_read_only=on" in captured["connect_args"]["options"]
    assert captured["pool_pre_ping"] is True


def test_engine_configuration_error_does_not_leak_credentials(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"not-a-url-{SECRET}")
    monkeypatch.delenv("DB_RESOLVER_DNS", raising=False)
    with pytest.raises(DatabaseError) as error:
        connection.create_readonly_engine()
    assert SECRET not in str(error.value)


def test_unresolvable_dns_server_is_reported_safely(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"postgresql://user:{SECRET}@host/db")
    monkeypatch.setenv("DB_RESOLVER_DNS", "192.0.2.1")
    monkeypatch.setattr(connection, "_resolve_hostaddr", lambda url: 1 / 0)
    with pytest.raises(DatabaseError, match="DB_RESOLVER_DNS") as error:
        connection.create_readonly_engine()
    assert SECRET not in str(error.value)


@pytest.mark.parametrize("raw, expected", [
    ("password authentication failed for user", "authentication failed"),
    ("connection timed out", "timed out"),
    ("could not translate host name", "could not be resolved"),
    ('relation "customer" does not exist', "table was not found"),
    ("SSL SYSCALL error", "Secure connection"),
    ("something else entirely", "Database error"),
])
def test_describe_db_error_messages(raw, expected):
    assert expected in describe_db_error(Exception(raw))


def test_unreachable_database_raises_safe_error(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/missing_dir/{SECRET}.db")
    with pytest.raises(DatabaseError) as error:
        check_connection(engine)
    assert SECRET not in str(error.value)


def test_fetch_customer_table_returns_required_columns(engine_with_table):
    df = fetch_customer_table(engine_with_table)
    assert list(df.columns) == settings.REQUIRED_COLUMNS
    assert len(df) == 2


def test_missing_table_is_reported(sqlite_engine):
    with pytest.raises(DatabaseError, match="table was not found"):
        fetch_customer_table(sqlite_engine)


def test_missing_columns_are_reported(sqlite_engine):
    pd.DataFrame({"customer_id": [1], "age": [30]}).to_sql(settings.TABLE_NAME, sqlite_engine, index=False)
    with pytest.raises(DatabaseError, match="missing expected columns"):
        fetch_customer_table(sqlite_engine)


def test_count_customer_rows(engine_with_table, sqlite_engine):
    assert count_customer_rows(engine_with_table) == 2
    assert count_customer_rows(create_engine("sqlite://")) is None  # no table -> None, not an exception


def test_load_customer_data_adds_segment_and_report(engine_with_table):
    df, report = load_customer_data(engine_with_table)
    assert len(df) == report.row_count == 2
    assert "customer_segment" in df.columns


def test_empty_table_is_rejected(sqlite_engine):
    build_customer_table([dict()]).iloc[0:0].to_sql(settings.TABLE_NAME, sqlite_engine, index=False)
    with pytest.raises(DatabaseError, match="empty or invalid"):
        load_customer_data(sqlite_engine)


def test_database_errors_are_translated(monkeypatch, engine_with_table):
    def failing_query(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception(f"password authentication failed {SECRET}"))

    monkeypatch.setattr(pd, "read_sql_query", failing_query)
    with pytest.raises(DatabaseError) as error:
        fetch_customer_table(engine_with_table)
    assert "authentication failed" in str(error.value)
    assert SECRET not in str(error.value)
