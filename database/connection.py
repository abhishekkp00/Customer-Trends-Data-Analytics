"""Read-only database connectivity to Neon PostgreSQL.

Security notes
--------------
* ``DATABASE_URL`` is read from the environment (``.env`` via python-dotenv).
* The URL is never logged or put into exception messages.
* Every session is opened with ``default_transaction_read_only = on`` so the
  server rejects any INSERT/UPDATE/DELETE/DDL issued through this engine.
"""
from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()


class DatabaseError(Exception):
    """Raised with a message that is safe to show to end users."""


def get_database_url() -> str:
    url: Optional[str] = os.getenv("DATABASE_URL")
    if not url or not url.strip():
        raise DatabaseError(
            "DATABASE_URL is not set. Copy `.env.example` to `.env` and add "
            "your Neon connection string."
        )
    url = url.strip().strip("'\"")
    # Always use the psycopg (v3) driver explicitly. Plain 'postgresql://' means
    # psycopg2 on SQLAlchemy 2.0 but psycopg on 2.1, so pin it for consistency.
    for legacy in ("postgres://", "postgresql://"):
        if url.startswith(legacy):
            url = "postgresql+psycopg://" + url[len(legacy):]
            break
    return url


def _resolve_hostaddr(url: str) -> Optional[str]:
    """If DB_RESOLVER_DNS is set (e.g. 1.1.1.1), resolve the DB host through
    that DNS server and return the IP for libpq's ``hostaddr``. The original
    hostname is still used for TLS/SNI, so certificate checks are unchanged.
    Useful when the local resolver cannot resolve Neon hostnames."""
    dns_server = os.getenv("DB_RESOLVER_DNS", "").strip()
    if not dns_server:
        return None
    import dns.resolver  # dnspython, only needed for this option
    host = make_url(url).host
    if not host:
        return None
    resolver = dns.resolver.Resolver(configure=False)
    resolver.nameservers = [dns_server]
    resolver.lifetime = 8
    answers = resolver.resolve(host, "A")
    return answers[0].to_text()


def create_readonly_engine() -> Engine:
    """Create a pooled engine whose sessions are read-only."""
    try:
        url = get_database_url()
        connect_args = {
            "connect_timeout": 15,
            "options": "-c default_transaction_read_only=on",
        }
        try:
            hostaddr = _resolve_hostaddr(url)
        except Exception:
            raise DatabaseError(
                "DB_RESOLVER_DNS is set but the database host could not be resolved through it."
            ) from None
        if hostaddr:
            connect_args["hostaddr"] = hostaddr
        return create_engine(
            url,
            pool_pre_ping=True,   # Neon may suspend idle compute
            pool_recycle=300,
            pool_size=2,
            max_overflow=2,
            connect_args=connect_args,
        )
    except DatabaseError:
        raise
    except Exception as exc:  # malformed URL, missing driver, ...
        raise DatabaseError(
            f"Could not configure the database connection ({type(exc).__name__}). "
            "Check the format of DATABASE_URL and that the PostgreSQL driver is installed."
        ) from None


def check_connection(engine: Engine) -> None:
    """Raise DatabaseError (with a safe message) if the DB is unreachable."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise DatabaseError(describe_db_error(exc)) from None


def describe_db_error(exc: BaseException) -> str:
    """Translate a driver error into a credential-free, helpful message."""
    raw = str(getattr(exc, "orig", exc)).lower()
    if "password authentication failed" in raw or "authentication" in raw:
        return "Database authentication failed. Check the credentials in DATABASE_URL."
    if "timeout" in raw or "timed out" in raw:
        return ("The database connection timed out. Neon may be waking from idle - "
                "wait a few seconds and press Refresh.")
    if ("could not translate host" in raw or "name or service not known" in raw
            or "failed to resolve host" in raw or "name resolution" in raw):
        return "Database host could not be resolved. Check the host in DATABASE_URL and your network."
    if "does not exist" in raw and "relation" in raw:
        return "The `customer` table was not found in the database."
    if "ssl" in raw:
        return "Secure connection to the database failed. Ensure the URL includes sslmode=require."
    return f"Database error ({type(exc).__name__}). Check connectivity and try again."
