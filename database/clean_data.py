import os
import random
import re
import pandas as pd


# =========================================================
# LOAD DATASETS
# =========================================================

DARAZ_PRODUCTS_PATH = "raw/daraz_products.csv"
DARAZ_DISCOUNTS_PATH = "raw/daraz_discounts.csv"
PAKISTAN_ORDERS_PATH = "raw/pakistan_ecommerce.csv"


daraz_products = pd.read_csv(DARAZ_PRODUCTS_PATH)
daraz_discounts = pd.read_csv(DARAZ_DISCOUNTS_PATH)
pakistan_orders = pd.read_csv(
    PAKISTAN_ORDERS_PATH,
    low_memory=False
)


# =========================================================
# DEBUG: SHOW AVAILABLE COLUMNS
# =========================================================

print("\n========== DATASET COLUMNS ==========\n")

print("Daraz Products Columns:")
print(daraz_products.columns.tolist())

print("\nDaraz Discounts Columns:")
print(daraz_discounts.columns.tolist())

print("\nPakistan Ecommerce Columns:")
print(pakistan_orders.columns.tolist())


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def clean_text(text):
    """
    Clean and normalize text.
    """

    if pd.isna(text):
        return None

    text = str(text)

    text = text.strip()

    text = re.sub(r"\s+", " ", text)

    return text


def clean_price(value):
    """
    Convert messy PKR price values into float.
    """

    if pd.isna(value):
        return None

    value = str(value)

    value = value.replace(",", "")
    value = value.replace("Rs.", "")
    value = value.replace("PKR", "")
    value = value.replace("₨", "")
    value = value.strip()

    try:
        return float(value)
    except ValueError:
        return None



def clean_rating(value):
    """
    Convert ratings like '4.6/5' into float.
    """

    if pd.isna(value):
        return None

    value = str(value)

    value = value.replace("/5", "").strip()

    try:
        return float(value)
    except ValueError:
        return None
    


def normalize_category(category):
    """
    Normalize categories into chatbot-friendly labels.
    """

    if pd.isna(category):
        return "other"

    category = clean_text(category).lower()

    CATEGORY_MAPPING = {
        "mobiles & tablets": "electronics",
        "beauty & grooming": "beauty",
        "women's fashion": "fashion",
        "men's fashion": "fashion",
        "appliances": "home_appliances",
        "home & living": "home_living",
        "computing": "electronics",
        "gaming": "gaming",
        "groceries": "groceries",
        "watches, bags, jewellery": "fashion",
        "kids watches": "fashion",
    }

    return CATEGORY_MAPPING.get(category, category)


def clean_product_name(name):
    """
    Normalize product names.
    """

    if pd.isna(name):
        return None

    name = clean_text(name)

    REMOVE_WORDS = [
        "Original",
        "Brand New",
        "New",
        "Latest",
        "Official",
        "100%",
        "Pakistan",
        "PTA Approved",
    ]

    for word in REMOVE_WORDS:
        name = name.replace(word, "")

    name = re.sub(r"\s+", " ", name)

    return name.strip()


def stock_status(qty):
    """
    Generate stock availability label.
    """

    if qty == 0:
        return "out_of_stock"

    if qty < 10:
        return "low_stock"

    return "in_stock"


def clean_integer(value):

    if pd.isna(value):
        return 0

    value = str(value)

    value = re.sub(r"[^0-9]", "", value)

    if value == "":
        return 0

    return int(value)



def clean_sold_count(value):

    if pd.isna(value):
        return 0

    value = str(value).lower().replace("sold", "").strip()

    if "k" in value:
        return int(float(value.replace("k", "")) * 1000)

    value = re.sub(r"[^0-9]", "", value)

    return int(value) if value else 0



# =========================================================
# CLEAN PRODUCTS DATASET
# =========================================================

print("\n========== CLEANING PRODUCTS ==========\n")

# IMPORTANT:
# Update these mappings based on actual CSV columns

PRODUCT_COLUMN_MAPPING = {
    "Title": "product_name",
    "Category": "category",
    "Current Price": "price_pkr",
    "Rating in Stars": "rating",
    "Rating Count": "review_count",
}


missing_product_columns = [
    col
    for col in PRODUCT_COLUMN_MAPPING.keys()
    if col not in daraz_products.columns
]

if missing_product_columns:
    print(
        f"WARNING: Missing product columns: "
        f"{missing_product_columns}"
    )

available_product_columns = [
    col
    for col in PRODUCT_COLUMN_MAPPING.keys()
    if col in daraz_products.columns
]

products = daraz_products[
    available_product_columns
].copy()

products = products.rename(
    columns=PRODUCT_COLUMN_MAPPING
)

products["review_count"] = (
    products["review_count"]
    .apply(clean_integer)
)

# Add fallback columns if missing

if "rating" not in products.columns:
    products["rating"] = 4.0

if "review_count" not in products.columns:
    products["review_count"] = 0


# Clean product names

products["product_name"] = (
    products["product_name"]
    .apply(clean_product_name)
)


# Normalize categories

products["category"] = (
    products["category"]
    .apply(normalize_category)
)


# Clean prices

products["price_pkr"] = (
    products["price_pkr"]
    .apply(clean_price)
)

products["rating"] = (
    products["rating"]
    .apply(clean_rating)
)

# Remove invalid rows

products = products.dropna(
    subset=[
        "product_name",
        "category",
        "price_pkr",
    ]
)


# Remove duplicates

products = products.drop_duplicates(
    subset=["product_name"]
)


# Generate product IDs

products["product_id"] = [
    f"P{i+1000}"
    for i in range(len(products))
]


# Reorder columns

products = products[[
    "product_id",
    "product_name",
    "category",
    "price_pkr",
    "rating",
    "review_count"
]]


print(products.head())


# =========================================================
# CREATE INVENTORY
# =========================================================

print("\n========== GENERATING INVENTORY ==========\n")

inventory = products[[
    "product_id"
]].copy()


inventory["stock_quantity"] = [
    random.randint(0, 200)
    for _ in range(len(inventory))
]


inventory["availability"] = (
    inventory["stock_quantity"]
    .apply(stock_status)
)


print(inventory.head())


# =========================================================
# CLEAN ORDERS DATASET
# =========================================================

print("\n========== CLEANING ORDERS ==========\n")

ORDER_COLUMN_MAPPING = {
    "increment_id": "order_id",
    "status": "order_status",
    "sku": "product_name",
    "grand_total": "order_total",
    "payment_method": "payment_method",
    "Customer ID": "customer_id",
    "created_at": "order_date",
    "category_name_1": "category",
}


missing_order_columns = [
    col
    for col in ORDER_COLUMN_MAPPING.keys()
    if col not in pakistan_orders.columns
]

if missing_order_columns:
    print(
        f"WARNING: Missing order columns: "
        f"{missing_order_columns}"
    )


available_order_columns = [
    col
    for col in ORDER_COLUMN_MAPPING.keys()
    if col in pakistan_orders.columns
]


orders = pakistan_orders[
    available_order_columns
].copy()


orders = orders.rename(
    columns=ORDER_COLUMN_MAPPING
)


orders["order_date"] = pd.to_datetime(
    orders["order_date"],
    errors="coerce"
)



# Normalize order statuses

STATUS_MAPPING = {
    "complete": "delivered",
    "canceled": "cancelled",
    "order_refunded": "refunded",
    "received": "processing",
}


orders["order_status"] = (
    orders["order_status"]
    .astype(str)
    .str.lower()
    .replace(STATUS_MAPPING)
)


# Clean categories

orders["category"] = (
    orders["category"]
    .apply(normalize_category)
)


# Clean product names

orders["product_name"] = (
    orders["product_name"]
    .apply(clean_product_name)
)


# Clean totals

orders["order_total"] = (
    orders["order_total"]
    .apply(clean_price)
)


# Clean payment methods

PAYMENT_MAPPING = {
    "cod": "Cash on Delivery",
    "ublcreditcard": "UBL Credit Card",
    "mygateway": "MyGateway",
    "customercredit": "Customer Credit",
}


orders["payment_method"] = (
    orders["payment_method"]
    .astype(str)
    .str.lower()
    .replace(PAYMENT_MAPPING)
)


# Remove bad rows

orders = orders.dropna(
    subset=[
        "order_id",
        "product_name",
    ]
)


print(orders.head())


# =========================================================
# CREATE PAYMENTS TABLE
# =========================================================

print("\n========== GENERATING PAYMENTS ==========\n")

payments = orders[[
    "order_id",
    "payment_method",
    "order_total"
]].copy()


payments = payments.rename(
    columns={
        "order_total": "amount"
    }
)


print(payments.head())


# =========================================================
# CLEAN DISCOUNTS DATASET
# =========================================================

print("\n========== CLEANING DISCOUNTS ==========\n")

DISCOUNT_COLUMN_MAPPING = {
    "Title": "product_name",
    "Original Price": "original_price",
    "Discount Price": "discounted_price",
    "Discount": "discount_percent",
}


available_discount_columns = [
    col
    for col in DISCOUNT_COLUMN_MAPPING.keys()
    if col in daraz_discounts.columns
]


discounts = daraz_discounts[
    available_discount_columns
].copy()


discounts = discounts.rename(
    columns=DISCOUNT_COLUMN_MAPPING
)


if "product_name" in discounts.columns:
    discounts["product_name"] = (
        discounts["product_name"]
        .apply(clean_product_name)
    )


if "original_price" in discounts.columns:
    discounts["original_price"] = (
        discounts["original_price"]
        .apply(clean_price)
    )


if "discounted_price" in discounts.columns:
    discounts["discounted_price"] = (
        discounts["discounted_price"]
        .apply(clean_price)
    )


print(discounts.head())


# =========================================================
# SAVE CLEANED DATASETS
# =========================================================

print("\n========== SAVING CLEANED FILES ==========\n")

products.to_csv(
    "data/cleaned/products.csv",
    index=False
)

inventory.to_csv(
    "data/cleaned/inventory.csv",
    index=False
)

orders.to_csv(
    "data/cleaned/orders.csv",
    index=False
)

payments.to_csv(
    "data/cleaned/payments.csv",
    index=False
)

discounts.to_csv(
    "data/cleaned/discounts.csv",
    index=False
)


# =========================================================
# FINAL SUMMARY
# =========================================================

print("\n========== CLEANING COMPLETE ==========\n")

print(f"Products: {len(products)}")
print(f"Inventory Rows: {len(inventory)}")
print(f"Orders: {len(orders)}")
print(f"Payments: {len(payments)}")
print(f"Discounts: {len(discounts)}")

print("\nCleaned files saved in:")
print("data/cleaned/")