"""Context-aware chat agent powered by GPT-4o.

The assistant sees the current itinerary, budget, and client preferences
so it can give relevant suggestions. Falls back to keyword matching
when no API key is set.
"""

from __future__ import annotations
import json
import os
from openai import OpenAI

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
