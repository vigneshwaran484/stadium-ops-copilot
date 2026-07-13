"""
vectorstore.py – FAISS vector store management.
Single shared index for all SOP documents (no per-user isolation needed).
"""
import os
from typing import List, Optional

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

from backend.config import VECTORSTORE_PATH
from backend.embeddings import get_embeddings

# In-memory cached FAISS instance
_store: Optional[FAISS] = None

FAISS_INDEX_DIR = os.path.join(VECTORSTORE_PATH, "faiss_index")


def _load_from_disk() -> Optional[FAISS]:
    """Attempt to load a persisted FAISS index from disk."""
    if not os.path.exists(FAISS_INDEX_DIR):
        return None
    try:
        store = FAISS.load_local(
            FAISS_INDEX_DIR,
            get_embeddings(),
            allow_dangerous_deserialization=True,
        )
        print(f"[VS] Loaded FAISS index from {FAISS_INDEX_DIR}", flush=True)
        return store
    except Exception as e:
        print(f"[VS] Failed to load FAISS index: {e}", flush=True)
        return None


def create_from_documents(docs: List[Document]) -> FAISS:
    """Create a new FAISS index from a list of Document chunks and persist it."""
    global _store
    embeddings = get_embeddings()
    _store = FAISS.from_documents(docs, embeddings)
    _store.save_local(FAISS_INDEX_DIR)
    print(f"[VS] Created and saved FAISS index with {len(docs)} chunks", flush=True)
    return _store


def get_vectorstore() -> Optional[FAISS]:
    """Return the current FAISS index, loading from disk if needed."""
    global _store
    if _store is not None:
        return _store
    _store = _load_from_disk()
    return _store


def search(query: str, k: int = 4) -> List[Document]:
    """
    Search the vector store for the top-k most relevant chunks.

    Args:
        query: The search query string.
        k: Number of results to return.

    Returns:
        List of Document objects, ordered by relevance.
    """
    store = get_vectorstore()
    if store is None:
        raise ValueError("Vector store not initialised. Run SOP ingestion first.")
    return store.similarity_search(query, k=k)


def index_exists() -> bool:
    """Check whether a FAISS index is available (in memory or on disk)."""
    if _store is not None:
        return True
    return os.path.exists(os.path.join(FAISS_INDEX_DIR, "index.faiss"))
