"""A/B/C proposal selector tabs and new-proposal button.

Each proposal is fully independent: own itinerary, activities, price_overrides, and tour_type.
"""

from __future__ import annotations

from typing import Callable

import streamlit as st


def _migrate_proposal(prop: dict) -> dict:
    """Ensure older proposal dicts have the new fields."""
    if "price_overrides" not in prop:
        prop["price_overrides"] = {}
    if "tour_type" not in prop:
        prop["tour_type"] = "walking"
    if "activities" not in prop:
        prop["activities"] = []
    if "start_time" not in prop:
        prop["start_time"] = "09:30"
    # Clean up legacy keys
    prop.pop("subgroups", None)
    prop.get("price_overrides", {}).pop("__tour_transport__", None)
    return prop


def render_proposal_selector(
    proposals: dict,
    get_itinerary_fn: Callable[[dict], list],
    client: dict,
) -> tuple[str, dict, list]:
    """Render proposal dropdown + rename input + new-proposal button.

    Returns:
        active_prop      — selected proposal key (e.g. 'A')
        current_proposal — proposal dict for the active key
        itin             — itinerary list for the active proposal
    """
    # Migrate all proposals on first load
    for key in proposals:
        _migrate_proposal(proposals[key])

    col_prop, col_name, col_new = st.columns([3, 3, 1])

    with col_prop:
        prop_options = [f"{k}: {v['name']}" for k, v in proposals.items()]
        selected = st.selectbox(
            "Proposal",
            prop_options,
            key="prop_sel",
            label_visibility="collapsed",
        )
        active_prop = selected.split(":")[0]
        st.session_state.active_proposal = active_prop

    with col_name:
        current_name = proposals[active_prop]["name"]
        new_name = st.text_input(
            "Proposal Name",
            value=current_name,
            key=f"prop_name_{active_prop}",
            label_visibility="collapsed",
            placeholder="Rename proposal...",
        )
        if new_name != current_name:
            proposals[active_prop]["name"] = new_name
            st.session_state.proposals = proposals

    with col_new:
        if st.button("+ New Proposal", use_container_width=True):
            next_letter = chr(ord(max(proposals.keys())) + 1) if proposals else "A"
            proposals[next_letter] = {
                "name": f"Option {next_letter}",
                "itinerary": get_itinerary_fn(client),
                "activities": [],
                "price_overrides": {},
                "tour_type": "walking",
                "start_time": "09:30",
            }
            st.session_state.proposals = proposals
            st.session_state.active_proposal = next_letter
            st.rerun()

    current_proposal = proposals[active_prop]
    itin = current_proposal["itinerary"]
    return active_prop, current_proposal, itin


def render_proposal_indicator(proposals: dict, active_prop: str) -> None:
    """Show a read-only badge indicating the active proposal (no rename, no create)."""
    name = proposals.get(active_prop, {}).get("name", active_prop)
    st.markdown(
        f"<div style='font-size:0.82rem;color:var(--muted);margin-bottom:0.5rem'>"
        f"Proposal <strong style='color:var(--orange)'>{active_prop}: {name}</strong></div>",
        unsafe_allow_html=True,
    )
