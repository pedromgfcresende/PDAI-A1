"""Client metrics KPI strip."""

from __future__ import annotations

import streamlit as st

from data.engine import format_date_display


def render_metrics_bar(
    client: dict,
    per_pp: float,
    final_total: float,
    budget_ok: bool,
) -> None:
    """Render the horizontal metrics row and over-budget warning if needed."""
    budget = client.get("budget_per_person")
    group = client["group_size"]
    location = client["locations"][0]

    if budget is not None:
        pp_color = "var(--orange)" if budget_ok else "var(--red)"
        budget_label = f"Per Person (€{budget} cap)"
    else:
        pp_color = "var(--orange)"
        budget_label = "Per Person"

    st.markdown(
        f"""
        <div class="metric-row">
          <div class="metric-badge"><span class="val">{client['client_name']}</span><span class="lbl">Client</span></div>
          <div class="metric-badge"><span class="val">{format_date_display(client.get('date', ''))}</span><span class="lbl">Date</span></div>
          <div class="metric-badge"><span class="val">{group}</span><span class="lbl">People</span></div>
          <div class="metric-badge"><span class="val">{location}</span><span class="lbl">Location</span></div>
          <div class="metric-badge"><span class="val" style="color:{pp_color}">€{per_pp:,.0f}</span><span class="lbl">{budget_label}</span></div>
          <div class="metric-badge"><span class="val" style="color:var(--orange)">€{final_total:,.0f}</span><span class="lbl">Total</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if budget is not None and not budget_ok:
        st.markdown(
            f'<div class="warn-box">⚠️ Over budget by €{per_pp - budget:.0f}/person</div>',
            unsafe_allow_html=True,
        )
