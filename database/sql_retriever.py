import os
import re
import sqlite3
from typing import Any, Dict, List, Optional

from rapidfuzz import process, fuzz


BASE_DIR = os.getcwd()
DB_PATH = os.path.join(BASE_DIR, "database", "support.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def normalize_text(value: str) -> str:
    if not value:
        return ""

    value = str(value).lower().strip()
    value = re.sub(r"[^a-z0-9\s&]", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value


def rows_to_dicts(rows: List[sqlite3.Row]) -> List[Dict[str, Any]]:
    return [dict(row) for row in rows]


def get_all_categories() -> List[str]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT DISTINCT category
        FROM products
        WHERE category IS NOT NULL
        ORDER BY category
    """).fetchall()
    conn.close()
    return [row["category"] for row in rows]


def get_all_product_names() -> List[str]:
    conn = get_connection()

    rows = conn.execute("""
        SELECT product_name
        FROM products
        WHERE product_name IS NOT NULL
    """).fetchall()

    conn.close()

    return [row["product_name"] for row in rows]


def fuzzy_match_product(
    query: str,
    min_score: int = 70,
    limit: int = 5,
) -> List[str]:
    """
    Returns up to `limit` product names that fuzzy-match `query`, ordered by score.
    Uses token_set_ratio so partial names like "samsung" correctly rank
    "Samsung Galaxy S24" above unrelated products.
    Returns empty list when nothing meets the threshold.
    """
    product_names = get_all_product_names()
    if not product_names:
        return []

    results = process.extract(
        query,
        product_names,
        scorer=fuzz.token_set_ratio,
        limit=limit,
    )

    return [name for name, score, _ in results if score >= min_score]


def get_matching_products(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Finds products by partial name matching using a two-pass strategy:
      Pass 1 — SQL LIKE for substring matches (fast, exact partial)
      Pass 2 — fuzzy token_set_ratio for typos / brand-only queries

    Returns a deduplicated ranked list of matching products.
    When only one product matches it is unambiguous.
    When multiple match the caller should show them for disambiguation.
    """
    conn = get_connection()
    clean = f"%{query}%"

    # Pass 1: LIKE substring match
    rows = conn.execute("""
        SELECT
            p.product_id, p.product_name, p.category,
            p.price_pkr, p.rating, p.review_count,
            i.stock_quantity, i.availability
        FROM products p
        LEFT JOIN inventory i ON p.product_id = i.product_id
        WHERE LOWER(p.product_name) LIKE LOWER(?)
        ORDER BY p.rating DESC, p.review_count DESC
        LIMIT ?
    """, (clean, limit)).fetchall()
    conn.close()

    seen = set()
    results = []
    for r in rows_to_dicts(rows):
        pid = r["product_id"]
        if pid not in seen:
            seen.add(pid)
            results.append(r)

    if results:
        return results

    # Pass 2: fuzzy match when LIKE found nothing
    matched_names = fuzzy_match_product(query, limit=limit)
    if not matched_names:
        return []

    conn = get_connection()
    placeholders = ",".join("?" * len(matched_names))
    rows = conn.execute(f"""
        SELECT
            p.product_id, p.product_name, p.category,
            p.price_pkr, p.rating, p.review_count,
            i.stock_quantity, i.availability
        FROM products p
        LEFT JOIN inventory i ON p.product_id = i.product_id
        WHERE p.product_name IN ({placeholders})
        ORDER BY p.rating DESC, p.review_count DESC
    """, matched_names).fetchall()
    conn.close()

    return rows_to_dicts(rows)


def search_products(
    query: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    conn = get_connection()

    clean_query = f"%{query}%"

    rows = conn.execute("""
        SELECT
            product_id,
            product_name,
            category,
            price_pkr,
            rating,
            review_count
        FROM products
        WHERE LOWER(product_name) LIKE LOWER(?)
        OR LOWER(category) LIKE LOWER(?)
        ORDER BY rating DESC, review_count DESC
        LIMIT ?
    """, (clean_query, clean_query, limit)).fetchall()

    conn.close()

    if rows:
        return rows_to_dicts(rows)

    matched_names = fuzzy_match_product(query, limit=limit)

    if not matched_names:
        return []

    conn = get_connection()
    placeholders = ",".join("?" * len(matched_names))
    rows = conn.execute(f"""
        SELECT product_id, product_name, category, price_pkr, rating, review_count
        FROM products
        WHERE product_name IN ({placeholders})
        ORDER BY rating DESC, review_count DESC
        LIMIT ?
    """, (*matched_names, limit)).fetchall()
    conn.close()

    return rows_to_dicts(rows)


def get_product_details(
    product_name: str
) -> List[Dict[str, Any]]:
    conn = get_connection()

    rows = conn.execute("""
        SELECT
            product_id,
            product_name,
            category,
            price_pkr,
            rating,
            review_count
        FROM products
        WHERE LOWER(product_name) LIKE LOWER(?)
        LIMIT 5
    """, (f"%{product_name}%",)).fetchall()

    conn.close()

    return rows_to_dicts(rows)


def get_product_price(
    product_name: str
) -> List[Dict[str, Any]]:
    """
    Returns a list of matching products for a price query.
    Callers should show a disambiguation list when len > 1.
    Returns empty list when nothing matches.
    """
    return get_matching_products(product_name, limit=5)


def get_products_by_category(
    category: str,
    limit: int = 10,
    max_price: Optional[float] = None,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    conn = get_connection()

    params: List[Any] = [category]

    query = """
        SELECT
            p.product_id,
            p.product_name,
            p.category,
            p.price_pkr,
            p.rating,
            p.review_count,
            i.stock_quantity,
            i.availability
        FROM products p
        LEFT JOIN inventory i
        ON p.product_id = i.product_id
        WHERE LOWER(p.category) = LOWER(?)
    """

    if max_price is not None:
        query += " AND p.price_pkr <= ?"
        params.append(max_price)

    query += """
        ORDER BY p.rating DESC, p.review_count DESC
        LIMIT ? OFFSET ?
    """

    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()

    conn.close()

    return rows_to_dicts(rows)


def get_available_inventory(
    category: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    conn = get_connection()

    if category:
        rows = conn.execute("""
            SELECT
                p.product_id,
                p.product_name,
                p.category,
                p.price_pkr,
                p.rating,
                i.stock_quantity,
                i.availability
            FROM products p
            JOIN inventory i
            ON p.product_id = i.product_id
            WHERE i.availability = 'in_stock'
            AND LOWER(p.category) = LOWER(?)
            ORDER BY i.stock_quantity DESC
            LIMIT ? OFFSET ?
        """, (category, limit, offset)).fetchall()

    else:
        rows = conn.execute("""
            SELECT
                p.product_id,
                p.product_name,
                p.category,
                p.price_pkr,
                p.rating,
                i.stock_quantity,
                i.availability
            FROM products p
            JOIN inventory i
            ON p.product_id = i.product_id
            WHERE i.availability = 'in_stock'
            ORDER BY i.stock_quantity DESC
            LIMIT ? OFFSET ?
        """, (limit, offset)).fetchall()

    conn.close()

    return rows_to_dicts(rows)


def get_low_stock_products(
    limit: int = 10
) -> List[Dict[str, Any]]:
    conn = get_connection()

    rows = conn.execute("""
        SELECT
            p.product_id,
            p.product_name,
            p.category,
            p.price_pkr,
            i.stock_quantity,
            i.availability
        FROM products p
        JOIN inventory i
        ON p.product_id = i.product_id
        WHERE i.availability = 'low_stock'
        ORDER BY i.stock_quantity ASC
        LIMIT ?
    """, (limit,)).fetchall()

    conn.close()

    return rows_to_dicts(rows)


def get_out_of_stock_products(
    limit: int = 10
) -> List[Dict[str, Any]]:
    conn = get_connection()

    rows = conn.execute("""
        SELECT
            p.product_id,
            p.product_name,
            p.category,
            p.price_pkr,
            i.stock_quantity,
            i.availability
        FROM products p
        JOIN inventory i
        ON p.product_id = i.product_id
        WHERE i.availability = 'out_of_stock'
        LIMIT ?
    """, (limit,)).fetchall()

    conn.close()

    return rows_to_dicts(rows)


def recommend_products(
    category: Optional[str] = None,
    max_price: Optional[float] = None,
    limit: int = 5,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    conn = get_connection()

    params: List[Any] = []

    query = """
        SELECT
            p.product_id,
            p.product_name,
            p.category,
            p.price_pkr,
            p.rating,
            p.review_count,
            i.stock_quantity,
            i.availability
        FROM products p
        LEFT JOIN inventory i
        ON p.product_id = i.product_id
        WHERE 1 = 1
    """

    if category:
        query += " AND LOWER(p.category) = LOWER(?)"
        params.append(category)

    if max_price is not None:
        query += " AND p.price_pkr <= ?"
        params.append(max_price)

    query += """
        ORDER BY p.rating DESC, p.review_count DESC, p.price_pkr ASC
        LIMIT ? OFFSET ?
    """

    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()

    conn.close()

    return rows_to_dicts(rows)


def update_order_status(order_id: str, new_status: str) -> bool:
    """
    Writes a new order_status to the database.
    Returns True if a row was updated, False if the order_id was not found.
    """
    conn = get_connection()
    cur  = conn.execute(
        "UPDATE orders SET order_status = ? WHERE order_id = ?",
        (new_status, str(order_id)),
    )
    conn.commit()
    updated = cur.rowcount > 0
    conn.close()
    return updated


def track_order(
    order_id: str
) -> Optional[Dict[str, Any]]:
    conn = get_connection()

    row = conn.execute("""
        SELECT
            order_id,
            customer_id,
            product_name,
            category,
            order_status,
            payment_method,
            order_total,
            order_date
        FROM orders
        WHERE order_id = ?
        LIMIT 1
    """, (str(order_id),)).fetchone()

    conn.close()

    return dict(row) if row else None


def get_customer_orders(
    customer_id: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    conn = get_connection()

    rows = conn.execute("""
        SELECT
            order_id,
            product_name,
            category,
            order_status,
            payment_method,
            order_total,
            order_date
        FROM orders
        WHERE customer_id = ?
        ORDER BY order_date DESC
        LIMIT ?
    """, (str(customer_id), limit)).fetchall()

    conn.close()

    return rows_to_dicts(rows)


def get_payment_methods() -> List[str]:
    conn = get_connection()

    rows = conn.execute("""
        SELECT DISTINCT payment_method
        FROM payments
        WHERE payment_method IS NOT NULL
    """).fetchall()

    conn.close()

    return [row["payment_method"] for row in rows]


def get_discounted_products(
    limit: int = 10,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    conn = get_connection()

    rows = conn.execute("""
        SELECT
            product_name,
            original_price,
            discounted_price,
            discount_percent
        FROM discounts
        WHERE discounted_price IS NOT NULL
        ORDER BY discount_percent DESC
        LIMIT ? OFFSET ?
    """, (limit, offset)).fetchall()

    conn.close()

    return rows_to_dicts(rows)


def get_products_under_budget(
    budget: float,
    category: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    return recommend_products(
        category=category,
        max_price=budget,
        limit=limit,
        offset=offset,
    )


def format_products_response(
    products: List[Dict[str, Any]],
    title: str = "Here are some products:"
) -> str:
    if not products:
        return "I couldn't find matching products in the database."

    lines = [title, ""]

    for product in products:
        name = product.get("product_name", "Unknown product")
        price = product.get("price_pkr")
        rating = product.get("rating")
        stock = product.get("stock_quantity")

        line = f"- {name}"

        if price is not None:
            line += f" — PKR {price:,.0f}"

        if rating is not None:
            line += f" | Rating: {rating}"

        if stock is not None:
            line += f" | Stock: {stock}"

        lines.append(line)

    return "\n".join(lines)


def format_order_response(order: Optional[Dict[str, Any]]) -> str:
    if not order:
        return "I could not find this order ID in the system."

    return (
        f"Order {order['order_id']} is currently "
        f"{order['order_status']}.\n"
        f"Product: {order['product_name']}\n"
        f"Payment Method: {order['payment_method']}\n"
        f"Total: PKR {order['order_total']:,.0f}\n"
        f"Order Date: {order['order_date']}"
    )


def format_price_response(product: Optional[Dict[str, Any]]) -> str:
    if not product:
        return "I couldn't find that product in the database."

    return (
        f"The price of {product['product_name']} is "
        f"PKR {product['price_pkr']:,.0f}."
    )


if __name__ == "__main__":
    print("\n========== SQL RETRIEVER TEST ==========\n")

    print("\nPayment Methods:")
    print(get_payment_methods())

    print("\nAvailable Inventory:")
    print(format_products_response(get_available_inventory(limit=5)))

    print("\nRecommended Products Under PKR 10000:")
    print(format_products_response(
        get_products_under_budget(10000, limit=5)
    ))

    print("\nDiscounted Products:")
    print(get_discounted_products(limit=5))