"""UI smoke test using a CSV-derived STAND-IN for Neon (offline only).

Replicates the notebook cleaning to build the same table, patches the loader,
then drives the real app through Streamlit's AppTest with several filters.
This is NOT a substitute for testing against Neon.
"""
import sys
sys.path.insert(0, ".")
import pandas as pd
from streamlit.testing.v1 import AppTest

SCRIPT = '''
import pandas as pd
from analytics import data_loader as dl
from database import connection as c
import analytics.data_loader
df = pd.read_csv("customer_shopping_behavior.csv")
df["Review Rating"] = df.groupby("Category")["Review Rating"].transform(lambda x: x.fillna(x.median()))
df.columns = df.columns.str.lower().str.replace(" ", "_")
df = df.rename(columns={"purchase_amount_(usd)": "purchase_amount"})
df["age_group"] = pd.qcut(df["age"], q=4, labels=["Young Adult","Adult","Middle-aged","Senior"])
df["purchase_frequency_days"] = df["frequency_of_purchases"].map({"Fortnightly":14,"Weekly":7,"Monthly":30,"Quarterly":90,"Bi-Weekly":14,"Annually":365,"Every 3 Months":90})
df = df.drop(columns="promo_code_used")
c.create_readonly_engine = lambda: object()
c.check_connection = lambda e: None
dl.load_customer_data = lambda e: (dl.prepare_dataframe(df), dl.validate_dataframe(df))
dl.database_row_count = lambda e: len(df)
exec(open("app.py").read())
'''


def run(label, setup=None):
    at = AppTest.from_string(SCRIPT, default_timeout=120).run()
    if setup:
        setup(at)
        at.run()
    status = "OK" if not at.exception else f"EXC: {[e.value for e in at.exception]}"
    print(f"{label}: {status}; errors={[e.value for e in at.error]}; warnings={len(at.warning)}")
    return at


at = run("baseline")
print("tabs:", len(at.tabs), "metrics:", [(m.label, m.value) for m in at.sidebar.metric])
for key, vals in [("flt_gender", ["Female"]), ("flt_category", ["Clothing", "Footwear"]),
                  ("flt_subscription_status", ["Yes"]), ("flt_season", ["Winter"]),
                  ("flt_age_group", ["Senior"]), ("flt_location", ["Montana"]),
                  ("flt_item_purchased", ["Blouse"]), ("flt_shipping_type", ["Express"]),
                  ("flt_discount_applied", ["Yes"]), ("flt_payment_method", ["PayPal"]),
                  ("flt_frequency_of_purchases", ["Weekly"])]:
    a = run(key, lambda t, k=key, v=vals: t.sidebar.multiselect(key=k).set_value(v))
    print("   records:", [m.value for m in a.sidebar.metric])
run("empty result", lambda t: (t.sidebar.multiselect(key="flt_gender").set_value(["Male"]),
                               t.sidebar.multiselect(key="flt_location").set_value(["Montana"]),
                               t.sidebar.multiselect(key="flt_item_purchased").set_value(["Blouse"]),
                               t.sidebar.multiselect(key="flt_season").set_value(["Winter"]),
                               t.sidebar.multiselect(key="flt_payment_method").set_value(["PayPal"]),
                               t.sidebar.multiselect(key="flt_shipping_type").set_value(["Express"])))
a = run("reset", lambda t: t.sidebar.multiselect(key="flt_gender").set_value(["Male"]))
a.sidebar.button(key="reset_filters_btn").click().run()
print("after reset:", [m.value for m in a.sidebar.metric])
