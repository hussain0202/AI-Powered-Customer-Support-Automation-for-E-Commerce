"""
Hybrid retrieval: combines SQL-structured data with RAG policy content
so responses carry both specific order/product facts AND the relevant policy text.

Used for intents where the user needs:
  - A personal data answer  (e.g. "your order #X is delivered")
  - A policy answer          (e.g. "our cancellation policy says …")
"""

from typing import Any, Dict, List, Optional

from rag.retriever import retrieve_context
from rag.context_builder import build_context
from rag.query_enricher import enrich_query

POLICY_HEADINGS: Dict[str, str] = {
    "refund_return":  "Refund & Return Policy",
    "cancel_order":   "Cancellation Policy",
    "payment_issue":  "Payment Support",
    "payment":        "Payment Policy",
}


def retrieve_policy_context(
    user_query: str,
    state_context: Dict[str, Any],
    chat_history: List[Dict[str, str]],
    top_k: int = 3,
) -> str:
    """
    Runs a context-enriched semantic search against the knowledge base
    and returns a ranked, deduplicated policy context string.
    """
    enriched = enrich_query(user_query, state_context, chat_history)
    chunks = retrieve_context(enriched, top_k=top_k)
    return build_context(chunks)


def build_hybrid_response(
    sql_section: Optional[str],
    policy_context: str,
    intent: str,
    user_query: str = "",
    chat_history: Optional[List[Dict[str, Any]]] = None,
) -> Optional[str]:
    """
    Merges the structured SQL answer with the retrieved policy context,
    then passes the combined block to the LLM for a natural response.

    Falls back to the raw combined text when the LLM is unavailable.
    """
    parts: List[str] = []

    if sql_section:
        parts.append(sql_section)

    if policy_context:
        heading = POLICY_HEADINGS.get(intent, "Policy Information")
        parts.append(f"**{heading}:**\n\n{policy_context}")

    if not parts:
        return None

    combined_context = "\n\n---\n\n".join(parts)

    # LLM-first path — send combined SQL + policy as RAG context
    if user_query:
        try:
            from llm_client import generate_response as llm_generate
            result = llm_generate(
                user_query=user_query,
                rag_context=combined_context,
                intent=intent,
                chat_history=chat_history,
            )
            if result:
                return result
        except Exception:
            pass

    # Fallback path — skip if disabled
    from runtime_config import is_fallback_enabled
    if not is_fallback_enabled():
        # Still return the raw SQL facts if available — they are always useful
        if sql_section:
            return (
                f"{sql_section}\n\n"
                "⚠️ AI model unavailable — policy details omitted (fallback disabled)."
            )
        return (
            "⚠️ The AI model did not return a response and static fallback is disabled. "
            "Please try again or enable fallback from the sidebar."
        )

    return combined_context
