"""
Run this script once after updating knowledge_base files to clear and re-seed ChromaDB.
Usage: python reset_chromadb.py

If the app is running, ChromaDB files may be locked — in that case stop the app first,
or this script will use the ChromaDB client API to delete + recreate the collection.
"""

import shutil
from pathlib import Path

CHROMA_DIR = Path(__file__).parent / "database" / "chroma_db"

# Try ChromaDB API first (works even if app is not running, avoids file-lock issues)
try:
    import chromadb
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    existing = client.list_collections()
    names = [c.name for c in existing]
    if "ecommerce_knowledge" in names:
        client.delete_collection("ecommerce_knowledge")
        print("Deleted existing 'ecommerce_knowledge' collection via ChromaDB API.")
    else:
        print("Collection not found — starting fresh.")
    del client
except Exception as e:
    print(f"ChromaDB API delete failed ({e}), trying file-level delete...")
    if CHROMA_DIR.exists():
        try:
            shutil.rmtree(CHROMA_DIR)
            print(f"Deleted ChromaDB directory: {CHROMA_DIR}")
        except PermissionError:
            print(
                "ERROR: ChromaDB files are locked by another process (Streamlit app is probably running).\n"
                "Please stop the Streamlit app first, then run this script again."
            )
            raise SystemExit(1)

print("Re-seeding ChromaDB from knowledge_base files...")
from rag.retriever import initialize_retriever
initialize_retriever()
print("Done! ChromaDB re-seeded with updated FAQ and knowledge base content.")
