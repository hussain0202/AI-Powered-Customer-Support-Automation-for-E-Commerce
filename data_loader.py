import pandas as pd
from pathlib import Path

# Base data directory relative to this script
DATA_DIR = Path(__file__).parent / 'data'

def _load_csv(filename: str) -> pd.DataFrame:
    """Helper function to load a CSV and clean its columns."""
    file_path = DATA_DIR / filename
    if not file_path.exists():
        raise FileNotFoundError(f"Error: Dataset '{filename}' not found at {file_path}")
    
    try:
        df = pd.read_csv(file_path)
        # Clean column names (lowercase and strip spaces)
        df.columns = df.columns.str.strip().str.lower()
        return df
    except Exception as e:
        raise RuntimeError(f"Failed to load dataset '{filename}'. Error: {str(e)}")

def load_orders() -> pd.DataFrame:
    return _load_csv('olist_orders_dataset.csv')

def load_reviews() -> pd.DataFrame:
    return _load_csv('olist_order_reviews_dataset.csv')

def load_products() -> pd.DataFrame:
    return _load_csv('olist_products_dataset.csv')

def load_order_items() -> pd.DataFrame:
    return _load_csv('olist_order_items_dataset.csv')

def load_customers() -> pd.DataFrame:
    return _load_csv('olist_customers_dataset.csv')

def load_category_translation() -> pd.DataFrame:
    return _load_csv('product_category_name_translation.csv')

def load_all_data() -> dict:
    """Loads all essential datasets and returns them in a dictionary."""
    datasets = {
        'orders': load_orders(),
        'reviews': load_reviews(),
        'order_items': load_order_items(),
        'products': load_products(),
        'customers': load_customers(),
        'category_translation': load_category_translation()
    }
    
    # Print shapes
    for name, df in datasets.items():
        print(f"Loaded {name}: {df.shape[0]} rows, {df.shape[1]} columns")
        
    return datasets

if __name__ == "__main__":
    try:
        print("Testing data loader...\n")
        data = load_all_data()
        print("\n--- First 3 rows of each dataset ---\n")
        for name, df in data.items():
            print(f"Dataset: {name}")
            print(df.head(3))
            print("-" * 60)
    except Exception as e:
        print(f"Test failed: {e}")
