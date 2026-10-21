# Customer Trends & Shopping Behavior Analysis

An end-to-end data analytics project exploring customer shopping behavior using Python, Pandas, and PostgreSQL. The workflow cleans and enriches transaction-level customer data, loads it into a PostgreSQL database hosted on Neon, and uses SQL queries to answer business questions about revenue, discounts, subscriptions, products, shipping, and customer segments.

## Project Goals

- Understand purchasing patterns across customer demographics and product categories.
- Compare revenue and purchase behavior across customer groups.
- Examine discount usage, product ratings, shipping methods, and subscription status.
- Segment customers using previous-purchase history.
- Demonstrate a reproducible workflow spanning Python data preparation and SQL-based analysis.

## Tech Stack

- **Python** — data preparation and transformation
- **Pandas** — data loading, cleaning, exploration, and feature engineering
- **PostgreSQL** — analytical queries and customer data storage
- **Neon** — hosted PostgreSQL database
- **SQLAlchemy** — database connection and data transfer
- **psycopg** — PostgreSQL connectivity
- **Jupyter Notebook** — exploratory analysis and workflow documentation
- **SQL** — aggregations, conditional logic, CTEs, and window functions

## Dataset

The project uses `customer_shopping_behavior.csv`, containing **3,900 customer shopping records** and fields such as:

- Customer ID, age, and gender
- Item purchased and product category
- Purchase amount and location
- Size, color, and season
- Review rating
- Subscription status
- Shipping type
- Discount applied and promo code used
- Previous purchases
- Payment method and purchase frequency

The dataset is suitable for descriptive analysis of the available records. It does not provide timestamps for a chronological time-series analysis, so the project focuses on shopping patterns and customer trends represented in the dataset rather than forecasting future demand.

## Workflow

1. **Load and inspect the data** in Pandas; review data types, distributions, and missing values.
2. **Prepare and enrich features**, including age-group labels and a mapped purchase-frequency interval in days.
3. **Check redundant fields** by comparing discount and promo-code indicators; remove the duplicate promo-code field from the prepared dataframe when they match.
4. **Connect to PostgreSQL** using SQLAlchemy and a Neon database connection string loaded from an environment variable.
5. **Load the prepared dataframe** into a PostgreSQL table named `customer`.
6. **Run SQL analysis** to calculate revenue, compare groups, rank products, and build customer segments.

## Business Questions Answered with SQL

The SQL script (`customer_behavior_sql_queries.sql`) includes queries addressing:

1. Total revenue by gender.
2. Customers who used a discount and spent at least the overall average purchase amount.
3. Five products with the highest average review rating.
4. Average purchase amount for Standard versus Express shipping.
5. Customer counts, average spend, and total revenue for subscribers versus non-subscribers.
6. Products with the highest percentage of purchases using discounts.
7. New, returning, and loyal customer segments based on previous-purchase counts.
8. Top three most-purchased products within each category using a CTE and window ranking.
9. Subscription status among repeat buyers with more than five previous purchases.
10. Revenue contribution by age group.

These queries demonstrate practical SQL skills, including `GROUP BY`, aggregate functions, subqueries, `CASE` expressions, CTEs, and window functions such as `ROW_NUMBER()`.

## Repository Contents

```text
Customer-Trends-Data-Analytics/
├── Customer_Shopping_Behavior_Analysis.ipynb
├── customer_shopping_behavior.csv
├── customer_behavior_sql_queries.sql
├── .gitignore
└── README.md
```

## Run the Analysis

### 1. Clone the repository

```bash
git clone https://github.com/abhishekkp00/Customer-Trends-Data-Analytics.git
cd Customer-Trends-Data-Analytics
```

### 2. Create a virtual environment and install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install pandas sqlalchemy "psycopg[binary]" python-dotenv jupyter
```

### 3. Configure the database connection

Create a local `.env` file in the project root:

```env
DATABASE_URL=your_neon_postgresql_connection_string
```

Use your own Neon connection string and keep the `.env` file private. It is excluded from version control by `.gitignore`.

### 4. Run the notebook

```bash
jupyter notebook Customer_Shopping_Behavior_Analysis.ipynb
```

Run the notebook cells in order. The database-loading portion connects to Neon and writes the prepared dataframe to the `customer` table. Review the database URL and target database before running cells that write data; the notebook uses `if_exists="replace"`, which replaces an existing table with the same name.

### 5. Execute the SQL queries

Open `customer_behavior_sql_queries.sql` in a PostgreSQL client connected to the same database, then execute the queries against the `customer` table after the data has been loaded.

## Interview Discussion Points

- **Data preparation:** handling missing values, normalizing column names, and creating derived features.
- **Data modeling choices:** identifying redundant columns and defining clear customer-segmentation rules.
- **SQL analysis:** comparing groups using aggregates, filtering with subqueries, and ranking products using window functions.
- **Database integration:** connecting a Pandas workflow to a hosted PostgreSQL database with SQLAlchemy.
- **Business interpretation:** translating query results into questions about customer engagement, discount dependence, product performance, and subscription behavior.
- **Limitations:** the analysis is descriptive; differences between groups do not establish causation, and frequency labels are mapped to approximate day intervals for feature creation.

## Scope and Limitations

This repository documents an analytics workflow, not a production customer analytics platform. It does not currently implement predictive modeling, automated dashboards, production scheduling, or causal analysis. Any business recommendations should be based on the actual query results and considered alongside the dataset's limitations.

## License

No license is specified in this repository. Contact the repository owner before reusing the code or dataset beyond the permissions that otherwise apply.
