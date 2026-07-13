"""
qa_chain.py – RAG pipeline: sanitize → retrieve → prompt → Gemini (structured JSON) → parse.

This is where GenAI decision-making lives. The pipeline:
1. Sanitises user input (prompt-injection guard)
2. Retrieves top-K relevant SOP chunks from FAISS
3. Builds a structured prompt with volunteer context and language instruction
4. Calls Gemini with response_mime_type="application/json" and a strict schema
5. Parses the structured response for answer, escalation flag, reasoning, and sources

The escalation decision uses a dual-signal approach:
  - Keyword signal: severity keywords detected in retrieved SOP chunks
  - LLM signal:     Gemini's own assessment based on the SOP context
  If EITHER signal says "escalate", the final flag is "escalate".
"""
import json
from typing import Any, Dict, List, Optional

from backend.sanitizer import sanitize_input
from backend.vectorstore import search
from backend.llm import generate_answer
from backend.config import TOP_K


# ── Severity keywords that trigger automatic escalation ──────────────────────
ESCALATION_KEYWORDS = [
    # Medical
    "unconscious", "unresponsive", "not breathing", "no pulse", "cardiac",
    "cardiac arrest", "cpr", "aed", "seizure", "anaphylaxis", "choking",
    "severe bleeding", "uncontrolled bleeding", "head injury", "heat stroke",
    # Child safety
    "missing child", "lost child", "code adam", "abduction", "unaccompanied",
    # Security
    "weapon", "firearm", "knife", "bomb", "bomb threat", "active threat",
    "active shooter", "suspicious package", "explosive", "terrorism",
    # Crowd
    "crush", "stampede", "crowd surge", "crush risk",
    # Weather
    "tornado", "tornado warning", "evacuation", "lightning",
    # General critical
    "emergency", "911", "life-threatening", "critical",
]


# ── Gemini response schema for structured output ────────────────────────────
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {
            "type": "string",
            "description": "Step-by-step instructions for the volunteer to follow, in the requested language.",
        },
        "escalation_flag": {
            "type": "string",
            "enum": ["escalate", "self_resolve"],
            "description": "Whether this situation requires escalation to a supervisor or can be handled by the volunteer.",
        },
        "escalation_reasoning": {
            "type": "string",
            "description": "Brief explanation of why the situation does or does not require escalation.",
        },
        "confidence": {
            "type": "string",
            "enum": ["high", "medium", "low"],
            "description": "Confidence level in the answer based on SOP coverage.",
        },
    },
    "required": ["answer", "escalation_flag", "escalation_reasoning", "confidence"],
}


# ── Prompt template ─────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are StadiumOps Copilot, an AI assistant for stadium volunteers and staff during a major international football tournament (FIFA World Cup 2026 scale).

Your role is to provide clear, actionable, step-by-step guidance based ONLY on the official Standard Operating Procedures (SOPs) provided below. You help volunteers handle real-time situations ranging from medical emergencies to general fan assistance.

RULES:
- Answer ONLY based on the provided SOP context. If the answer is not in the SOPs, say so clearly.
- Provide step-by-step numbered instructions when applicable.
- Include relevant radio channels, contact numbers, and key details from the SOPs.
- Assess the severity of the situation and determine whether the volunteer should ESCALATE to a supervisor or can SELF-RESOLVE the situation.
- Consider the volunteer's zone and role when tailoring your response.
- Respond in the language specified by the user. If no language is specified, respond in English.

ESCALATION CRITERIA:
- Flag as "escalate" if the situation involves life-threatening conditions, critical severity SOPs, security threats, missing children, medical emergencies, dangerous crowd levels, or any scenario where the SOP explicitly states "ESCALATE IF".
- Flag as "self_resolve" if the situation is routine (directions, lost items of low value, general information, accessibility guidance that can be directly provided).
"""


def _build_prompt(
    question: str,
    context_chunks: List[Any],
    language: str = "en",
    volunteer_context: Optional[Dict[str, str]] = None,
) -> str:
    """Assemble the full prompt from system instructions, SOP context, and user query."""

    # Format retrieved SOP chunks with source attribution
    context_parts = []
    for i, doc in enumerate(context_chunks, 1):
        source = doc.metadata.get("source", "Unknown")
        sop_title = doc.metadata.get("sop_title", "Unknown SOP")
        severity = doc.metadata.get("severity", "unknown")
        context_parts.append(
            f"--- SOP Chunk {i} ---\n"
            f"Source: {source} | Title: {sop_title} | Severity: {severity}\n"
            f"{doc.page_content}\n"
        )
    context_text = "\n".join(context_parts)

    # Format volunteer context
    vol_context = ""
    if volunteer_context:
        zone = volunteer_context.get("zone", "Not specified")
        role = volunteer_context.get("role", "General Volunteer")
        vol_context = f"\nVolunteer Zone: {zone}\nVolunteer Role: {role}\n"

    # Language mapping for natural instruction
    language_names = {
        "en": "English", "es": "Spanish", "fr": "French",
        "ar": "Arabic", "pt": "Portuguese", "de": "German",
    }
    lang_name = language_names.get(language, language)
    lang_instruction = f"\nRespond in {lang_name}."

    prompt = f"""{SYSTEM_PROMPT}

=== RETRIEVED SOP CONTEXT ===
{context_text}
=== END SOP CONTEXT ===
{vol_context}
{lang_instruction}

Volunteer's Question: {question}"""

    return prompt


def _check_keyword_escalation(chunks: List[Any]) -> bool:
    """
    Scan retrieved chunks for severity keywords that warrant automatic escalation.
    Returns True if any escalation keyword is found.
    """
    combined_text = " ".join(doc.page_content.lower() for doc in chunks)
    return any(keyword in combined_text for keyword in ESCALATION_KEYWORDS)


def answer_question(
    question: str,
    language: str = "en",
    volunteer_context: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Run the full RAG pipeline for a volunteer's question.

    Args:
        question: The volunteer's question text (will be sanitised).
        language: ISO language code for the response (default: "en").
        volunteer_context: Optional dict with "zone" and "role" keys.

    Returns:
        Dict with keys: answer, sources, escalation (flag + reasoning),
        language, was_sanitized.
    """
    # 1. Sanitise input
    clean_question, was_sanitized = sanitize_input(question)
    if not clean_question:
        return {
            "answer": "I couldn't understand your question. Please try rephrasing.",
            "sources": [],
            "escalation": {"flag": "self_resolve", "reasoning": "Empty or invalid input."},
            "language": language,
            "was_sanitized": was_sanitized,
        }

    # 2. Retrieve relevant SOP chunks
    chunks = search(clean_question, k=TOP_K)

    # 3. Keyword-based escalation signal
    keyword_escalate = _check_keyword_escalation(chunks)

    # 4. Build prompt and call Gemini with structured JSON output
    prompt = _build_prompt(clean_question, chunks, language, volunteer_context)

    raw_response = generate_answer(
        prompt=prompt,
        temperature=0.2,
        max_tokens=2048,
        response_mime_type="application/json",
        response_schema=RESPONSE_SCHEMA,
    )

    # 5. Parse structured response
    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError:
        # Fallback: treat as plain text answer with default escalation
        parsed = {
            "answer": raw_response,
            "escalation_flag": "escalate" if keyword_escalate else "self_resolve",
            "escalation_reasoning": "Response parsing failed; defaulting based on keyword analysis.",
            "confidence": "low",
        }

    # 6. Dual-signal escalation: if EITHER keyword or LLM says escalate, escalate
    llm_flag = parsed.get("escalation_flag", "self_resolve")
    final_flag = "escalate" if (keyword_escalate or llm_flag == "escalate") else "self_resolve"

    # 7. Build source citations
    sources = []
    seen = set()
    for doc in chunks:
        src = doc.metadata.get("source", "Unknown")
        if src not in seen:
            seen.add(src)
            sources.append({
                "filename": src,
                "sop_title": doc.metadata.get("sop_title", "Unknown SOP"),
                "severity": doc.metadata.get("severity", "unknown"),
                "excerpt": doc.page_content[:300] + ("..." if len(doc.page_content) > 300 else ""),
            })

    reasoning = parsed.get("escalation_reasoning", "")
    if keyword_escalate and llm_flag != "escalate":
        reasoning += " [Keyword override: severity keywords detected in matched SOP chunks.]"

    return {
        "answer": parsed.get("answer", "No answer generated."),
        "sources": sources,
        "escalation": {
            "flag": final_flag,
            "reasoning": reasoning,
        },
        "confidence": parsed.get("confidence", "medium"),
        "language": language,
        "was_sanitized": was_sanitized,
    }
