import os
from pathlib import Path

def load_documents(kb_dir="knowledge_base"):
    """Loads all knowledge base text files safely."""
    base_path = Path(__file__).parent.parent / kb_dir
    documents = []
    
    if not base_path.exists():
        return documents
        
    for file_path in base_path.glob("*.txt"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read().strip()
                if text:
                    documents.append({
                        "text": text,
                        "metadata": {
                            "filename": file_path.name,
                            "category": file_path.stem
                        }
                    })
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            
    return documents
