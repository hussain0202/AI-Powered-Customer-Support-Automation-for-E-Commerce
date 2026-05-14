"""
Groq SDK wrapper for the e-commerce AI support assistant.

Design:
  - Singleton client initialised once from GROQ_API_KEY env var
  - System prompt injected as the first "system" role message (Groq/OpenAI style)
  - Chat history is passed as proper alternating user/assistant turns so the model
    has real dialogue context rather than a compressed summary
  - All failures return None; callers fall back to template responses
"""

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────────

MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 1024
TEMPERATURE = 0.7
TOP_P = 1

# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a professional, friendly AI customer support assistant for \
a Pakistani e-commerce store. You help customers with orders, products, payments, \
refunds, and general shopping queries.

CORE RESPONSIBILITIES
- Answer questions accurately using ONLY the context provided to you
- Track orders and explain their status clearly
- Recommend products within a customer's stated budget and category
- Explain store policies (refunds, shipping, cancellations, payments)
- Escalate gracefully when you cannot help

RESPONSE STYLE
- Be concise: 2-4 sentences for simple queries; bullet points for lists
- Be warm and empathetic, especially for complaints or refund requests
- Never invent information that is not present in the provided context
- Always format prices as "PKR X,XXX" (e.g. PKR 5,000)
- When referencing an order, always include the order ID and product name

CONTEXT USAGE
You will receive two types of context before the customer's question:
  1. [Order / Product Data] — structured facts from the database (trust these completely)
  2. [Knowledge Base] — retrieved policy and FAQ text (use to explain policies)

If neither context is provided, answer from general e-commerce knowledge and be \
transparent that you are doing so.

IMPORTANT CONSTRAINTS
- Do NOT mention "context", "knowledge base", "database", or internal system names
- Do NOT say "based on the provided context" — just answer directly
- If you cannot answer, say: "I don't have that information right now. \
Please contact our support team for further assistance."
"""

# ── Client singleton ──────────────────────────────────────────────────────────

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client

    # Load .env if present (development convenience)
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY is not set.")

    from groq import Groq
    _client = Groq(api_key=api_key)
    return _client


# ── Public API ────────────────────────────────────────────────────────────────

def generate_response(
    user_query: str,
    rag_context: str = "",
    intent: str = "",
    conversation_summary: str = "",
    chat_history: Optional[List[Dict[str, Any]]] = None,
    max_tokens: int = MAX_TOKENS,
) -> Optional[str]:
    """
    Sends the user query to Groq (Llama 3.3 70B) with:
      - System prompt as the first message
      - Recent chat history as proper alternating turns
      - RAG / SQL context prepended to the final user message

    Returns the assistant's text, or None if the call fails.
    """
    try:
        client = _get_client()
    except EnvironmentError:
        return None

    try:
        messages = _build_messages(user_query, rag_context, chat_history)

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=TEMPERATURE,
            max_completion_tokens=max_tokens,
            top_p=TOP_P,
            stream=False,
            stop=None,
        )

        return response.choices[0].message.content

    except Exception as exc:
        logger.warning("LLM call failed (%s: %s) — using template fallback.", type(exc).__name__, exc)
        return None


# ── Internal helpers ──────────────────────────────────────────────────────────

def _build_messages(
    user_query: str,
    rag_context: str,
    chat_history: Optional[List[Dict[str, Any]]],
) -> List[Dict[str, str]]:
    """
    Builds the messages list for the Groq API.

    Structure:
      [system, prior user turn, prior assistant turn, ..., final user turn]

    The final user turn prepends any retrieved context so the model has
    the facts it needs without polluting the conversation history.
    """
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": _SYSTEM_PROMPT}
    ]

    # Include the last 3 exchanges (6 turns) from chat history
    if chat_history:
        history_window = chat_history[-6:]
        for turn in history_window:
            role = turn.get("role", "")
            content = turn.get("message", "").strip()
            if role == "assistant":
                api_role = "assistant"
            elif role == "user":
                api_role = "user"
            else:
                continue
            if content:
                messages.append({"role": api_role, "content": content})

        # Groq requires alternating turns; if last turn is from user,
        # drop it so we can append the final user turn cleanly
        if messages[-1]["role"] == "user":
            messages.pop()

    # Final user turn: prepend context block if available
    context_block = _format_context(rag_context)
    if context_block:
        final_content = f"{context_block}\n\nCustomer question: {user_query}"
    else:
        final_content = user_query

    messages.append({"role": "user", "content": final_content})
    return messages


def _format_context(rag_context: str) -> str:
    if not rag_context or not rag_context.strip():
        return ""
    return f"[Relevant Information]\n{rag_context.strip()}"
