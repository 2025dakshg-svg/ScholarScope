"""LLM client wrapper for Gemini API using official google-genai SDK.

Handles:
- API key and model resolution strictly from .env
- JSON mode extraction and robust markdown stripping
- Prompt formatting for Analysis, Scoring (V1/V2/V3), and Report generation
- Exponential backoff retry on transient HTTP 429/503 errors (base delay 5s, max 60s)
- Honors explicit 'retry in N seconds' server hints
"""

import json
import os
import re
import time
from typing import Any, Dict, Optional
from dotenv import load_dotenv

from prompts import ANALYSIS_PROMPT, SCORING_PROMPTS, REPORT_PROMPT

# Read strictly from .env
load_dotenv(override=True)

DEFAULT_MODEL = "gemini-3.5-flash"


def get_model_name() -> str:
    """Returns the Gemini model name from .env or default Flash model."""
    return os.getenv("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def get_api_key() -> Optional[str]:
    """Retrieves the Gemini API key strictly from .env."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key or key.startswith("your_") or "placeholder" in key.lower():
        return None
    return key


def get_genai_client():
    """Initializes the official google-genai client using GEMINI_API_KEY from .env."""
    api_key = get_api_key()
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is missing or invalid in .env. Please set your Gemini API key in .env."
        )
    from google import genai
    return genai.Client(api_key=api_key)


def extract_json(raw_text: str) -> Dict[str, Any]:
    """Extracts and parses JSON from model output, stripping markdown code blocks."""
    text = raw_text.strip()
    # Strip markdown fences ```json ... ``` or ``` ... ```
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    # If surrounded by other text, locate outermost braces
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]

    return json.loads(text)


def extract_retry_hint_seconds(err_msg: str) -> Optional[float]:
    """Extracts explicit server wait hint like 'retry in 14s' or 'retry after 15.2s'."""
    pattern = r"retry\s+(?:in|after)\s+([0-9]+(?:\.[0-9]+)?)\s*s"
    match = re.search(pattern, err_msg, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def call_gemini(
    prompt: str,
    temperature: float = 0.2,
    json_mode: bool = True,
    max_retries: int = 3,
    base_delay: float = 5.0,
    max_delay: float = 60.0
) -> str:
    """
    Calls Gemini API using the official google-genai SDK.
    Implements exponential backoff: base delay ~5s, max 60s, honoring explicit retry hints.
    """
    client = get_genai_client()
    from google.genai import types

    model = get_model_name()
    config = types.GenerateContentConfig(
        temperature=temperature,
        response_mime_type="application/json" if json_mode else "text/plain"
    )

    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config
            )
            return response.text or ""
        except Exception as e:
            last_exception = e
            err_str = str(e)

            # Check if this 429 error represents DAILY quota exhaustion
            # (e.g. 'GenerateRequestsPerDayPerProjectPerModel-FreeTier', 'limit exceeded on Free Tier', 'PerDay')
            is_daily_quota = (
                "perday" in err_str.lower()
                or "per day" in err_str.lower()
                or "daily" in err_str.lower()
                or "generaterequestsperday" in err_str.lower()
            )
            if is_daily_quota and any(code in err_str for code in ["429", "RESOURCE_EXHAUSTED"]):
                print(f"[LLM] Daily quota limit exceeded. Halting immediately without retry.")
                raise RuntimeError(
                    f"Gemini API daily quota exhausted: {err_str[:160]}"
                ) from e

            # Only back off and retry for per-minute rate limits (15 RPM) or transient 503 errors
            is_transient = any(
                code in err_str for code in ["429", "503", "UNAVAILABLE", "RESOURCE_EXHAUSTED"]
            )
            if is_transient and attempt < max_retries:
                # Check for server-provided per-minute retry hint
                hint_sec = extract_retry_hint_seconds(err_str)
                if hint_sec is not None:
                    delay = min(max(hint_sec, 1.0), max_delay)
                    print(f"[LLM] Server requested retry in {hint_sec:.1f}s. Waiting {delay:.1f}s...")
                else:
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    print(f"[LLM] Transient API error (attempt {attempt + 1}/{max_retries}): {err_str[:70]}...")
                    print(f"[LLM] Exponential backoff: waiting {delay:.1f}s before retry...")

                time.sleep(delay)
                continue

            # Per-minute rate limit hit 3 times in a row
            if any(k in err_str.lower() for k in ["minute", "rpm", "429", "resource_exhausted"]):
                raise RuntimeError(
                    "Gemini API per-minute rate limit exceeded 3 times in a row. Halting execution."
                ) from e

            # Non-transient or retries exhausted
            raise last_exception

    return ""


def generate_topic_analysis(topic: str) -> Dict[str, Any]:
    """Stage 1: Analyzes topic domain, refined question, and researchability."""
    prompt = f"{ANALYSIS_PROMPT}\n\n<topic>\n{topic.strip()}\n</topic>"
    raw_output = call_gemini(prompt, temperature=0.2, json_mode=True)
    return extract_json(raw_output)


def generate_topic_scoring(
    topic: str,
    analysis: Dict[str, Any],
    version: str = "V3",
    correction_hint: Optional[str] = None
) -> Dict[str, Any]:
    """Stage 2: Scores topic on 4 criteria using chosen prompt version (V1, V2, or V3)."""
    system_prompt = SCORING_PROMPTS.get(version, SCORING_PROMPTS["V3"])

    context_block = f"Topic Domain: {analysis.get('domain', 'General')}\nRefined Question: {analysis.get('research_question', topic)}"
    prompt = f"{system_prompt}\n\nContext Analysis:\n{context_block}\n\n<topic>\n{topic.strip()}\n</topic>"

    if correction_hint:
        prompt += f"\n\nCRITICAL FIX: A previous attempt failed rubric validation with these errors:\n{correction_hint}\nPlease fix all issues and return valid JSON."

    raw_output = call_gemini(prompt, temperature=0.2, json_mode=True)
    return extract_json(raw_output)


def generate_report(topic: str, scoring: Dict[str, Any]) -> str:
    """Stage 4: Synthesizes final Markdown feasibility report."""
    scoring_str = json.dumps(scoring, indent=2)
    prompt = f"{REPORT_PROMPT}\n\nTopic:\n{topic.strip()}\n\nValidated Scores JSON:\n{scoring_str}"

    raw_output = call_gemini(prompt, temperature=0.3, json_mode=False)
    return raw_output.strip()
