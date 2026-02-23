"""Context-aware chat agent powered by GPT-4o.

The assistant sees the current itinerary, budget, and client preferences
so it can give relevant suggestions. Falls back to keyword matching
when no API key is set.
"""

from __future__ import annotations

import json
import os

from openai import OpenAI

# Simple keyword \u2192 response map used as fallback
_BOT_RESPONSES: dict[str, str] = {
    "lunch": "I'd suggest adding a lunch break between 12:00\u201314:00. Traditional Portuguese restaurants near your route offer great group menus at \u20ac20\u201330/person.",
    "wine": "A wine tasting experience would be a great addition! Porto wine cellars offer group tastings at \u20ac25/person including a guided tour.",
    "transport": "Transport can be arranged from major pickup points. Extremo HQ (Cascais) is free, Lisbon Centro is \u20ac80, or Cascais Hotels at \u20ac30.",
    "photo": "Professional photography is available as an add-on for \u20ac200 flat fee. Check the Pricing tab to enable it.",
    "budget": "You can check the current per-person cost in the metrics bar above. Use the Pricing tab for manual overrides on any activity.",
    "route": "I can re-optimize your route using OR-Tools. Click the 'Re-optimize Route' button below the itinerary editor.",
    "hello": "Hello! I'm your EA planning assistant. I can help you adjust the itinerary, suggest activities, or answer questions about pricing.",
    "help": "I can help with: adjusting activities, suggesting alternatives, route optimization, budget planning, and sub-group management. What would you like to do?",
    "vegetarian": "For vegetarian guests, I recommend selecting restaurants with farm-to-table menus. Most venues in our catalog offer vegetarian options \u2014 just mention it in the Notes column.",
    "weather": "Portugal generally has great weather for outdoor activities. March\u2013May and September\u2013October are ideal. We always have indoor backup options.",
    "discount": "Groups larger than 10 people automatically receive a 5% discount on the total cost.",
}

_SYSTEM_PROMPT = """\
You are the AI planning assistant for Extremo Ambiente, a corporate adventure tourism company in Portugal.
You help staff plan corporate events by suggesting activities, adjusting itineraries, and answering questions.

You have access to the current event context below. Use it to give specific, relevant advice.
Keep responses concise (2-3 sentences max). Be friendly and professional.
Always mention specific activities, prices, or times when relevant.

Current Event Context:
{context}
"""


def get_bot_response(
    message: str,
    context: dict | None = None,
) -> str:
    """Return a bot reply for the given user message.

    Args:
        message: The user's chat message.
        context: Optional dict with itinerary, client, and budget info
                 for context-aware responses.

    Returns:
        AI-generated response string.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return _gpt4o_response(message, context, api_key)
    return _keyword_response(message)


def _keyword_response(message: str) -> str:
    """Fallback: match keywords in user message."""
    ml = message.lower()
    for kw, resp in _BOT_RESPONSES.items():
        if kw in ml:
            return resp
    return "Noted! I've logged your request. You can adjust activities in the itinerary editor above, or ask me about pricing, routes, or alternatives."


def _gpt4o_response(
    message: str,
    context: dict | None,
    api_key: str,
) -> str:
    """GPT-4o powered response with full event context."""
    context_str = json.dumps(context, indent=2, default=str) if context else "No event loaded yet."
    system = _SYSTEM_PROMPT.format(context=context_str)

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": message},
        ],
        temperature=0.7,
        max_tokens=200,
    )
    return response.choices[0].message.content.strip()
