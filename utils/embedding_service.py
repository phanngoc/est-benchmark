"""
Embedding Service for text vectorization using OpenAI
"""
import os
from typing import List, Optional
from openai import OpenAI


class EmbeddingService:
    """Service for generating text embeddings"""

    def __init__(self, api_key: Optional[str] = None, model: str = "text-embedding-3-small"):
        """
        Initialize embedding service

        Args:
            api_key: OpenAI API key (defaults to env variable)
            model: Embedding model to use (default: text-embedding-3-small)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment or provided")

        self.client = OpenAI(api_key=self.api_key)
        self.model = model

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text

        Args:
            text: Text to embed

        Returns:
            List of embedding values
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        try:
            # Generate embedding via API
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"
            )

            embedding = response.data[0].embedding
            return embedding

        except Exception as e:
            raise RuntimeError(f"Failed to generate embedding: {e}")

    def generate_batch_embeddings(
        self,
        texts: List[str]
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts

        Args:
            texts: List of texts to embed

        Returns:
            List of embeddings
        """
        if not texts:
            return []

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts,
                encoding_format="float"
            )

            embeddings = [embedding_data.embedding for embedding_data in response.data]
            return embeddings

        except Exception as e:
            raise RuntimeError(f"Failed to generate batch embeddings: {e}")



# Singleton instance
_embedding_service_instance = None

def get_embedding_service() -> EmbeddingService:
    """Get or create singleton EmbeddingService instance"""
    global _embedding_service_instance
    if _embedding_service_instance is None:
        _embedding_service_instance = EmbeddingService()
    return _embedding_service_instance
