import pandas as pd
import re
from data_loader import load_orders

_orders_df = None

def _get_orders_df():
    """Helper to cache orders dataset during the session."""
    global _orders_df
    if _orders_df is None:
        _orders_df = load_orders()
    return _orders_df

def extract_order_id(user_query):
    """
    Detects 32-character hexadecimal order IDs from user input.
    Example valid ID: e481f51cbdc54678b7cc49136f2d6af7
    """
    match = re.search(r'\b[a-f0-9]{32}\b', user_query.lower())
    if match:
        return match.group(0)
    return None

def track_order(order_id):
    """
    Searches the orders dataset and returns formatted tracking information.
    Intelligently handles delivery timeline analysis.
    """
    orders = _get_orders_df()
    
    # Find order by ID
    order_row = orders[orders['order_id'] == order_id]
    
    if order_row.empty:
        return "I could not find an order with that ID. Please check the 32-character ID and try again."
        
    order = order_row.iloc[0]
    status = order.get('order_status', 'unknown')
    
    # Safely convert dates, handling null values
    try:
        purchase_date = pd.to_datetime(order.get('order_purchase_timestamp'))
    except:
        purchase_date = pd.NaT
        
    try:
        estimated_date = pd.to_datetime(order.get('order_estimated_delivery_date'))
    except:
        estimated_date = pd.NaT
        
    try:
        delivered_date = pd.to_datetime(order.get('order_delivered_customer_date'))
    except:
        delivered_date = pd.NaT
    
    # Format the customer support response
    response = f"**Order Status:** {str(status).capitalize()}\n\n"
    
    if pd.notnull(purchase_date):
        response += f"- **Purchased on:** {purchase_date.strftime('%Y-%m-%d')}\n"
    if pd.notnull(estimated_date):
        response += f"- **Estimated Delivery:** {estimated_date.strftime('%Y-%m-%d')}\n"
        
    # Intelligent Delivery Analysis
    if status == 'delivered' and pd.notnull(delivered_date):
        response += f"- **Delivered on:** {delivered_date.strftime('%Y-%m-%d')}\n\n"
        
        if pd.notnull(estimated_date):
            if delivered_date > estimated_date:
                response += "⚠️ *Your order was delivered later than expected. We apologize for the delay.*"
            elif delivered_date < estimated_date:
                response += "✅ *Your order arrived earlier than expected!*"
            else:
                response += "✅ *Your order was delivered exactly on time.*"
    else:
        response += "\n🕒 *Your order is still being processed or shipped.*"
        
    return response
