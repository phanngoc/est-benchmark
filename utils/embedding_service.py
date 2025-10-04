"""
Embedding Service for text vectorization using OpenAI
"""
import os
from typing import List, Optional
from openai import OpenAI
import hashlib
import json
from pathlib import Path


class EmbeddingService:
    """Service for generating and caching text embeddings"""

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
        self.cache_dir = Path("./embedding_cache")
        self.cache_dir.mkdir(exist_ok=True)

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key from text"""
        return hashlib.md5(f"{self.model}:{text}".encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path"""
        return self.cache_dir / f"{cache_key}.json"

    def _load_from_cache(self, text: str) -> Optional[List[float]]:
        """Load embedding from cache if exists"""
        cache_key = self._get_cache_key(text)
        cache_path = self._get_cache_path(cache_key)

        if cache_path.exists():
            try:
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                    return data.get('embedding')
            except Exception as e:
                print(f"⚠️ Cache read error: {e}")
                return None
        return None

    def _save_to_cache(self, text: str, embedding: List[float]):
        """Save embedding to cache"""
        cache_key = self._get_cache_key(text)
        cache_path = self._get_cache_path(cache_key)

        try:
            with open(cache_path, 'w') as f:
                json.dump({
                    'text': text[:100],  # Save snippet for reference
                    'embedding': embedding,
                    'model': self.model
                }, f)
        except Exception as e:
            print(f"⚠️ Cache write error: {e}")

    def generate_embedding(self, text: str, use_cache: bool = True) -> List[float]:
        """
        Generate embedding for text

        Args:
            text: Text to embed
            use_cache: Whether to use cache (default: True)

        Returns:
            List of embedding values
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        # Try cache first
        if use_cache:
            cached = self._load_from_cache(text)
            if cached is not None:
                return cached

        try:
            # Generate embedding via API
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"
            )

            embedding = response.data[0].embedding

            # Cache the result
            if use_cache:
                self._save_to_cache(text, embedding)

            return embedding

        except Exception as e:
            raise RuntimeError(f"Failed to generate embedding: {e}")

    def generate_batch_embeddings(
        self,
        texts: List[str],
        use_cache: bool = True
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts

        Args:
            texts: List of texts to embed
            use_cache: Whether to use cache

        Returns:
            List of embeddings
        """
        embeddings = []
        uncached_texts = []
        uncached_indices = []

        # Check cache for each text
        for i, text in enumerate(texts):
            if use_cache:
                cached = self._load_from_cache(text)
                if cached is not None:
                    embeddings.append(cached)
                    continue

            uncached_texts.append(text)
            uncached_indices.append(i)
            embeddings.append(None)  # Placeholder

        # Batch generate uncached embeddings
        if uncached_texts:
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=uncached_texts,
                    encoding_format="float"
                )

                for i, embedding_data in enumerate(response.data):
                    embedding = embedding_data.embedding
                    original_index = uncached_indices[i]
                    embeddings[original_index] = embedding

                    # Cache the result
                    if use_cache:
                        self._save_to_cache(uncached_texts[i], embedding)

            except Exception as e:
                raise RuntimeError(f"Failed to generate batch embeddings: {e}")

        return embeddings

    def get_dimension(self) -> int:
        """Get embedding dimension for the current model"""
        if "text-embedding-3-small" in self.model:
            return 1536
        elif "text-embedding-3-large" in self.model:
            return 3072
        elif "text-embedding-ada-002" in self.model:
            return 1536
        else:
            # Generate a test embedding to get dimension
            test_embedding = self.generate_embedding("test", use_cache=False)
            return len(test_embedding)


# Singleton instance
_embedding_service_instance = None

def get_embedding_service() -> EmbeddingService:
    """Get or create singleton EmbeddingService instance"""
    global _embedding_service_instance
    if _embedding_service_instance is None:
        _embedding_service_instance = EmbeddingService()
    return _embedding_service_instance
