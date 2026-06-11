"""Text embeddings for semantic search"""
from typing import List
from sentence_transformers import SentenceTransformer
from nexus.utils.logger import logger


class Embeddings:
    """Text embeddings using sentence transformers"""

    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        try:
            self.model = SentenceTransformer(model_name)
            logger.info(f"Embedding model loaded: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self.model = None

    def encode(self, text: str) -> List[float]:
        """Encode text to embedding vector"""
        if not self.model:
            return []

        try:
            embedding = self.model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Encoding failed: {e}")
            return []

    def encode_batch(self, texts: List[str]) -> List[List[float]]:
        """Encode multiple texts"""
        if not self.model:
            return [[]]

        try:
            embeddings = self.model.encode(texts)
            return [e.tolist() for e in embeddings]
        except Exception as e:
            logger.error(f"Batch encoding failed: {e}")
            return [[]]

    def similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts"""
        try:
            emb1 = self.encode(text1)
            emb2 = self.encode(text2)

            if not emb1 or not emb2:
                return 0.0

            import numpy as np
            return float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2)))
        except Exception as e:
            logger.error(f"Similarity calculation failed: {e}")
            return 0.0