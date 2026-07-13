"""
test_qa_chain.py – Tests for the RAG pipeline's retrieval and escalation logic.

Tests are split into two categories:
  1. Keyword escalation logic (pure logic, no API calls)
  2. Full pipeline integration (requires GEMINI_API_KEY + FAISS index)

Integration tests are marked with @pytest.mark.integration and skipped
if the FAISS index or API key is not available.
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document

from backend.qa_chain import _check_keyword_escalation, ESCALATION_KEYWORDS


# ── Helper: create mock Document objects ─────────────────────────────────────

def _make_doc(content: str, source: str = "test.md", severity: str = "low") -> Document:
    """Create a mock LangChain Document for testing."""
    return Document(
        page_content=content,
        metadata={
            "source": source,
            "sop_title": "Test SOP",
            "severity": severity,
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 1. KEYWORD ESCALATION TESTS (pure logic, no API)
# ═══════════════════════════════════════════════════════════════════════════════

class TestKeywordEscalation:
    """Test the keyword-based escalation signal in isolation."""

    def test_medical_keywords_trigger_escalation(self):
        """Chunks mentioning cardiac arrest should trigger escalation."""
        chunks = [
            _make_doc(
                "If the patient is unconscious and not breathing, begin CPR immediately. "
                "Request AED to location. This is a cardiac arrest emergency.",
                source="medical_emergency.md",
                severity="critical",
            ),
        ]
        assert _check_keyword_escalation(chunks) is True

    def test_security_keywords_trigger_escalation(self):
        """Chunks mentioning suspicious package should trigger escalation."""
        chunks = [
            _make_doc(
                "Do NOT touch the suspicious package. Clear the area to 30 meters. "
                "Radio Security Command immediately.",
                source="security_incident.md",
                severity="critical",
            ),
        ]
        assert _check_keyword_escalation(chunks) is True

    def test_lost_child_keywords_trigger_escalation(self):
        """Chunks mentioning Code Adam / missing child should trigger escalation."""
        chunks = [
            _make_doc(
                "Code Adam activated. A missing child has been reported in the East Concourse. "
                "All exits are being monitored. The lost child is 6 years old.",
                source="lost_child.md",
                severity="critical",
            ),
        ]
        assert _check_keyword_escalation(chunks) is True

    def test_weather_evacuation_keywords_trigger_escalation(self):
        """Chunks mentioning tornado/evacuation should trigger escalation."""
        chunks = [
            _make_doc(
                "A tornado warning has been issued. Begin evacuation protocol immediately. "
                "Direct fans to interior shelter zones.",
                source="weather_evacuation.md",
                severity="critical",
            ),
        ]
        assert _check_keyword_escalation(chunks) is True

    def test_routine_query_no_escalation(self):
        """Chunks about general directions should NOT trigger escalation."""
        chunks = [
            _make_doc(
                "Restrooms are located near every section entrance. "
                "The Fan Shop is at Section 115. Concessions are on the main concourse.",
                source="general_fan_assistance.md",
                severity="low",
            ),
        ]
        assert _check_keyword_escalation(chunks) is False

    def test_lost_item_low_severity_no_escalation(self):
        """Routine lost sunglasses should NOT trigger escalation."""
        chunks = [
            _make_doc(
                "For lost personal items, gather details from the fan including "
                "description, last known location, and contact information. "
                "Direct them to the Guest Services Center.",
                source="lost_and_found.md",
                severity="low",
            ),
        ]
        assert _check_keyword_escalation(chunks) is False

    def test_empty_chunks_no_escalation(self):
        """Empty chunk list should not trigger escalation."""
        assert _check_keyword_escalation([]) is False

    def test_mixed_chunks_escalation_wins(self):
        """If ANY chunk contains escalation keywords, escalation triggers."""
        chunks = [
            _make_doc(
                "The nearest restroom is at Section 108.",
                source="general_fan_assistance.md",
                severity="low",
            ),
            _make_doc(
                "If the patient is unconscious, call 911 immediately.",
                source="medical_emergency.md",
                severity="critical",
            ),
        ]
        assert _check_keyword_escalation(chunks) is True


# ═══════════════════════════════════════════════════════════════════════════════
# 2. ESCALATION SCENARIO TESTS (mocked LLM + retrieval)
# ═══════════════════════════════════════════════════════════════════════════════

class TestEscalationScenarios:
    """
    Test the full escalation logic with mocked LLM and retrieval.
    These verify the dual-signal approach (keyword + LLM) without API calls.
    """

    def _mock_answer(self, question, mock_chunks, llm_flag="self_resolve"):
        """Run answer_question with mocked search and LLM."""
        mock_llm_response = (
            '{"answer": "Test answer", '
            f'"escalation_flag": "{llm_flag}", '
            '"escalation_reasoning": "Test reasoning", '
            '"confidence": "high"}'
        )

        with patch("backend.qa_chain.search", return_value=mock_chunks), \
             patch("backend.qa_chain.generate_answer", return_value=mock_llm_response):
            from backend.qa_chain import answer_question
            return answer_question(question)

    def test_fan_fainted_should_escalate(self):
        """'Fan fainted near concession stand' → escalate (medical keywords)."""
        chunks = [
            _make_doc(
                "If a person is unconscious or unresponsive, call medical team immediately. "
                "Begin CPR if trained. This is a critical emergency.",
                source="medical_emergency.md",
                severity="critical",
            ),
        ]
        result = self._mock_answer("A fan fainted near the concession stand", chunks)
        assert result["escalation"]["flag"] == "escalate"

    def test_restroom_directions_should_self_resolve(self):
        """'Where is the nearest restroom' → self_resolve (general info)."""
        chunks = [
            _make_doc(
                "Restrooms are located near every section entrance and concourse junction. "
                "Family restrooms are at Sections 105, 205, 305.",
                source="general_fan_assistance.md",
                severity="low",
            ),
        ]
        result = self._mock_answer("Where is the nearest restroom?", chunks)
        assert result["escalation"]["flag"] == "self_resolve"

    def test_suspicious_bag_should_escalate(self):
        """'Suspicious unattended bag near Gate 3' → escalate (security keywords)."""
        chunks = [
            _make_doc(
                "Do NOT touch a suspicious package. Clear the immediate area to 30 meters. "
                "Radio Security Command on Channel 2 immediately.",
                source="security_incident.md",
                severity="critical",
            ),
        ]
        result = self._mock_answer("There's a suspicious unattended bag near Gate 3", chunks)
        assert result["escalation"]["flag"] == "escalate"

    def test_lost_sunglasses_should_self_resolve(self):
        """'Someone lost their sunglasses' → self_resolve (low severity lost item)."""
        chunks = [
            _make_doc(
                "For lost personal items, gather details from the fan. "
                "Direct them to Guest Services Center at Section 115. "
                "Items are held for 30 days.",
                source="lost_and_found.md",
                severity="low",
            ),
        ]
        result = self._mock_answer("Someone lost their sunglasses", chunks)
        assert result["escalation"]["flag"] == "self_resolve"

    def test_keyword_override_forces_escalation(self):
        """Even if LLM says self_resolve, keyword match should override to escalate."""
        chunks = [
            _make_doc(
                "If a fan collapses and is unconscious, begin emergency response.",
                source="medical_emergency.md",
                severity="critical",
            ),
        ]
        # LLM says self_resolve, but keywords say escalate → final = escalate
        result = self._mock_answer(
            "A person collapsed",
            chunks,
            llm_flag="self_resolve",
        )
        assert result["escalation"]["flag"] == "escalate"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. INTEGRATION TESTS (require API key + FAISS index)
# ═══════════════════════════════════════════════════════════════════════════════

def _has_api_key():
    return bool(os.getenv("GEMINI_API_KEY"))


def _has_index():
    try:
        from backend.vectorstore import index_exists
        return index_exists()
    except Exception:
        return False


@pytest.mark.integration
@pytest.mark.skipif(
    not (_has_api_key() and _has_index()),
    reason="Requires GEMINI_API_KEY and a built FAISS index",
)
class TestRetrievalRelevance:
    """Integration tests that verify FAISS retrieval returns relevant SOP chunks."""

    def test_medical_query_retrieves_medical_sop(self):
        """Query about someone collapsing should retrieve medical_emergency.md."""
        from backend.vectorstore import search
        results = search("Someone collapsed and is not breathing", k=4)
        sources = [doc.metadata.get("source", "") for doc in results]
        assert "medical_emergency.md" in sources

    def test_lost_child_query_retrieves_child_sop(self):
        """Query about a lost child should retrieve lost_child.md."""
        from backend.vectorstore import search
        results = search("A parent is looking for their missing child", k=4)
        sources = [doc.metadata.get("source", "") for doc in results]
        assert "lost_child.md" in sources
