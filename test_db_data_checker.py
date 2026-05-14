import sqlite3
import pandas as pd

conn = sqlite3.connect("database/support.db")

tables = [
    "products",
    "inventory",
    "orders",
    "payments",
    "discounts"
]

for table in tables:

    print(f"\n===== {table.upper()} =====")

    query = f"PRAGMA table_info({table})"

    result = pd.read_sql(query, conn)

    print(result[["name", "type"]])

conn.close()