# Customer Intelligence — Shopping Behavior & Business Insights

> An end-to-end data analytics project: cloud PostgreSQL → Python analytics pipeline → interactive Streamlit dashboard. Built for a retail dataset of **3,900 customer purchase records**, it answers real business questions through 8 interactive tabs, 20+ Plotly charts, 7 auto-generated insights, and an 11-filter sidebar — all live from a Neon cloud database.

[![Python](https://img.shields.io/badge/Python-3.12-4F46E5?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.50+-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io)
[![PostgreSQL](https://img.shields.io/badge/Neon_PostgreSQL-cloud-0EA5E9?style=flat-square&logo=postgresql&logoColor=white)](https://neon.tech)
[![Plotly](https://img.shields.io/badge/Plotly-5.24+-3D4DB7?style=flat-square&logo=plotly&logoColor=white)](https://plotly.com)
[![Tests](https://img.shields.io/badge/Tests-71_passed-10B981?style=flat-square&logo=pytest&logoColor=white)](tests/)

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Solution Overview](#solution-overview)
3. [Dataset](#dataset)
4. [Architecture](#architecture)
5. [Project Structure](#project-structure)
6. [Tech Stack](#tech-stack)
7. [Dashboard Screenshots](#dashboard-screenshots)
8. [SQL Analysis](#sql-analysis)
9. [Key Insights](#key-insights)
10. [Analytical Safeguards](#analytical-safeguards)
11. [Run Locally](#run-locally)
12. [Testing](#testing)
13. [Design Decisions](#design-decisions)

---

## Problem Statement

Retail businesses collect large volumes of customer transaction data but often lack the tooling to explore it interactively. Business questions like *"Which customer segments spend the most?"*, *"Do subscribers actually spend more?"*, or *"Which products carry the highest discount dependence?"* require either one-off SQL queries or static reports — neither of which enables a business analyst to drill down on the fly.

**The goal:** build a production-quality, interactive analytics dashboard that:
- Connects live to a cloud database (no CSV files at runtime)
- Answers demographic, product, subscription, discount, and payment questions
- Lets any team member filter the data and see every chart and KPI update instantly
- Surfaces auto-generated, caveat-aware business insights from the filtered slice
- Validates data quality automatically and surfaces issues

---

## Solution Overview

A fully modular **Streamlit + Plotly** dashboard backed by **Neon PostgreSQL**. The pipeline is:

1. **EDA & Feature Engineering** — Jupyter notebook (`notebooks/`) explores the raw CSV, engineers `age_group`, cleans nulls, and uploads the cleaned table to Neon.
2. **Cloud Database** — The `customer` table lives in Neon; the dashboard reads it via a pooled, read-only SQLAlchemy engine.
3. **Analytics Layer** — Pure Python functions compute KPIs, group summaries, segment distributions, payment/shipping matrices, and discount rates from the filtered DataFrame.
4. **Insights Engine** — Seven business insights are generated live from the current filter selection, each with a *finding*, *metric*, *why it matters*, *recommendation*, and *caveat*.
5. **Interactive Dashboard** — 8 tab modules render all charts and KPIs; an 11-filter sidebar drives the entire view without a page reload.

---

## Dataset

| Property | Value |
|---|---|
| Source | [Consumer Behavior and Shopping Habits Dataset](https://www.kaggle.com/datasets/zeesolver/consumer-behavior-and-shopping-habits-dataset) (Kaggle) |
| Records | 3,900 customer purchase records |
| Customers | 3,900 unique customer IDs |
| Features (raw) | 18 columns |
| Features (after engineering) | 19 columns (`age_group` added) |
| Storage | Neon PostgreSQL — `customer` table |

**Key columns:**

| Column | Type | Description |
|---|---|---|
| `customer_id` | int | Unique customer identifier |
| `age` | int | Customer age |
| `age_group` | text | Engineered quartile group (Young Adult / Adult / Middle-aged / Senior) |
| `gender` | text | Male / Female |
| `location` | text | US state |
| `category` | text | Product category (Clothing, Accessories, Footwear, Outerwear) |
| `item_purchased` | text | Specific product name |
| `purchase_amount` | float | Purchase value in USD |
| `review_rating` | float | 1–5 customer review (nullable) |
| `previous_purchases` | int | Count of prior recorded purchases |
| `subscription_status` | text | Yes / No |
| `discount_applied` | text | Yes / No |
| `payment_method` | text | Credit Card, PayPal, Cash, etc. |
| `shipping_type` | text | Standard, Express, Free Shipping, etc. |
| `frequency_of_purchases` | text | Weekly, Monthly, Annually, etc. |
| `season` | text | Spring, Summer, Fall, Winter |

---

## Architecture

![System Architecture](docs/screenshots/architecture.jpg)

The codebase follows a strict **layered architecture** — each layer may only import from layers below it:

```
config  ──►  database  ──►  analytics  ──►  components  ──►  dashboard  ──►  app.py
```

- **`config/`** — constants only; no imports from any other internal package
- **`database/`** — connectivity and read-only SQL; no analytics or UI
- **`analytics/`** — pure Python functions; no database, no Streamlit, no Plotly
- **`components/`** — Plotly figure builders and Streamlit widgets; no database
- **`dashboard/`** — tab modules that call analytics and components; no direct DB access
- **`app.py`** — orchestrator only (95 lines); wires all layers together

A test (`test_no_circular_imports`) and a parametrised boundary test (`test_layers_do_not_import_across_boundaries`) enforce these rules automatically on every test run.

---

## Project Structure

```
Customer-Trend-Data-Analysis/
│
├── app.py                          # Entry point (95 lines — orchestration only)
│
├── config/
│   └── settings.py                 # All constants: schema, thresholds, colours, filters
│
├── database/
│   ├── connection.py               # Read-only SQLAlchemy engine, error sanitisation
│   └── queries.py                  # Schema introspection + SELECT; no analytics logic
│
├── analytics/
│   ├── data_loader.py              # Validate → fetch → prepare pipeline
│   ├── metrics.py                  # Pure aggregation functions (KPIs, summaries, rates)
│   └── insights.py                 # 7 auto-generated business insights engine
│
├── components/
│   ├── charts.py                   # Plotly figure builders (hbar, vbar, donut, heatmap…)
│   ├── filters.py                  # Sidebar filter widgets + apply/describe logic
│   └── kpi_cards.py                # KPI card renderer + formatting helpers
│
├── dashboard/                      # One module per dashboard tab
│   ├── styles.py                   # CSS injection, hero banner, finding callout
│   ├── overview.py                 # Tab 1 — KPIs + amount histogram + category treemap
│   ├── demographics.py             # Tab 2 — Gender, age group, location
│   ├── products.py                 # Tab 3 — Category, product ranking, scatter, box plots
│   ├── subscriptions.py            # Tab 4 — Subscriber vs non-subscriber, segments
│   ├── discounts.py                # Tab 5 — Discount usage, spend comparison
│   ├── purchasing.py               # Tab 6 — Shipping, payment, frequency, heatmap
│   ├── insights.py                 # Tab 7 — 7 auto-generated insight cards
│   └── data_quality.py             # Tab 8 — Row reconciliation, schema checks
│
├── tests/
│   ├── conftest.py                 # Shared fixtures: synthetic DataFrame + SQLite engine
│   ├── test_analytics.py           # Unit tests for metrics, loader, filters, insights
│   ├── test_database.py            # Integration tests for queries and error sanitisation
│   └── test_dashboard.py           # Streamlit AppTest: all tabs, all filters, error paths
│
├── notebooks/
│   └── Customer_Shopping_Behavior_Analysis.ipynb   # EDA + feature engineering + upload
│
├── sql/
│   └── customer_behavior_sql_queries.sql           # 9 exploratory SQL queries (Q1–Q9)
│
├── data_source/
│   └── customer_shopping_behavior.csv              # Raw dataset (source for notebook only)
│
├── requirements.txt
├── pytest.ini
└── .env.example
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Language** | Python 3.12 | Core language |
| **Dashboard** | Streamlit ≥ 1.50 | Interactive web UI with live filtering |
| **Charts** | Plotly ≥ 5.24 | Interactive visualisations (20+ chart types) |
| **Data** | Pandas ≥ 2.2, NumPy ≥ 1.26 | DataFrame processing and aggregations |
| **Database** | PostgreSQL (Neon cloud) | Hosted relational database, serverless |
| **ORM / Driver** | SQLAlchemy ≥ 2.0 + psycopg v3 | Pooled, read-only engine; schema introspection |
| **EDA** | Jupyter Notebook, Matplotlib | Exploratory analysis and feature engineering |
| **Config** | python-dotenv ≥ 1.0 | Secure credential management from `.env` |
| **DNS** | dnspython ≥ 2.4 | Optional custom DNS resolver for Neon hostnames |
| **Testing** | pytest ≥ 8.0, Streamlit AppTest | 71 tests — unit, integration, and UI |

---

## Dashboard Screenshots

### Executive Overview — 8 KPIs + Distribution + Treemap
![Executive Overview tab showing KPI cards and purchase distribution](docs/screenshots/overview.jpg)

The overview tab renders **8 KPI cards** (Total Records, Unique Customers, Total Purchase Amount, Average per Record, Average Age, Average Rating, Subscription Rate, Discount Rate), a purchase amount histogram, and a category revenue treemap. When filters are active, each KPI also shows the unfiltered "All data" value for comparison.

---

### Customer Demographics — Gender, Age, Location
![Demographics tab showing gender donut, age bars, and location chart](docs/screenshots/demographics.jpg)

Breaks down purchase records and amounts by gender, age quartile group, and US state. Each section includes a **key-finding callout** that dynamically updates with the filtered data. The location bar chart uses a slider to show 5–30 states.

---

### Product & Category — Ranking, Treemap, Popularity vs Rating
![Products tab showing category bars, product ranking, scatter, and box plots](docs/screenshots/products.jpg)

Category performance charts, a **dynamically sortable product ranking table** (by records, total amount, average amount, or average rating), a bubble scatter chart of popularity vs rating, and per-product purchase amount distributions via box plots.

---

### Insights & Recommendations — Live-generated from Filters
![Insights tab showing 4 structured insight cards](docs/screenshots/insights.jpg)

Seven insights are computed from the active filter selection. Each card surfaces:
- **What the data shows** — the key finding
- **Metric & comparison** — supporting numbers with context
- **Why it matters** — business relevance
- **Recommendation** — a concrete action
- **Caveat** — a methodological warning to prevent overconfidence

Insights are **suppressed when data is insufficient** (< 30 records, or < 10 per group for ranking insights).

---

## SQL Analysis

Nine exploratory SQL queries are in [`sql/customer_behavior_sql_queries.sql`](sql/customer_behavior_sql_queries.sql):

| # | Business Question |
|---|---|
| Q1 | Total revenue: Male vs Female customers |
| Q2 | Discount users who still spent above average |
| Q3 | Top 5 products by average review rating |
| Q4 | Average spend: Standard vs Express shipping |
| Q5 | Do subscribers spend more? Average and total revenue comparison |
| Q6 | Top 5 products by discount usage rate |
| Q7 | Customer segmentation: New / Returning / Loyal (rule matches `config/settings.py`) |
| Q8 | Top 3 products per category (window function with `ROW_NUMBER`) |
| Q9 | Repeat buyers (> 5 purchases) — are they more likely to subscribe? |

The segmentation rule in Q7 uses `previous_purchases <= 1` for **New**, `2–10` for **Returning**, `> 10` for **Loyal** — identical to the `NEW_MAX_PREVIOUS_PURCHASES` and `RETURNING_MAX_PREVIOUS_PURCHASES` constants in `config/settings.py`, enforced by a dedicated test.

---

## Key Insights

The following are representative findings from the full dataset (all 3,900 records, no filters applied):

| Insight | Finding |
|---|---|
| **Highest-spending segment** | Loyal customers (> 10 previous purchases) have the highest average purchase per record |
| **Most popular category** | Clothing leads in purchase record count and total purchase amount |
| **Best-rated product** | Determined per run from products with ≥ 10 records; avoids small-sample bias |
| **Discount dependence** | Footwear and Accessories have the highest share of discounted purchases |
| **Subscriber spend gap** | Subscribers and non-subscribers have comparable average basket sizes (see the dashboard for the exact current figures) |
| **Top payment method** | Credit Card is the most frequently used payment method |
| **Top shipping option** | Free Shipping is the most chosen shipping type |

> All insights include a **caveat** — e.g. the subscriber spend comparison is associational, not causal. The dataset has no timestamps, so there are no time trends or cohort analyses.

---

## Analytical Safeguards

The dashboard applies several safeguards to prevent misleading conclusions:

| Safeguard | Implementation |
|---|---|
| **Schema validation** | `validate_dataframe()` checks required columns, numeric ranges, and expected categorical labels before any chart is drawn |
| **Empty-state handling** | Every chart builder returns an empty figure placeholder rather than raising an exception |
| **Safe division** | `safe_divide()` and `pct()` return `None` or `0` instead of `ZeroDivisionError` |
| **Minimum group sizes** | Ranking insights require ≥ 10 records per group; overall insights require ≥ 30 records |
| **Group-level denominators** | Discount and subscription rates use the group's own record count, not the total, so groups of different sizes are comparable |
| **Credential sanitisation** | `describe_db_error()` strips passwords and hostnames from all exception messages before they reach the UI |
| **Read-only engine** | Every session opens with `default_transaction_read_only = on` — the server rejects any write |
| **Duplicate/ID checks** | `DataQualityReport` flags duplicate rows and non-unique customer IDs in the Data Quality tab |

---

## Run Locally

**Requirements:** Python 3.10+, a Neon account with the `customer` table loaded.

```bash
# 1. Clone
git clone https://github.com/abhishekkp00/Customer-Trends-Data-Analytics.git
cd Customer-Trends-Data-Analytics

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure the database
cp .env.example .env
# Edit .env and set your Neon DATABASE_URL:
# DATABASE_URL=postgresql://USER:PASSWORD@HOST.neon.tech/DBNAME?sslmode=require

# 5. Run the dashboard
streamlit run app.py
```

The app opens at `http://localhost:8501`.

**DNS troubleshooting:** if you see *"Database host could not be resolved"* but your URL is correct, add this to `.env`:
```
DB_RESOLVER_DNS=1.1.1.1
```
This resolves the Neon hostname through Cloudflare's DNS while keeping TLS/SNI checks unchanged.

**Notebook:** to re-run the EDA and re-upload the data, launch Jupyter from the `notebooks/` folder:
```bash
cd notebooks
jupyter lab
```
> ⚠️ The notebook's last cell uploads with `if_exists="replace"`, which replaces the entire `customer` table. Only run it deliberately.

---

## Testing

The test suite requires **no live database or network access** — it uses a synthetic DataFrame fixture and in-memory SQLite.

```bash
# Run all 71 tests
python -m pytest -v

# Run a specific module
python -m pytest tests/test_analytics.py -v
python -m pytest tests/test_database.py -v
python -m pytest tests/test_dashboard.py -v
```

| File | Tests | What is covered |
|---|---|---|
| `test_analytics.py` | 25 | KPI computation, segment boundaries, discount/subscription rates, payment matrix, filter logic, insights engine, data validation |
| `test_database.py` | 21 | URL pinning, read-only enforcement, error sanitisation (6 message patterns), schema introspection, loader pipeline |
| `test_dashboard.py` | 25 | Full AppTest render (20+ charts, 8 tabs), all 11 filters, empty-selection message, reset/refresh buttons, 2 error paths, circular import check, 5 layer boundary checks, CSV usage check |

**Selected test highlights:**

```python
# Segment thresholds in SQL match the Python constants exactly
def test_segment_sql_uses_the_same_thresholds_as_python():
    sql = Path("sql/customer_behavior_sql_queries.sql").read_text()
    assert f"<= {settings.NEW_MAX_PREVIOUS_PURCHASES}" in sql

# Credentials never reach the UI
def test_database_errors_are_translated(monkeypatch, engine_with_table):
    # inject a real OperationalError with a password in its message
    with pytest.raises(DatabaseError) as error:
        fetch_customer_table(engine_with_table)
    assert SECRET not in str(error.value)   # password scrubbed

# Architecture: analytics may never import dashboard or streamlit
def test_layers_do_not_import_across_boundaries(package, forbidden):
    for path in source_files(package):
        roots = {module.split(".")[0] for module in imported_modules(path)}
        assert not roots & forbidden
```

---

## Design Decisions

**Why Neon PostgreSQL, not SQLite or a CSV?**
Demonstrates a real production data pipeline — cloud database, connection pooling, TLS, and read-only enforcement — rather than `pd.read_csv()`.

**Why split `app.py` into a `dashboard/` package?**
The original `app.py` was 385 lines mixing layout, SQL, analytics and CSS. Splitting into focused tab modules means each file has one responsibility and is independently readable and testable.

**Why are analytics functions "pure"?**
`analytics/metrics.py` and `analytics/insights.py` take DataFrames and return plain numbers or DataFrames. No Streamlit, no Plotly, no DB calls. This makes them unit-testable without spinning up a UI or database.

**Why is the segmentation rule defined in `config/settings.py` and not inline?**
So that the SQL query (Q7), the Python classifier, the insight text, and the segment-rule documentation in the UI all derive from a single constant. The test `test_segment_sql_uses_the_same_thresholds_as_python` verifies they stay in sync.

**Why does the connection layer have custom DNS resolution?**
Neon serverless hostnames are sometimes unresolvable from certain corporate or university networks. `DB_RESOLVER_DNS` lets the user route DNS through a public resolver (e.g. 1.1.1.1) while the TLS certificate is still validated against the original hostname — no security trade-off.

---

## Author

**Abhishek K P**
[GitHub: @abhishekkp00](https://github.com/abhishekkp00)
[Repository](https://github.com/abhishekkp00/Customer-Trends-Data-Analytics)
