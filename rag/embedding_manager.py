from sentence_transformers import SentenceTransformer

_model = None

def get_embedding_model():
    """Singleton pattern to load the embedding model once globally."""
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def generate_embeddings(texts: list):
    """Generates embeddings for a batch of texts."""
    model = get_embedding_model()
    # return as list of floats for ChromaDB compatibility
    return model.encode(texts, batch_size=32).tolist()
