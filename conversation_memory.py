import re
from typing import Any, Dict, List, Optional

MAX_SUMMARY_TURNS = 5
DEAD_END_THRESHOLD = 2


# ---------------------------------------------------------------------------
# Entity extraction
# ---------------------------------------------------------------------------

def extract_entities_from_history(
    chat_history: List[Dict[str, str]],
) -> Dict[str, Optional[str]]:
    """
    Scans the last 10 user turns for entity mentions that may have been dropped
    from the active conversation state (e.g. an order ID mentioned 4 turns ago).

    Returns a dict with whichever of the following were found first (most recent):
      - order_id  : 32-char hex or ORD-prefixed numeric ID
      - budget    : numeric amount (digits only, commas stripped)
    """
    entities: Dict[str, Optional[str]] = {"order_id": None, "budget": None}

    for turn in reversed(chat_history[-20:]):
        if not isinstance(turn, dict) or turn.get("role") != "user":
            continue
        text = turn.get("message", "")

        if not entities["order_id"]:
            m = re.search(r"\b[a-f0-9]{32}\b|\b(?:ORD)?\d{5,}\b", text, re.IGNORECASE)
            if m:
                entities["order_id"] = m.group(0)

        if not entities["budget"]:
            m = re.search(r"\b\d+(?:,\d+)*\b", text.replace(" ", ""))
            if m:
                raw = m.group(0).replace(",", "")
                # Only treat as budget if it looks like a plausible PKR amount (> 99)
                if int(raw) > 99:
                    entities["budget"] = raw

        if all(entities.values()):
            break

    return entities


# ---------------------------------------------------------------------------
# Conversation summary
# ---------------------------------------------------------------------------

def get_conversation_summary(
    chat_history: List[Dict[str, str]],
    max_turns: int = MAX_SUMMARY_TURNS,
) -> str:
    """
    Returns a compact text block of the last N conversation turns.
    Injected into RAG response generation so the LLM / template can reference
    what was already discussed (e.g. "as we discussed, your order is delivered").
    """
    if not chat_history:
        return ""

    recent = chat_history[-(max_turns * 2):]
    lines: List[str] = []

    for turn in recent:
        if not isinstance(turn, dict):
            continue
        role = turn.get("role", "")
        message = turn.get("message", "").strip()
        if not message:
            continue
        label = "User" if role == "user" else "Assistant"
        # Truncate long bot responses to keep context concise
        if role == "assistant" and len(message) > 150:
            message = message[:147] + "..."
        lines.append(f"{label}: {message}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Dead-end detection
# ---------------------------------------------------------------------------

def is_dead_end(state: dict) -> bool:
    """True when the bot has failed to understand the user DEAD_END_THRESHOLD times in a row."""
    return state.get("context", {}).get("_consecutive_unknown", 0) >= DEAD_END_THRESHOLD


def increment_unknown(state: dict) -> dict:
    ctx = state.setdefault("context", {})
    ctx["_consecutive_unknown"] = ctx.get("_consecutive_unknown", 0) + 1
    return state


def reset_unknown(state: dict) -> dict:
    state.get("context", {})["_consecutive_unknown"] = 0
    return state


# ---------------------------------------------------------------------------
# Help menu
# ---------------------------------------------------------------------------

def build_help_menu() -> str:
    return (
        "I'm having trouble understanding your request. Here's what I can help you with:\n\n"
        "- **Order Tracking** — check your order status\n"
        "- **Product Search** — browse by category\n"
        "- **Pricing** — look up a product price\n"
        "- **Recommendations** — find products within your budget\n"
        "- **Discounts** — see current offers\n"
        "- **Refunds & Returns** — start a return request\n"
        "- **Payment Info** — payment methods and issues\n"
        "- **Shipping** — delivery timelines and policies\n"
        "- **Account Help** — login, password, profile\n\n"
        "What would you like help with?"
    )
