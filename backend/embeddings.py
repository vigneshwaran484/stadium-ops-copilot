"""
embeddings.py – Gemini embedding wrapper implementing LangChain Embeddings interface.
Uses Google's text-embedding-004 model (768 dimensions) via the google-genai SDK.
No local model weights — all embeddings are API-based to keep repo under 10MB.
"""
from typing import List
from functools import lru_cache

from langchain.embeddings.base import Embeddings
from google import genai

from backend.config import GEMINI_API_KEY, GEMINI_EMBEDDING_MODEL


class GeminiEmbeddings(Embeddings):
    """LangChain-compatible wrapper around Google Gemini Embeddings API."""

    def __init__(self, api_key: str = None, model: str = None):
        self._api_key = api_key or GEMINI_API_KEY
        self._model = model or GEMINI_EMBEDDING_MODEL
        self._client = genai.Client(api_key=self._api_key)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of document texts. Batches automatically."""
        if not texts:
            return []
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query string."""
        result = self._client.models.embed_content(
            model=self._model,
            contents=[text],
        )
        return result.embeddings[0].values


@lru_cache(maxsize=1)
def get_embeddings() -> GeminiEmbeddings:
    """Return a cached singleton GeminiEmbeddings instance."""
    return GeminiEmbeddings()
