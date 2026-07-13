"""
routers/ask.py – Question answering endpoint for stadium volunteers.
POST /api/ask
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List

from backend.qa_chain import answer_question

router = APIRouter()


# ── Request / Response Models ────────────────────────────────────────────────

class VolunteerContext(BaseModel):
    zone: str = Field(default="Not specified", max_length=200, description="Stadium zone (e.g., 'North Stand Gate 7')")
    role: str = Field(default="General Volunteer", max_length=200, description="Volunteer role (e.g., 'Medical', 'Security', 'Guest Services')")


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000, description="The volunteer's question")
    language: str = Field(default="en", pattern=r"^(en|es|fr|ar|pt|de)$", description="ISO language code")
    volunteer_context: Optional[VolunteerContext] = None


class EscalationInfo(BaseModel):
    flag: str
    reasoning: str


class SourceInfo(BaseModel):
    filename: str
    sop_title: str
    severity: str
    excerpt: str


class AskResponse(BaseModel):
    success: bool
    question: str
    answer: str
    sources: List[SourceInfo]
    escalation: EscalationInfo
    confidence: str
    language: str
    was_sanitized: bool


# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """
    Ask StadiumOps Copilot a question.

    Retrieves relevant SOP chunks, generates a step-by-step answer via Gemini,
    and returns an escalation flag with reasoning.
    """
    try:
        vol_ctx = None
        if request.volunteer_context:
            vol_ctx = {
                "zone": request.volunteer_context.zone,
                "role": request.volunteer_context.role,
            }

        result = answer_question(
            question=request.question,
            language=request.language,
            volunteer_context=vol_ctx,
        )

        return {
            "success": True,
            "question": request.question,
            "answer": result["answer"],
            "sources": result["sources"],
            "escalation": result["escalation"],
            "confidence": result["confidence"],
            "language": result["language"],
            "was_sanitized": result["was_sanitized"],
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"QA pipeline error: {e}")
