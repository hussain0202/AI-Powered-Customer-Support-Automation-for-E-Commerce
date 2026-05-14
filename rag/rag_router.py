RAG_ENABLED_INTENTS = {
    "general_faq",
    "shipping",
    "security_privacy",
    "technical_support",
    "account_help",
    "store_location",
    "business_hours",
    "subscription_membership",
}

DB_ENABLED_INTENTS = {
    "product_search",
    "inventory_query",
    "product_availability",
    "pricing_query",
    "order_tracking",
    "product_recommendation",
    "discount_offer",
}

# Intents that combine SQL structured data WITH RAG policy content
HYBRID_INTENTS = {
    "refund_return",
    "cancel_order",
    "payment_issue",
    "payment",
}


def determine_strategy(intent: str) -> str:
    """
    Returns the retrieval strategy for a given intent:
      hybrid_retrieval  — SQL facts + RAG policy merged in one response
      semantic_search   — knowledge base retrieval only
      sql_retrieval     — structured database query only
      static_generation — ResponseGenerator handler (no retrieval)
    """
    if intent in HYBRID_INTENTS:
        return "hybrid_retrieval"
    if intent in RAG_ENABLED_INTENTS:
        return "semantic_search"
    if intent in DB_ENABLED_INTENTS:
        return "sql_retrieval"
    return "static_generation"
