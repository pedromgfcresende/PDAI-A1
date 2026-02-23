"""GPT-4o email parser \u2014 extracts structured event data from client emails.

This is the AI-centered value proposition: a raw email goes in,
structured JSON comes out, ready to feed the itinerary planner.
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
  "client_name": "Company or person name",
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
- If location is not specified, default to ["Porto"]
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
    session_id = "evt-2026001"
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


def _fallback_parse(email_text: str) -> dict:
    """Simple keyword-based fallback when no API key is available."""
    text = email_text.lower()

    # Try to extract group size
    group_size = 10
    for word in text.split():
        if word.isdigit() and 2 <= int(word) <= 500:
            group_size = int(word)
            break

    # Detect preferences
    prefs = []
    if any(kw in text for kw in ["adventure", "outdoor", "jeep", "kayak", "surf", "team building"]):
        prefs.append("adventure")
    if any(kw in text for kw in ["culture", "cultural", "museum", "palace", "history", "wine"]):
        prefs.append("cultural")
    if any(kw in text for kw in ["food", "lunch", "dinner", "restaurant", "cuisine", "tasting"]):
        prefs.append("food")
    if not prefs:
        prefs = ["adventure", "cultural"]

    # Detect location
    locations = ["Porto"]
    if "sintra" in text:
        locations = ["Sintra"]
    elif "algarve" in text:
        locations = ["Algarve"]

    return _normalize({
        "client_name": "Parsed Client",
        "group_size": group_size,
        "locations": locations,
        "preferences": prefs,
        "special_requests": email_text[:200] if len(email_text) > 200 else email_text,
    })


# Sample email for demo/testing purposes
SAMPLE_EMAIL = """\
From: Sarah Mitchell <sarah.mitchell@innovatech.co.uk>
To: events@extremoambiente.pt
Subject: Corporate Team Building Event - 20 people - Porto

Hi Extremo Ambiente team,

We're planning a corporate team building event for our London office.
Here are the details:

- Company: InnovaTech Solutions
- Group size: 20 people
- Preferred date: April 15, 2026
- Location: Porto area
- Duration: Full day (approximately 8 hours)
- Budget: around \u20ac180 per person

We're interested in a mix of adventure activities and cultural experiences.
Some team members are quite adventurous but others prefer something calmer.
We'd love to include a traditional Portuguese lunch.

Special requests:
- 2 vegetarians in the group
- One person uses a wheelchair
- We'd like a group photo session

Looking forward to your proposal!

Best regards,
Sarah Mitchell
Head of People & Culture
InnovaTech Solutions
sarah.mitchell@innovatech.co.uk
+44 20 7946 0958
"""
