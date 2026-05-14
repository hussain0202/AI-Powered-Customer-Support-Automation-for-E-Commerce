import re
from typing import Any, Dict, List

MAX_HISTORY_TURNS = 3

_FILLER_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "i", "me", "my", "we",
    "you", "it", "can", "could", "would", "should", "do", "does", "did",
    "what", "how", "where", "when", "please", "tell", "give", "show",
    "want", "need", "looking", "get", "have", "has", "been", "just",
    "also", "ok", "okay", "yes", "no", "hi", "hello",
}


def _keywords(text: str) -> str:
    words = re.sub(r"[^a-z0-9\s]", " ", text.lower()).split()
    return " ".join(w for w in words if w not in _FILLER_WORDS and len(w) > 2)


def enrich_query(
    user_message: str,
    context: Dict[str, Any],
    chat_history: List[Dict[str, str]],
) -> str:
    """
    Builds a context-aware search query for ChromaDB by combining:
      1. The current user message (primary signal)
      2. Active session entities — product, category, order ID
      3. Keywords from the last N user turns (conversational continuity)

    Example:
      user_message : "what is the return policy?"
      active_product: "Samsung Galaxy S23"
      recent turn  : "I bought it last week"
      → enriched   : "what is the return policy? Samsung Galaxy S23 bought last week"
    """
    parts = [user_message.strip()]

    # Active context entities give the retriever topical grounding
    if context.get("active_product"):
        parts.append(context["active_product"])
    if context.get("active_category"):
        parts.append(context["active_category"].replace("_", " "))
    if context.get("active_order_id"):
        parts.append(f"order {context['active_order_id']}")

    # Recent user turns add conversational continuity
    recent_keywords: List[str] = []
    for turn in chat_history[-(MAX_HISTORY_TURNS * 2):]:
        if not isinstance(turn, dict):
            continue
        if turn.get("role") == "user":
            content = turn.get("message", "").strip()
            if content and content != user_message.strip():
                kw = _keywords(content)
                if kw:
                    recent_keywords.append(kw)

    if recent_keywords:
        # Use only the two most recent unique user turns to avoid noise
        parts.append(" ".join(recent_keywords[-2:]))

    return " ".join(parts)
