import pandas as pd
from data_loader import load_all_data

def verify_relationships():
    print("Loading data for verification...")
    data = load_all_data()
    
    orders = data['orders']
    customers = data['customers']
    reviews = data['reviews']
    items = data['order_items']
    products = data['products']
    
    print("\n====================================================")
    print("VERIFYING JOINS AND RELATIONSHIPS")
    print("====================================================\n")
    
    # 1. Orders <-> Customers
    orders_customers = pd.merge(orders, customers, on='customer_id', how='inner')
    print("-> Orders <-> Customers Join:")
    print(f"Resulting Shape: {orders_customers.shape}")
    print(f"Null counts in joined data:\n{orders_customers.isnull().sum().head(5)}")
    print(f"Sample row:\n{orders_customers.iloc[0]}\n")
    print("-" * 60)
    
    # 2. Orders <-> Reviews
    orders_reviews = pd.merge(orders, reviews, on='order_id', how='inner')
    print("-> Orders <-> Reviews Join:")
    print(f"Resulting Shape: {orders_reviews.shape}")
    print(f"Null counts in joined data:\n{orders_reviews.isnull().sum().head(5)}")
    print(f"Sample row:\n{orders_reviews.iloc[0]}\n")
    print("-" * 60)
    
    # 3. Orders <-> Order Items
    orders_items = pd.merge(orders, items, on='order_id', how='inner')
    print("-> Orders <-> Order Items Join:")
    print(f"Resulting Shape: {orders_items.shape}")
    print(f"Null counts in joined data:\n{orders_items.isnull().sum().head(5)}")
    print(f"Sample row:\n{orders_items.iloc[0]}\n")
    print("-" * 60)
    
    # 4. Order Items <-> Products
    items_products = pd.merge(items, products, on='product_id', how='inner')
    print("-> Order Items <-> Products Join:")
    print(f"Resulting Shape: {items_products.shape}")
    print(f"Null counts in joined data:\n{items_products.isnull().sum().head(5)}")
    print(f"Sample row:\n{items_products.iloc[0]}\n")

if __name__ == "__main__":
    verify_relationships()
