from .document_loader import load_documents
from .text_chunker import chunk_text
from .vector_store import add_chunks, search

def initialize_retriever():
    """Boots up the RAG pipeline by loading, chunking, and indexing KB documents."""
    docs = load_documents()
    chunks = chunk_text(docs)
    add_chunks(chunks)

def retrieve_context(query: str, top_k: int = 3):
    """Retrieves relevant semantic chunks based on the query."""
    return search(query, top_k)
