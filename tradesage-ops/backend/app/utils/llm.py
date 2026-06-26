"""
TradeSage Ops — Gemini LLM Integration Utility.

Uses google-genai SDK to call Gemini 2.5 Flash for agent reasoning.
Falls back to intelligent mock responses when GEMINI_API_KEY is not set,
so the demo always works.

Follows the same pattern as agent-starter-pack's Vertex AI / Gemini integration.
"""

import os
import logging
import json
from typing import Optional

logger = logging.getLogger(__name__)


def _get_client():
    """Get a google-genai client if API key is available."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except ImportError:
        logger.warning("google-genai not installed. Using mock responses.")
        return None
    except Exception as e:
        logger.warning(f"Failed to create Gemini client: {e}")
        return None


def call_gemini(prompt: str, fallback: str) -> str:
    """
    Call Gemini for reasoning. If the API is unavailable, return the fallback.

    This is the core LLM function used by every specialist agent.
    In production with a GEMINI_API_KEY, it sends the prompt to Gemini 2.5 Flash.
    Without a key, it returns the pre-computed fallback so the demo still works.

    Args:
        prompt: The analysis prompt to send to Gemini
        fallback: The mock response to use if Gemini is unavailable

    Returns:
        The LLM's response text, or the fallback string
    """
    client = _get_client()
    if client is None:
        logger.info("No Gemini API key — using mock response")
        return fallback

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        return fallback


def call_gemini_json(prompt: str, fallback: dict) -> dict:
    """
    Call Gemini and parse the response as JSON.
    Falls back to the provided dict if parsing fails or API is unavailable.
    """
    client = _get_client()
    if client is None:
        return fallback

    try:
        full_prompt = prompt + "\n\nRespond with valid JSON only. No markdown, no explanation."
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt,
        )
        text = response.text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
        return json.loads(text)
    except Exception as e:
        logger.error(f"Gemini JSON call failed: {e}")
        return fallback
