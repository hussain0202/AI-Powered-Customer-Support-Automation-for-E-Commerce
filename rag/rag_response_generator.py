from typing import Any, Dict, List, Optional

_LLM_UNAVAILABLE = (
    "⚠️ The AI model did not return a response and static fallback is disabled. "
    "Please try again or enable fallback from the sidebar."
)


def generate_rag_response(
    user_query: str,
    context: str,
    intent: str,
    conversation_summary: str = "",
    chat_history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    from runtime_config import is_fallback_enabled

    # LLM-first path
    try:
        from llm_client import generate_response as llm_generate
        result = llm_generate(
            user_query=user_query,
            rag_context=context,
            intent=intent,
            conversation_summary=conversation_summary,
            chat_history=chat_history,
        )
        if result:
            return result
    except Exception:
        pass

    # Fallback path — skip if disabled
    if not is_fallback_enabled():
        return _LLM_UNAVAILABLE

    if not context:
        return (
            "I'm sorry, I couldn't find specific information about your request "
            "in our knowledge base. Please try rephrasing, or type 'list categories' "
            "to explore our product catalog."
        )

    history_section = (
        f"\n\nConversation so far:\n{conversation_summary}"
        if conversation_summary else ""
    )

    return (
        f"Based on our knowledge base:{history_section}\n\n"
        f"{context}"
    )
