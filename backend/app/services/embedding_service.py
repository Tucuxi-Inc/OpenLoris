"""
Embedding service for generating vector embeddings from text.

Supports multiple backends (in priority order):
1. sentence-transformers (local ML model, best quality)
2. Ollama embeddings API
3. TF-IDF hash embeddings (deterministic fallback, no ML dependencies)

The hash-based fallback produces reasonable similarity scores for similar
texts, enabling the automation pipeline to work in development without
requiring ML models or external services.
"""

import hashlib
import logging
import math
import re
from collections import Counter
from typing import List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generate text embeddings for semantic similarity search."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        dimension: int = 384,
    ):
        self.model_name = model_name
        self.dimension = dimension
        self._model = None

    async def generate(self, text: str) -> List[float]:
        """
        Generate an embedding vector for the given text.

        Priority: Ollama (best quality when available) -> sentence-transformers -> hash fallback.
        """
        # Try Ollama embeddings (preferred - uses nomic-embed-text)
        try:
            return await self._generate_ollama(text)
        except Exception as e:
            logger.debug(f"Ollama embeddings unavailable: {e}")

        # Try sentence-transformers (local ML model)
        try:
            return await self._generate_sentence_transformers(text)
        except Exception as e:
            logger.debug(f"sentence-transformers unavailable: {e}")

        # Fallback: hash-based TF-IDF embedding (always works, no dependencies)
        logger.info("Using hash-based embedding fallback")
        return self._generate_hash_embedding(text)

    def _generate_hash_embedding(self, text: str) -> List[float]:
        """
        Generate a deterministic embedding using token hashing.

        This produces a bag-of-words style vector where similar texts
        will have high cosine similarity. Works without any ML model.

        Approach:
        - Tokenize and normalize text
        - Hash each token to a dimension index
        - Build a sparse vector, then normalize to unit length
        """
        # Tokenize: lowercase, split on non-alphanumeric, filter short tokens
        tokens = re.findall(r'[a-z]+', text.lower())
        tokens = [t for t in tokens if len(t) > 2]  # Drop very short words

        if not tokens:
            return [0.0] * self.dimension

        # Count token frequencies
        token_counts = Counter(tokens)

        # Build vector by hashing tokens to dimensions
        vector = [0.0] * self.dimension

        for token, count in token_counts.items():
            # Hash token to get primary dimension index
            h = int(hashlib.md5(token.encode()).hexdigest(), 16)
            idx = h % self.dimension
            # Use token frequency as weight
            vector[idx] += count

            # Also add bigram-like features using a second hash
            h2 = int(hashlib.sha1(token.encode()).hexdigest(), 16)
            idx2 = h2 % self.dimension
            vector[idx2] += count * 0.5

        # L2-normalize to unit length
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]

        return vector

    async def _generate_sentence_transformers(self, text: str) -> List[float]:
        """Generate embedding using sentence-transformers (runs locally)."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
                logger.info(f"Loaded sentence-transformers model: {self.model_name}")
            except ImportError:
                raise RuntimeError("sentence-transformers not available")

        import asyncio
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None, lambda: self._model.encode(text).tolist()
        )
        return embedding

    async def _generate_ollama(self, text: str) -> List[float]:
        """Generate embedding using Ollama embeddings API."""
        ollama_url = getattr(settings, 'OLLAMA_URL', 'http://host.docker.internal:11434')

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{ollama_url}/api/embeddings",
                json={
                    "model": self.model_name,
                    "prompt": text
                }
            )
            response.raise_for_status()
            data = response.json()
            embedding = data.get("embedding", [])
            if not embedding:
                raise ValueError("Empty embedding returned from Ollama")
            return embedding

    async def generate_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        results = []
        for text in texts:
            embedding = await self.generate(text)
            results.append(embedding)
        return results


# Global instance - uses Ollama nomic-embed-text (768 dims) when available,
# falls back to hash-based embeddings (384 dims) for development without Ollama
embedding_service = EmbeddingService(
    model_name="nomic-embed-text",
    dimension=768
)
