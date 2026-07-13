"""
config.py – Centralised configuration loaded from .env
"""
import os
from dotenv import load_dotenv

load_dotenv(override=True)

# ── Gemini API (For Embeddings) ──────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_EMBEDDING_MODEL: str = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2")

# ── Groq API (For Text Generation) ───────────────────────────────────────────
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# ── Chunking & Retrieval ─────────────────────────────────────────────────────
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))
TOP_K: int = int(os.getenv("TOP_K", "4"))

# ── Paths ────────────────────────────────────────────────────────────────────
VECTORSTORE_PATH: str = os.getenv("VECTORSTORE_PATH", "./vectorstore")
SOP_PATH: str = os.getenv("SOP_PATH", "./sop_documents")

# Ensure directories exist
os.makedirs(VECTORSTORE_PATH, exist_ok=True)
