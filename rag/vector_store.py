import chromadb
from pathlib import Path

_client = None
_collection = None

def get_vector_store():
    """Initializes and returns the persistent ChromaDB local storage."""
    global _client, _collection
    if _client is None:
        db_path = Path(__file__).parent.parent / 'database' / 'chroma_db'
        _client = chromadb.PersistentClient(path=str(db_path))
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
