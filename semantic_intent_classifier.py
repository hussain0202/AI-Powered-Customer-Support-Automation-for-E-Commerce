import json
import logging
import hashlib
import numpy as np
import torch
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Configure structured logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SemanticIntentClassifier:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', examples_file: str = 'intent_examples.json'):
        """Initializes the classifier, loads the model once globally, and prepares embeddings."""
        self.model_name = model_name
        self.examples_path = Path(__file__).parent / examples_file
        self.cache_path = Path(__file__).parent / 'database' / 'embeddings_cache.npz'
        
        self.example_texts = []
        self.example_labels = []
        self.intent_embeddings = None
        
        logger.info(f"Loading SentenceTransformer model: {model_name}")
        self.model = SentenceTransformer(self.model_name)
        
        self._initialize_pipeline()

    def _initialize_pipeline(self):
        """Loads examples and prepares embeddings either from disk cache or via generation."""
        self.load_examples()
        
        # Calculate a hash of the normalized examples to safely invalidate cache if data changes
        examples_hash = self._compute_hash(self.example_texts)
        
        if self._load_cached_embeddings(examples_hash):
            logger.info("Successfully loaded intent embeddings from disk cache.")
        else:
            logger.info("Generating new intent embeddings (batch processing)...")
            self.generate_embeddings()
            self.save_embeddings(examples_hash)

    def _compute_hash(self, texts: list) -> str:
        """Computes a SHA256 hash of the concatenated texts to detect changes."""
        concatenated = "|".join(texts)
        return hashlib.sha256(concatenated.encode('utf-8')).hexdigest()

    def preprocess_text(self, text: str) -> str:
        """Lightweight text normalization before embedding."""
        if not text:
            return ""
        text = text.lower()
        text = text.strip()
        text = " ".join(text.split()) # collapse repeated spaces
        return text

    def load_examples(self):
        """Loads intent examples from the JSON file."""
        logger.info(f"Loading intent examples from {self.examples_path}")
        with open(self.examples_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        for intent, examples in data.items():
            for text in examples:
                norm_text = self.preprocess_text(text)
                self.example_texts.append(norm_text)
                self.example_labels.append(intent)

    def generate_embeddings(self, batch_size: int = 32):
        """Generates embeddings using batch encoding, optimizing for performance and scalability."""
        tensor_embeddings = self.model.encode(self.example_texts, batch_size=batch_size, convert_to_tensor=True)
        # Convert to numpy for sklearn cosine similarity and disk caching
        self.intent_embeddings = tensor_embeddings.cpu().numpy()

    def save_embeddings(self, hash_val: str):
        """Persists the generated embeddings to disk to prevent recomputation on restart."""
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(self.cache_path, embeddings=self.intent_embeddings, hash_val=np.array([hash_val]))
            logger.info(f"Saved embeddings to {self.cache_path}")
        except Exception as e:
            logger.error(f"Failed to save embeddings: {e}")

    def _load_cached_embeddings(self, current_hash: str) -> bool:
        """Attempts to load embeddings from disk and validates the hash."""
        if not self.cache_path.exists():
            return False
            
        try:
            data = np.load(self.cache_path)
            cached_hash = data['hash_val'][0]
            if cached_hash == current_hash:
                self.intent_embeddings = data['embeddings']
                return True
            else:
                logger.info("Cache invalidated: intent_examples.json has changed.")
                return False
        except Exception as e:
            logger.error(f"Failed to load cached embeddings: {e}")
            return False

    def predict_intent(self, user_query: str, top_k: int = 3) -> dict:
        """
        Predicts intent using Cosine Similarity against cached embeddings.
        Returns top-K matches and confidence thresholds.
        """
        norm_query = self.preprocess_text(user_query)
        logger.info(f"Incoming query: '{norm_query}'")
        
        query_embedding = self.model.encode([norm_query], convert_to_tensor=True).cpu().numpy()
        similarities = cosine_similarity(query_embedding, self.intent_embeddings)[0]
        
        # Get indices of top K similarities
        top_k_idx = np.argsort(similarities)[::-1][:top_k]
        
        top_matches = []
        for idx in top_k_idx:
            top_matches.append({
                "intent": self.example_labels[idx],
                "score": float(similarities[idx]),
                "matched_example": self.example_texts[idx]
            })
            
        best_match = top_matches[0]
        best_score = best_match['score']
        predicted_intent = best_match['intent']
        
        # Strict Confidence Thresholding
        if best_score >= 0.75:
            confidence_level = "HIGH"
        elif best_score >= 0.55:
            confidence_level = "MEDIUM"
        elif best_score >= 0.40:
            confidence_level = "LOW"
        else:
            confidence_level = "UNKNOWN"
            predicted_intent = "unknown"
            
        logger.info(f"Predicted: {predicted_intent} | Score: {best_score:.4f} | Confidence: {confidence_level}")
        
        return {
            "query": user_query,
            "intent": predicted_intent,
            "confidence": confidence_level,
            "score": best_score,
            "matched_example": best_match['matched_example'] if confidence_level != "UNKNOWN" else None,
            "top_matches": top_matches
        }

# Global Singleton instantiation for Streamlit optimization (avoids reloading on UI reruns)
_classifier_instance = None

def get_classifier() -> SemanticIntentClassifier:
    """Lazy initialization of the classifier singleton."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = SemanticIntentClassifier()
    return _classifier_instance

def predict_intent(user_query: str) -> dict:
    """Wrapper function to maintain modularity and API backwards compatibility."""
    classifier = get_classifier()
    return classifier.predict_intent(user_query)
