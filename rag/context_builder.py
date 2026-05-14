MAX_DISTANCE = 1.2  # ChromaDB L2 distance ceiling — chunks above this are too weak


def build_context(retrieved_chunks, score_threshold: float = MAX_DISTANCE) -> str:
    """
    Combines retrieved chunks into a clean context string for the response generator.

    Improvements over the original:
    - Sorts by relevance score ascending (ChromaDB L2: lower distance = better match)
    - Drops chunks whose distance exceeds score_threshold (low-quality matches)
    - Falls back to all chunks if the threshold would leave nothing
    - Separates sources with a divider for easier LLM parsing
    """
    if not retrieved_chunks:
        return ""

    # Sort best-first (ascending distance)
    sorted_chunks = sorted(retrieved_chunks, key=lambda c: c.get("score", float("inf")))

    # Filter by quality threshold; fall back to everything if all are above threshold
    filtered = [c for c in sorted_chunks if c.get("score", 0) <= score_threshold]
    if not filtered:
        filtered = sorted_chunks

    seen = set()
    context_blocks = []

    for chunk in filtered:
        text = chunk["text"].strip()
        if text and text not in seen:
            seen.add(text)
            source = chunk.get("source", "knowledge base")
            context_blocks.append(f"[{source}]\n{text}")

    return "\n\n---\n\n".join(context_blocks)
