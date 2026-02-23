"""
GPT-4o email parser extracts structured event data from client emails.
"""

from __future__ import annotations
import json
import os
from openai import OpenAI

_SYSTEM_PROMPT = """\
You are an expert assistant for Extremo Ambiente, a corporate adventure tourism company in Portugal.

Your task is to extract structured event information from a client email.
Return ONLY valid JSON with these fields (use null for missing values):

{
  "client_name": "Company name",
  "email": "client email address",
  "group_size": <integer>,
  "date": "YYYY-MM-DD",
  "locations": ["list of locations mentioned"],
  "duration_hours": <integer>,
  "preferences": ["adventure", "cultural", "food"],
  "budget_per_person": <float or null>,
  "special_requests": "any special notes"
}

Rules:
- Infer preferences from context (e.g. "team building" -> adventure, "wine tasting" -> cultural+food)
- If location is not specified, default to ["Sintra"]
- If duration is not specified, default to 6
- If budget is not mentioned, set budget_per_person to null
- Extract the email address from the signature or From field if present
- Return ONLY the JSON object, no markdown, no explanation
"""


def parse_email(email_text: str) -> dict:
    """Parse a client email into structured event data using GPT-4o.

    Args:
        email_text: Raw email body text from the client.

    Returns:
        Dict with extracted fields matching DEMO_CLIENTS format,
        plus a generated session_id.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _fallback_parse(email_text)

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": email_text},
        ],
        temperature=0.1, 
        max_tokens=500,
    )

    raw = response.choices[0].message.content.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

    parsed = json.loads(raw)
    return _normalize(parsed)


def _normalize(parsed: dict) -> dict:
    """Ensure all required fields exist and add a session_id."""
    session_id = "evt-2026001" #for now session_id is static, but in production this would be generated uniquely
    return {
        "client_name": parsed.get("client_name") or "Unknown Client",
        "email": parsed.get("email") or "",
        "group_size": int(parsed.get("group_size") or 10),
        "date": parsed.get("date") or "2026-04-01",
        "locations": parsed.get("locations") or ["Porto"],
        "duration_hours": int(parsed.get("duration_hours") or 6),
        "preferences": parsed.get("preferences") or ["adventure"],
        "budget_per_person": float(parsed["budget_per_person"]) if parsed.get("budget_per_person") is not None else None,
        "special_requests": parsed.get("special_requests") or "",
        "session_id": session_id,
    }