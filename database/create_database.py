import os
import sqlite3


# =========================================================
# DATABASE PATH
# =========================================================

BASE_DIR = os.getcwd()

DATABASE_DIR = os.path.join(
    BASE_DIR,
    "database"
)

os.makedirs(DATABASE_DIR, exist_ok=True)

DB_PATH = os.path.join(
    DATABASE_DIR,
    "support.db"
)


# =========================================================
# CREATE DATABASE CONNECTION
# =========================================================

conn = sqlite3.connect(DB_PATH)

cursor = conn.cursor()


print("\n========== CREATING DATABASE ==========\n")


# =========================================================
# PRODUCTS TABLE
# =========================================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT,
    price_pkr REAL,
    rating REAL,
    review_count INTEGER
)
""")


# =========================================================
# INVENTORY TABLE
# =========================================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS inventory (
    inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT,
    stock_quantity INTEGER,
    availability TEXT,

    FOREIGN KEY(product_id)
    REFERENCES products(product_id)
)
""")


# =========================================================
# ORDERS TABLE
# =========================================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT,
    product_name TEXT,
    category TEXT,
    order_status TEXT,
    payment_method TEXT,
    order_total REAL,
    order_date TEXT
)
""")


# =========================================================
# PAYMENTS TABLE
# =========================================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS payments (
    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT,
    payment_method TEXT,
    amount REAL,

    FOREIGN KEY(order_id)
    REFERENCES orders(order_id)
)
""")


# =========================================================
# DISCOUNTS TABLE
# =========================================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS discounts (
    discount_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT,
    original_price REAL,
    discounted_price REAL,
    discount_percent REAL
)
""")


# =========================================================
# CUSTOMERS TABLE
# =========================================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT PRIMARY KEY,
    customer_name TEXT,
    customer_city TEXT,
    customer_email TEXT,
    customer_phone TEXT
)
""")


# =========================================================
# REVIEWS TABLE
# =========================================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT,
    rating REAL,
    review_text TEXT,

    FOREIGN KEY(product_id)
    REFERENCES products(product_id)
)
""")


# =========================================================
# CONVERSATION LOGS TABLE
# =========================================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS conversation_logs (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    user_message TEXT,
    bot_response TEXT,
    detected_intent TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")


# =========================================================
# CREATE INDEXES
# =========================================================

print("\n========== CREATING INDEXES ==========\n")


# Products Indexes

cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_products_name
ON products(product_name)
""")

cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_products_category
ON products(category)
""")


# Inventory Indexes

cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_inventory_product
ON inventory(product_id)
""")


# Orders Indexes

cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_orders_customer
ON orders(customer_id)
""")

cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_orders_status
ON orders(order_status)
""")

cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_orders_date
ON orders(order_date)
""")


# Payments Indexes

cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_payments_order
ON payments(order_id)
""")


# Discounts Indexes

cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_discounts_product
ON discounts(product_name)
""")


# Reviews Indexes

cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_reviews_product
ON reviews(product_id)
""")


# Conversation Logs Indexes

cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_conversation_session
ON conversation_logs(session_id)
""")


# =========================================================
# COMMIT CHANGES
# =========================================================

conn.commit()


# =========================================================
# CLOSE CONNECTION
# =========================================================

conn.close()


# =========================================================
# SUCCESS MESSAGE
# =========================================================

print("\n========== DATABASE CREATED ==========\n")

print(f"Database Location:\n{DB_PATH}")

print("\nCreated Tables:")
print("- products")
print("- inventory")
print("- orders")
print("- payments")
print("- discounts")
print("- customers")
print("- reviews")
print("- conversation_logs")

print("\nIndexes created successfully.")