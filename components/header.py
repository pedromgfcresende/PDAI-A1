"""EA header band with logo and session badge."""

from __future__ import annotations

import streamlit as st


def render_header(logo_b64: str | None, session_id: str | None = None) -> None:
    """Render the top header band with logo, brand name and session badge."""
    badge_html = (
        f"<div class='ea-session-badge'>SESSION {session_id}</div>"
        if session_id
        else ""
    )

    if logo_b64:
        st.markdown(
            f'''<div class="ea-header">
              <img src="data:image/png;base64,{logo_b64}"
                   style="height:64px;width:64px;object-fit:contain;border-radius:6px">
              <div>
                <div class="ea-logo">EXTREMO<span>AMBIENTE</span></div>
                <div class="ea-tagline">Corporate Event Automation</div>
              </div>
              <div style="flex:1"></div>
              {badge_html}
            </div>''',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""<div class="ea-header">
              <div>
                <div class="ea-logo">EXTREMO<span>AMBIENTE</span></div>
                <div class="ea-tagline">Corporate Event Automation</div>
              </div>
              {badge_html}
            </div>""",
            unsafe_allow_html=True,
        )
