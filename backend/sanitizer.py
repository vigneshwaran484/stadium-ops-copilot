"""
sanitizer.py – Prompt-injection guard for user input.
Strips or escapes instruction-like patterns before including user text
in the LLM prompt. Provides a basic defence layer against prompt injection.
"""
import re
from typing import Tuple

# Patterns that indicate prompt-injection attempts
_INJECTION_PATTERNS = [
    # Direct instruction overrides
    re.compile(r"ignore\s+(all\s+)?(previous|above|prior|earlier)\s+(instructions|prompts|context|rules)", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|above|prior|earlier)\s+(instructions|prompts|context|rules)", re.IGNORECASE),
    re.compile(r"forget\s+(all\s+)?(previous|above|prior|earlier)\s+(instructions|prompts|context|rules)", re.IGNORECASE),

    # Role reassignment
    re.compile(r"you\s+are\s+now\s+", re.IGNORECASE),
    re.compile(r"act\s+as\s+(if\s+you\s+are|a|an)\s+", re.IGNORECASE),
    re.compile(r"pretend\s+(to\s+be|you\s+are)\s+", re.IGNORECASE),
    re.compile(r"from\s+now\s+on\s+you\s+", re.IGNORECASE),

    # System/assistant prompt injection
    re.compile(r"<\|?(system|assistant|user|im_start|im_end)\|?>", re.IGNORECASE),
    re.compile(r"\[INST\]", re.IGNORECASE),
    re.compile(r"\[/INST\]", re.IGNORECASE),
    re.compile(r"<<\s*SYS\s*>>", re.IGNORECASE),

    # Output manipulation
    re.compile(r"output\s+(only|just|exactly)\s+", re.IGNORECASE),
    re.compile(r"respond\s+with\s+(only|just|exactly)\s+", re.IGNORECASE),

    # Instruction injection within fenced blocks
    re.compile(r"```\s*(system|instruction|prompt)", re.IGNORECASE),
]


def sanitize_input(user_input: str) -> Tuple[str, bool]:
    """
    Sanitize user input by removing prompt-injection patterns.

    Args:
        user_input: Raw text from the user.

    Returns:
        Tuple of (cleaned_text, was_sanitized).
        was_sanitized is True if any injection patterns were found and removed.
    """
    if not user_input:
        return "", False

    cleaned = user_input
    was_sanitized = False

    for pattern in _INJECTION_PATTERNS:
        if pattern.search(cleaned):
            cleaned = pattern.sub("[FILTERED]", cleaned)
            was_sanitized = True

    # Strip any remaining control characters (except newlines and tabs)
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", cleaned)

    return cleaned.strip(), was_sanitized
