"""
run.py – Server entry point
Usage: python run.py
"""
import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    is_dev = os.environ.get("ENV", "development") == "development"

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=port,
        reload=is_dev,
        reload_dirs=["backend"] if is_dev else None,
    )