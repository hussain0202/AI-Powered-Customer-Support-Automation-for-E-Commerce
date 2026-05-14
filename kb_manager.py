def get_faq_response(intent: str, user_query: str) -> str:
    """
    Returns a standard professional FAQ response based on the detected intent or keywords.
    Acts as the integrated Knowledge Base.
    """
    query = user_query.lower()
    
    faq_data = {
        "refund_return": "We accept returns within 30 days of delivery. The item must be unused, in its original packaging, and accompanied by a receipt. Approved refunds will be applied to your original method of payment within 5-7 business days.",
        "payment": "We accept all major credit and debit cards (Visa, MasterCard, American Express), PayPal, Apple Pay, and Google Pay. We also offer Cash on Delivery (COD) for eligible locations.",
        "shipping": "Standard shipping typically takes 3-5 business days. Expedited shipping takes 1-2 business days. Standard delivery is free for orders over $50.",
        "general_faq": "You can reach our customer support team via email at support@ecommerce.com, or call us at 1-800-123-4567. Our working hours are Monday to Friday, 9 AM to 6 PM EST."
    }
    
    # Base match on intent
    if intent in faq_data:
        return faq_data[intent]
        
    # Fallback keyword matching for edge cases
    if "cancel" in query:
        return "You can cancel your order within 24 hours of placing it, provided it has not yet been shipped. Please contact our support team immediately to request a cancellation."
    elif "warranty" in query:
        return "All our electronics and appliances come with a standard 1-year manufacturer warranty. Please refer to the specific product page for detailed warranty terms."
        
    return None
