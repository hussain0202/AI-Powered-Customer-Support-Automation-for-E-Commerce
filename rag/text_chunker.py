def chunk_text(documents, chunk_size=400, overlap=100):
    """
    Splits large documents into semantic chunks, preserving meaning 
    and avoiding abrupt cuts where possible.
    """
    chunks = []
    for doc in documents:
        text = doc["text"]
        i = 0
        while i < len(text):
            chunk_end = i + chunk_size
            if chunk_end < len(text):
                # Try to find the nearest space to avoid cutting words
                next_space = text.rfind(' ', i, chunk_end)
                if next_space != -1 and next_space > i + (chunk_size // 2):
                    chunk_end = next_space
            
            chunk_text = text[i:chunk_end].strip()
            if chunk_text:
                chunks.append({
                    "text": chunk_text,
                    "source": doc["metadata"]["filename"],
                    "chunk_id": f"{doc['metadata']['filename']}_{len(chunks)}"
                })
            
            # Step forward, accounting for overlap
            i = chunk_end - overlap if chunk_end < len(text) else len(text)
            
    return chunks
