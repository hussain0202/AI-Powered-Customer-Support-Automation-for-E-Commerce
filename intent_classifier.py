import re

def classify_intent(user_query: str) -> dict:
    """
    Classifies user queries into predefined intents using keyword and regex heuristics.
    Returns the detected intent, confidence score, and a reason string.
    """
    query = user_query.lower()
    
    # 1. Order Tracking
    if re.search(r'\b[a-f0-9]{32}\b', query) or any(word in query for word in ["where is", "track", "status", "my order"]):
        return {"intent": "order_tracking", "confidence": 0.85, "reason": "Matched order tracking keywords or valid 32-char ID"}
        
    # 2. Product Recommendation
    if any(word in query for word in ["recommend", "looking for", "popular", "best", "show me", "buy"]):
        return {"intent": "product_recommendation", "confidence": 0.80, "reason": "Matched recommendation keywords"}
        
    # 3. Refund / Return
    if any(word in query for word in ["refund", "return", "money back", "exchange"]):
        return {"intent": "refund_return", "confidence": 0.90, "reason": "Matched refund/return keywords"}
        
    # 4. Human Escalation (Needs to be checked before Complaint or Unknown)
    if any(word in query for word in ["human", "agent", "representative", "support person", "speak to", "help me"]):
        return {"intent": "human_escalation", "confidence": 0.95, "reason": "Matched explicit human escalation keywords"}
        
    # 5. Complaint
    if any(word in query for word in ["angry", "terrible", "awful", "bad", "hate", "issue", "problem", "broken", "unhappy", "late"]):
        return {"intent": "complaint", "confidence": 0.75, "reason": "Matched complaint/frustration keywords"}
        
    # 6. Payment
    if any(word in query for word in ["payment", "card", "pay", "credit", "debit", "paypal"]):
        return {"intent": "payment", "confidence": 0.85, "reason": "Matched payment keywords"}
        
    # 7. Shipping / Delivery Delay
    if any(word in query for word in ["shipping", "delivery", "ship", "time", "how long", "delay"]):
        return {"intent": "shipping", "confidence": 0.80, "reason": "Matched shipping/logistics keywords"}
        
    # 8. General FAQ
    if any(word in query for word in ["policy", "faq", "contact", "support"]):
        return {"intent": "general_faq", "confidence": 0.70, "reason": "Matched general FAQ keywords"}
        
    # 9. Unknown Fallback
    return {"intent": "unknown", "confidence": 0.30, "reason": "No clear intent pattern matched"}
