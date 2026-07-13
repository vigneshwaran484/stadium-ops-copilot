"""
main.py – FastAPI application entry point.
Mounts all routers, serves the frontend as static files, and auto-ingests
SOP documents into the FAISS vector store on startup if not already indexed.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.routers import ask


# ── Startup: auto-ingest SOPs ────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run SOP ingestion on startup if the vector store is empty."""
    from backend.vectorstore import index_exists, create_from_documents
    from backend.ingest import ingest_all_sops

    if not index_exists():
        print("[STARTUP] No FAISS index found — ingesting SOP documents...", flush=True)
        try:
            chunks = ingest_all_sops()
            create_from_documents(chunks)
            print("[STARTUP] SOP ingestion complete.", flush=True)
        except Exception as e:
            print(f"[STARTUP] SOP ingestion failed: {e}", flush=True)
            print("[STARTUP] The /api/ask endpoint will return errors until SOPs are indexed.", flush=True)
    else:
        print("[STARTUP] FAISS index already exists — skipping ingestion.", flush=True)

    yield  # App runs here


# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="StadiumOps Copilot",
    description=(
        "AI-powered volunteer assistant for Smart Stadium & Tournament Operations. "
        "Retrieves relevant SOPs and provides step-by-step guidance with escalation decisions."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routers ───────────────────────────────────────────────────────────────
app.include_router(ask.router, prefix="/api", tags=["Ask"])


# ── Health Check ─────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["Health"])
async def health():
    from backend.vectorstore import index_exists
    return {
        "status": "ok",
        "service": "StadiumOps Copilot",
        "index_ready": index_exists(),
    }


# ── Serve Frontend Static Files ──────────────────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    @app.get("/{full_path:path}", include_in_schema=False)
    async def catch_all(full_path: str):
        file_path = os.path.join(FRONTEND_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
