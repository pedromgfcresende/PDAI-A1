"""Workflow phase progress indicator."""

from __future__ import annotations

import streamlit as st

_PHASES = ["Email Parsed", "Planning", "Review", "Finalized"]
_PHASE_ORDER = {p: i for i, p in enumerate(_PHASES)}


def render_phase_bar(phase: str) -> None:
    """Render the four-step phase progress bar.

    Args:
        phase: current phase slug \u2014 one of 'parsed', 'planning', 'review', 'finalized'
    """
    slug_to_label = {
        "parsed": "Email Parsed",
        "planning": "Planning",
        "review": "Review",
        "finalized": "Finalized",
    }
    active_label = slug_to_label.get(phase, "")
    active_idx = _PHASE_ORDER.get(active_label, -1)

    segments = []
    for i, p in enumerate(_PHASES):
        if i < active_idx:
            css = "done"
        elif i == active_idx:
            css = "active"
        else:
            css = ""
        segments.append(f'<div class="phase-seg {css}">{p}</div>')

    st.markdown(
        f'<div class="phase-bar">{"".join(segments)}</div>',
        unsafe_allow_html=True,
    )
