"""AI assistant chat panel powered by GPT-4o."""

from __future__ import annotations

import streamlit as st

from ai.chat_agent import get_bot_response


def render_chat_panel(
    chat_log: list[dict],
    key_suffix: str = "",
    subgroup: str | None = None,
    context: dict | None = None,
) -> list[dict]:
    """Render the chat window and input field.

    Args:
        chat_log:    Shared conversation history (mutated in place).
        key_suffix:  Appended to widget keys to allow multiple instances
                     (e.g. one per sub-group tab) on the same page.
        subgroup:    Optional sub-group context shown in the panel title
                     so the AI can be primed for that group.
        context:     Optional dict with itinerary/client info for GPT-4o context.

    Returns the updated chat_log.
    """
    title = "AI Assistant"
    if subgroup:
        title = f"AI Assistant \u00b7 {subgroup}"
    st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)

    bubbles = "".join(
        f"<div class='bubble-bot'>\U0001f916 {msg['text']}</div>"
        if msg["role"] == "bot"
        else f"<div class='bubble-user'>\U0001f464 {msg['text']}</div>"
        for msg in chat_log
    )
    st.markdown(f"<div class='chat-window'>{bubbles}</div>", unsafe_allow_html=True)

    user_msg = st.text_input(
        "Message",
        key=f"chat_input{key_suffix}",
        placeholder="e.g. 'Add a lunch break at 13:00'",
        label_visibility="collapsed",
    )
    if st.button("Send", use_container_width=True, key=f"chat_send{key_suffix}"):
        if user_msg.strip():
            prefix = f"[Sub-group: {subgroup}] " if subgroup else ""
            chat_log.append({"role": "user", "text": user_msg})
            reply = get_bot_response(prefix + user_msg, context=context)
            chat_log.append({"role": "bot", "text": reply})
            st.session_state.chat_history = chat_log
            st.rerun()

    return chat_log
