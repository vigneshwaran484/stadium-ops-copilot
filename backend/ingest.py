"""
ingest.py – SOP document parsing and chunking.
Reads pre-committed Markdown SOP files from sop_documents/ and splits them
into LangChain Document chunks with rich metadata for retrieval.
"""
import os
import re
from pathlib import Path
from typing import List, Tuple

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.config import CHUNK_SIZE, CHUNK_OVERLAP, SOP_PATH


# Map filename stems to human-readable SOP titles
SOP_TITLES = {
    "medical_emergency": "Medical Emergency Response",
    "lost_child": "Lost or Missing Child",
    "accessibility_wheelchair": "Accessibility & Wheelchair Assistance",
    "crowd_control": "Crowd Control & Escalation",
    "lost_and_found": "Lost & Found",
    "weather_evacuation": "Weather Emergency & Evacuation",
    "security_incident": "Security Incident Response",
    "general_fan_assistance": "General Fan Assistance",
}

# Severity keywords extracted from SOPs for metadata tagging
SEVERITY_MAP = {
    "medical_emergency": "critical",
    "lost_child": "critical",
    "accessibility_wheelchair": "medium",
    "crowd_control": "high",
    "lost_and_found": "low",
    "weather_evacuation": "critical",
    "security_incident": "critical",
    "general_fan_assistance": "low",
}


def _extract_sop_id(text: str) -> str:
    """Extract the SOP ID from the document text if present."""
    match = re.search(r"\*\*SOP ID:\*\*\s*(SOP-[\w-]+)", text)
    return match.group(1) if match else "UNKNOWN"


def _parse_markdown(file_path: str) -> str:
    """Read a Markdown file and return its raw text content."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def ingest_sop(file_path: str, filename: str) -> Tuple[List[Document], str]:
    """
    Parse a single SOP markdown file and split it into chunks.
    Returns a list of LangChain Document objects with metadata and the SOP ID.
    """
    raw_text = _parse_markdown(file_path)
    if not raw_text.strip():
        raise ValueError(f"SOP document appears empty: {filename}")

    stem = Path(filename).stem
    sop_id = _extract_sop_id(raw_text)
    sop_title = SOP_TITLES.get(stem, stem.replace("_", " ").title())
    severity = SEVERITY_MAP.get(stem, "unknown")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""],
    )

    chunks = splitter.create_documents(
        [raw_text],
        metadatas=[{
            "source": filename,
            "sop_id": sop_id,
            "sop_title": sop_title,
            "severity": severity,
        }],
    )

    return chunks, sop_id


def ingest_all_sops() -> List[Document]:
    """
    Discover and ingest all SOP markdown files from the configured SOP_PATH.
    Returns a flat list of all Document chunks across all SOPs.
    """
    all_chunks: List[Document] = []

    if not os.path.isdir(SOP_PATH):
        raise FileNotFoundError(f"SOP directory not found: {SOP_PATH}")

    md_files = sorted(
        f for f in os.listdir(SOP_PATH) if f.endswith(".md")
    )

    if not md_files:
        raise FileNotFoundError(f"No .md files found in {SOP_PATH}")

    for filename in md_files:
        file_path = os.path.join(SOP_PATH, filename)
        chunks, sop_id = ingest_sop(file_path, filename)
        all_chunks.extend(chunks)
        print(f"[INGEST] {filename} -> {len(chunks)} chunks (SOP: {sop_id})", flush=True)

    print(f"[INGEST] Total: {len(all_chunks)} chunks from {len(md_files)} SOPs", flush=True)
    return all_chunks
