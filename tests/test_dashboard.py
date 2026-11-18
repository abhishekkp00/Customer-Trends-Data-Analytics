"""Dashboard tests: the real ``app.py`` is run headlessly with Streamlit's AppTest.

The database layer is replaced by synthetic data, so nothing here touches Neon.
Module-boundary tests (import cycles, layering, no CSV source) read the source files.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from analytics import data_loader
from config import settings
from database import connection, queries
from database.connection import DatabaseError

ROOT = Path(__file__).resolve().parent.parent
APP_FILE = ROOT / "app.py"
PACKAGES = ["analytics", "components", "dashboard", "database", "config"]
EXPECTED_TABS = 8


@pytest.fixture
def app(monkeypatch, dashboard_table):
    """Factory returning a fresh AppTest whose data comes from ``dashboard_table``."""
    st.cache_data.clear()
    st.cache_resource.clear()
    monkeypatch.setattr(connection, "create_readonly_engine", lambda: object())
    monkeypatch.setattr(connection, "check_connection", lambda engine: None)
    monkeypatch.setattr(data_loader, "load_customer_data", lambda engine: (
        data_loader.prepare_dataframe(dashboard_table), data_loader.validate_dataframe(dashboard_table)))
    monkeypatch.setattr(queries, "count_customer_rows", lambda engine: len(dashboard_table))
    return lambda: AppTest.from_file(str(APP_FILE), default_timeout=120)


def sidebar_count(at: AppTest) -> str:
    return next(m.value for m in at.sidebar.metric if m.label == "Records matching filters")


def test_every_dashboard_section_renders(app):
    at = app().run()
    assert not at.exception
    assert not at.error
    assert len(at.tabs) == EXPECTED_TABS
    assert len(at.get("plotly_chart")) >= 20
    assert sidebar_count(at) == "160 / 160"
    assert any(m.label == "Rows loaded" and m.value == "160" for m in at.metric)


@pytest.mark.parametrize("column, label", settings.FILTER_SPECS)
def test_each_filter_narrows_data_without_errors(app, column, label):
    at = app().run()
    first_option = at.sidebar.multiselect(key=f"flt_{column}").options[0]
    at.sidebar.multiselect(key=f"flt_{column}").set_value([first_option]).run()
    assert not at.exception
    shown, total = (int(part.replace(",", "")) for part in sidebar_count(at).split(" / "))
    assert 0 < shown < total


def test_empty_selection_shows_message_instead_of_error(app):
    at = app().run()
    at.sidebar.multiselect(key="flt_category").set_value(["Clothing"])
    at.sidebar.multiselect(key="flt_item_purchased").set_value(["Sandals"])
    at.run()
    assert not at.exception
    assert sidebar_count(at).startswith("0 /")
    assert any("No records match" in warning.value for warning in at.warning)
    assert len(at.tabs) == 0


def test_tiny_selection_still_renders(app):
    at = app().run()
    at.sidebar.multiselect(key="flt_location").set_value(["Utah"])
    at.sidebar.multiselect(key="flt_item_purchased").set_value(["Hat"])
    at.sidebar.multiselect(key="flt_season").set_value(["Fall"])
    at.run()
    assert not at.exception


def test_reset_button_clears_filters(app):
    at = app().run()
    at.sidebar.multiselect(key="flt_gender").set_value(["Male"]).run()
    assert sidebar_count(at).split(" / ")[0] != "160"
    at.sidebar.button(key="reset_filters_btn").click().run()
    assert sidebar_count(at) == "160 / 160"


def test_refresh_button_reloads_data(app):
    at = app().run()
    at.sidebar.button(key="refresh_btn").click().run()
    assert not at.exception
    assert len(at.tabs) == EXPECTED_TABS


@pytest.mark.parametrize("error, expected", [
    (DatabaseError("Database host could not be resolved."), "Could not load data: Database host could not be resolved."),
    (RuntimeError("password=hunter2"), "Unexpected error while loading data (RuntimeError)"),
])
def test_load_failures_show_safe_message(app, monkeypatch, error, expected):
    def failing_loader(engine):
        raise error

    monkeypatch.setattr(data_loader, "load_customer_data", failing_loader)
    at = app().run()
    assert not at.exception
    assert len(at.error) == 1 and at.error[0].value.startswith(expected)
    assert "hunter2" not in " ".join(e.value for e in at.error)
    assert len(at.tabs) == 0


def source_files(package: str) -> list[Path]:
    return sorted((ROOT / package).glob("*.py"))


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
            modules.update(f"{node.module}.{alias.name}" for alias in node.names)
    return modules


def internal_import_graph() -> dict[str, set[str]]:
    all_modules = {f"{p}.{f.stem}" for p in PACKAGES for f in source_files(p) if f.stem != "__init__"}
    graph = {}
    for package in PACKAGES:
        for path in source_files(package):
            name = package if path.stem == "__init__" else f"{package}.{path.stem}"
            graph[name] = imported_modules(path) & all_modules
    return graph


def test_no_circular_imports():
    graph = internal_import_graph()
    visiting, done = [], set()

    def visit(module: str) -> None:
        assert module not in visiting, f"circular import: {' -> '.join(visiting[visiting.index(module):] + [module])}"
        if module in done:
            return
        visiting.append(module)
        for dependency in graph.get(module, ()):
            visit(dependency)
        visiting.pop()
        done.add(module)

    for module in graph:
        visit(module)


@pytest.mark.parametrize("package, forbidden", [
    ("analytics", {"streamlit", "plotly", "components", "dashboard"}),
    ("database", {"streamlit", "plotly", "analytics", "components", "dashboard"}),
    ("config", {"streamlit", "plotly", "analytics", "components", "dashboard", "database"}),
    ("components", {"database", "dashboard"}),
    ("dashboard", {"database"}),
])
def test_layers_do_not_import_across_boundaries(package, forbidden):
    for path in source_files(package):
        roots = {module.split(".")[0] for module in imported_modules(path)}
        assert not roots & forbidden, f"{path.relative_to(ROOT)} imports {sorted(roots & forbidden)}"


def test_chart_builders_do_not_query_the_database():
    assert "database" not in {m.split(".")[0] for m in imported_modules(ROOT / "components" / "charts.py")}


def test_dashboard_reads_neon_not_the_csv():
    for package in ["analytics", "components", "dashboard", "database"]:
        for path in source_files(package):
            text = path.read_text()
            assert "read_csv" not in text and ".csv" not in text, path
    app_source = APP_FILE.read_text()
    assert "read_csv" not in app_source and ".csv" not in app_source
    assert "load_customer_data(engine)" in app_source and "create_readonly_engine" in app_source
