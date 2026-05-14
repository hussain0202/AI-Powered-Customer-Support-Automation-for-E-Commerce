import pandas as pd
from data_loader import load_products, load_order_items, load_category_translation

_products = None
_items = None
_translations = None

def _load_data():
    """Helper to cache recommendation datasets during the session."""
    global _products, _items, _translations
    if _products is None:
        _products = load_products()
    if _items is None:
        _items = load_order_items()
    if _translations is None:
        _translations = load_category_translation()

def get_top_categories(limit=5):
    """
    Returns the top selling categories mapped to English.
    """
    _load_data()
    # Join items with products
    merged = pd.merge(_items, _products, on='product_id', how='inner')
    
    # Count by portuguese category
    category_counts = merged['product_category_name'].value_counts().reset_index()
    category_counts.columns = ['product_category_name', 'count']
    
    # Translate to english
    translated = pd.merge(category_counts, _translations, on='product_category_name', how='inner')
    
    # Return top N
    top_categories = translated.head(limit)
    return top_categories[['product_category_name_english', 'count']].to_dict(orient='records')

def recommend_products_by_category(category):
    """
    Recommends top 3 products within a specific English category.
    """
    _load_data()
    
    # Map english category to portuguese
    trans_row = _translations[_translations['product_category_name_english'].str.lower() == category.lower()]
    if trans_row.empty:
        return []
    
    portuguese_cat = trans_row.iloc[0]['product_category_name']
    
    # Filter products by category
    cat_products = _products[_products['product_category_name'] == portuguese_cat]
    
    # Get top products in this category by sales count
    merged = pd.merge(_items, cat_products, on='product_id', how='inner')
    top_products = merged['product_id'].value_counts().head(3).index.tolist()
    
    recommendations = []
    for pid in top_products:
        recommendations.append({
            'product_id': pid,
            'category': category,
            'reason': 'Highly purchased in this category'
        })
    return recommendations

def search_products(user_query):
    """
    Match user query to an English category, then recommend products.
    """
    _load_data()
    query_lower = user_query.lower()
    query_words = set(query_lower.split())
    
    # Get all english categories (drop nulls)
    english_cats = _translations['product_category_name_english'].dropna().unique().tolist()
    
    matched_cat = None
    for cat in english_cats:
        # Check if any word from user query matches the category words
        clean_cat_words = set(cat.replace('_', ' ').lower().split())
        if query_words.intersection(clean_cat_words):
            matched_cat = cat
            break
            
    if matched_cat:
        recs = recommend_products_by_category(matched_cat)
        return matched_cat, recs
        
    return None, []
