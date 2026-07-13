"""
llm.py – Groq LLM client wrapper.
Provides a thin interface over the groq SDK for fast text generation.
"""
from functools import lru_cache
from typing import Optional
import json

from groq import Groq

from backend.config import GROQ_API_KEY, GROQ_MODEL


@lru_cache(maxsize=1)
def _get_client() -> Groq:
    """Instantiate and cache the Groq client."""
    return Groq(api_key=GROQ_API_KEY)


def generate_answer(
    prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 2048,
    response_mime_type: Optional[str] = None,
    response_schema: Optional[dict] = None,
) -> str:
    """
    Generate a text response from Groq.

    Args:
        prompt: The full prompt string to send.
        temperature: Sampling temperature (0.0–1.0).
        max_tokens: Maximum output tokens.
        response_mime_type: Optional MIME type for structured output (e.g. "application/json").
        response_schema: Optional JSON schema for structured output.

    Returns:
        The generated text string.
    """
    client = _get_client()

    messages = [{"role": "user", "content": prompt}]
    response_format = None

    if response_mime_type == "application/json":
        response_format = {"type": "json_object"}
        if response_schema:
            messages.insert(0, {
                "role": "system",
                "content": f"You must respond ONLY with valid JSON that strictly matches this schema:\n{json.dumps(response_schema)}"
            })

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format=response_format
    )

    return response.choices[0].message.content
