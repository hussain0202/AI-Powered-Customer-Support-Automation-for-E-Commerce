import os
import sqlite3
import pandas as pd


# =========================================================
# PATH CONFIGURATION
# =========================================================

BASE_DIR = os.getcwd()

DATABASE_DIR = os.path.join(
    BASE_DIR,
    "database"
)

CLEANED_DATA_DIR = os.path.join(
    BASE_DIR,
    "data",
    "cleaned"
)

DB_PATH = os.path.join(
    DATABASE_DIR,
    "support.db"
)


# =========================================================
# CLEANED CSV FILES
# =========================================================

PRODUCTS_CSV = os.path.join(
    CLEANED_DATA_DIR,
    "products.csv"
)

INVENTORY_CSV = os.path.join(
    CLEANED_DATA_DIR,
    "inventory.csv"
)

ORDERS_CSV = os.path.join(
    CLEANED_DATA_DIR,
    "orders.csv"
)

PAYMENTS_CSV = os.path.join(
    CLEANED_DATA_DIR,
    "payments.csv"
)

DISCOUNTS_CSV = os.path.join(
    CLEANED_DATA_DIR,
    "discounts.csv"
)


# =========================================================
# LOAD CLEANED DATA
# =========================================================

print("\n========== LOADING CLEANED DATA ==========\n")

products = pd.read_csv(PRODUCTS_CSV)

inventory = pd.read_csv(INVENTORY_CSV)

orders = pd.read_csv(
    ORDERS_CSV,
    dtype={"order_id": str},
    low_memory=False
)
orders.drop_duplicates(subset=["order_id"], inplace=True)

payments = pd.read_csv(PAYMENTS_CSV)

discounts = pd.read_csv(DISCOUNTS_CSV)


print(f"Products Loaded: {len(products)}")
print(f"Inventory Loaded: {len(inventory)}")
print(f"Orders Loaded: {len(orders)}")
print(f"Payments Loaded: {len(payments)}")
print(f"Discounts Loaded: {len(discounts)}")


# =========================================================
# CONNECT DATABASE
# =========================================================

print("\n========== CONNECTING DATABASE ==========\n")

conn = sqlite3.connect(DB_PATH)

cursor = conn.cursor()


# =========================================================
# CLEAR OLD DATA
# =========================================================

print("\n========== CLEARING OLD DATA ==========\n")

cursor.execute("DELETE FROM products")
cursor.execute("DELETE FROM inventory")
cursor.execute("DELETE FROM orders")
cursor.execute("DELETE FROM payments")
cursor.execute("DELETE FROM discounts")


conn.commit()


# =========================================================
# INSERT PRODUCTS
# =========================================================

print("\n========== INSERTING PRODUCTS ==========\n")

products.to_sql(
    "products",
    conn,
    if_exists="append",
    index=False
)

print(f"Inserted {len(products)} products")


# =========================================================
# INSERT INVENTORY
# =========================================================

print("\n========== INSERTING INVENTORY ==========\n")

inventory.to_sql(
    "inventory",
    conn,
    if_exists="append",
    index=False
)

print(f"Inserted {len(inventory)} inventory rows")


# =========================================================
# INSERT ORDERS
# =========================================================

print("\n========== INSERTING ORDERS ==========\n")

orders.to_sql(
    "orders",
    conn,
    if_exists="append",
    index=False
)

print(f"Inserted {len(orders)} orders")


# =========================================================
# INSERT PAYMENTS
# =========================================================

print("\n========== INSERTING PAYMENTS ==========\n")

payments.to_sql(
    "payments",
    conn,
    if_exists="append",
    index=False
)

print(f"Inserted {len(payments)} payments")


# =========================================================
# INSERT DISCOUNTS
# =========================================================

print("\n========== INSERTING DISCOUNTS ==========\n")

discounts.to_sql(
    "discounts",
    conn,
    if_exists="append",
    index=False
)

print(f"Inserted {len(discounts)} discounts")


# =========================================================
# VALIDATE INSERTION
# =========================================================

print("\n========== VALIDATING DATABASE ==========\n")


def count_rows(table_name):

    query = f"SELECT COUNT(*) FROM {table_name}"

    result = cursor.execute(query).fetchone()

    return result[0]


tables = [
    "products",
    "inventory",
    "orders",
    "payments",
    "discounts"
]


for table in tables:

    row_count = count_rows(table)

    print(f"{table}: {row_count} rows")


# =========================================================
# SAMPLE TEST QUERIES
# =========================================================

print("\n========== SAMPLE QUERY TESTS ==========\n")


# ---------------------------------------------------------
# TEST 1 — PRODUCTS
# ---------------------------------------------------------

print("\nTOP PRODUCTS:\n")

query = """
SELECT
    product_name,
    category,
    price_pkr
FROM products
LIMIT 5
"""

result = pd.read_sql(query, conn)

print(result)


# ---------------------------------------------------------
# TEST 2 — INVENTORY
# ---------------------------------------------------------

print("\nIN-STOCK PRODUCTS:\n")

query = """
SELECT
    p.product_name,
    i.stock_quantity
FROM products p
JOIN inventory i
ON p.product_id = i.product_id
WHERE i.availability = 'in_stock'
LIMIT 5
"""

result = pd.read_sql(query, conn)

print(result)


# ---------------------------------------------------------
# TEST 3 — ORDER STATUS
# ---------------------------------------------------------

print("\nORDER STATUS:\n")

query = """
SELECT
    order_id,
    order_status,
    payment_method
FROM orders
LIMIT 5
"""

result = pd.read_sql(query, conn)

print(result)


# ---------------------------------------------------------
# TEST 4 — PAYMENT METHODS
# ---------------------------------------------------------

print("\nPAYMENT METHODS:\n")

query = """
SELECT DISTINCT payment_method
FROM payments
"""

result = pd.read_sql(query, conn)

print(result)


# =========================================================
# COMMIT CHANGES
# =========================================================

conn.commit()


# =========================================================
# CLOSE DATABASE
# =========================================================

conn.close()


# =========================================================
# SUCCESS MESSAGE
# =========================================================

print("\n========== DATA INSERTION COMPLETE ==========\n")

print(f"Database Updated Successfully:\n{DB_PATH}")

print("\nYour Ecommerce AI Database is now ready for:")
print("- SQL Retrieval")
print("- Inventory Queries")
print("- Product Recommendations")
print("- Order Tracking")
print("- Payment Queries")
print("- RAG Integration")