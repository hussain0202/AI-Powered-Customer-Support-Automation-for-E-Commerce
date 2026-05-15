import chromadb
from pathlib import Path

_client = None
_collection = None


def _make_client(db_path: str) -> chromadb.PersistentClient:
    """Create a PersistentClient, recovering from Rust-bindings cleanup errors.

    On Streamlit hot-reload the module globals reset to None, but ChromaDB's
    internal shared-system table still holds a reference to the now-broken
    RustBindingsAPI object.  When a new client is created it tries to call
    stop() on that stale object, which raises AttributeError because 'bindings'
    was never fully initialised.  We catch that, force-clear the internal
    registry, and retry — the second attempt succeeds cleanly.
    """
    try:
        return chromadb.PersistentClient(path=db_path)
    except AttributeError:
        # Clear the broken shared-system state and retry once
        try:
            from chromadb.api.shared_system_client import SharedSystemClient
            for key in list(getattr(SharedSystemClient, "_identifier_to_system", {}).keys()):
                try:
                    del SharedSystemClient._identifier_to_system[key]
                except Exception:
                    pass
            for key in list(getattr(SharedSystemClient, "_identifier_to_system_ref_count", {}).keys()):
                try:
                    del SharedSystemClient._identifier_to_system_ref_count[key]
                except Exception:
                    pass
        except Exception:
            pass
        return chromadb.PersistentClient(path=db_path)


def get_vector_store():
    """Initializes and returns the persistent ChromaDB local storage."""
    global _client, _collection
    if _client is None:
        db_path = str(Path(__file__).parent.parent / "database" / "chroma_db")
        _client = _make_client(db_path)
        _collection = _client.get_or_create_collection(name="ecommerce_knowledge")
    return _collection

def add_chunks(chunks):
    """Embeds and inserts chunks into the Vector DB. Skips if already loaded."""
    collection = get_vector_store()
    existing = collection.get()
    
    if len(existing["ids"]) > 0:
        return # DB already populated
        
    if not chunks:
        return
        
    ids = [c["chunk_id"] for c in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [{"source": c["source"]} for c in chunks]
    
    from .embedding_manager import generate_embeddings
    embeddings = generate_embeddings(documents)
    
    collection.add(
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids
    )

def search(query: str, top_k: int = 3):
    """Performs semantic vector search for top-k relevant chunks."""
    collection = get_vector_store()
    
    from .embedding_manager import generate_embeddings
    query_embedding = generate_embeddings([query])[0]
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )
    
    retrieved = []
    if results["documents"] and results["documents"][0]:
        for i in range(len(results["documents"][0])):
            retrieved.append({
                "text": results["documents"][0][i],
                "score": results["distances"][0][i] if "distances" in results and results["distances"] else 0.0,
                "source": results["metadatas"][0][i]["source"]
            })
            
    return retrieved
