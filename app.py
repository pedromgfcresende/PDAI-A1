"""Extremo Ambiente — Event Automation Dashboard (Assignment Prototype).

AI-centered corporate event quoting system. GPT-4o parses client emails,
suggests itineraries, and assists staff via a context-aware chat assistant.

Run:
    uv run streamlit run app.py
"""

import base64
import json
import os
from copy import deepcopy

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Streamlit Cloud secrets → env vars bridge ────────────────────────────────
# On Streamlit Community Cloud, secrets are in st.secrets, not .env.
# Copy them into os.environ so all modules that use os.getenv() still work.
try:
    for key, value in st.secrets.items():
        if isinstance(value, str):
            os.environ.setdefault(key, value)
except FileNotFoundError:
    pass  # No secrets file (local dev uses .env instead)

# ── Page config (must be first Streamlit call) ───────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_FAVICON = os.path.join(_HERE, "assets", "favicon.png")

st.set_page_config(
    page_title="Extremo Ambiente | Event Planner",
    page_icon=_FAVICON if os.path.exists(_FAVICON) else "🟠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ──────────────────────────────────────────────────────────────────────
def _load_css(filename: str) -> None:
    path = os.path.join(_HERE, filename)
    try:
        with open(path, encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"⚠️  {filename} not found.")

_load_css("style.css")
st.markdown("""
<style>
  div[data-testid="stTab"][aria-selected="true"] { color: var(--orange-light) !important; }
  button[role="tab"][aria-selected="true"]       { color: var(--orange-light) !important; }
</style>
""", unsafe_allow_html=True)

# ── Image helpers ────────────────────────────────────────────────────────────
def _b64(path: str) -> str | None:
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

_logo_b64    = _b64(os.path.join(_HERE, "assets", "logo.png"))
_sidebar_b64 = _b64(os.path.join(_HERE, "assets", "logo_sidebar.png"))

# ── Imports ──────────────────────────────────────────────────────────────────
from components.header import render_header
from components.metrics_bar import render_metrics_bar
from components.proposal_selector import render_proposal_indicator, render_proposal_selector
from components.itinerary_editor import render_itinerary_editor
from components.map_view import render_map
from components.chat_panel import render_chat_panel
from components.pricing_panel import render_pricing_panel
from components.activities_editor import render_activities_editor
from data.engine import compute_totals, format_date_display, get_itinerary_for_client, parse_date_input
from ai.email_parser import parse_email, SAMPLE_EMAIL

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    if _sidebar_b64:
        st.markdown(
            f"<div style='text-align:center;padding:0.5rem 0 1rem'>"
            f"<img src='data:image/png;base64,{_sidebar_b64}' "
            f"style='width:80px;height:80px;object-fit:contain;border-radius:8px'></div>",
            unsafe_allow_html=True,
        )

    if "client" in st.session_state:
        st.markdown("<div class='section-title'>Active Client</div>", unsafe_allow_html=True)
        c = st.session_state.client
        st.markdown(f"**{c['client_name']}**")
        st.markdown(f"📍 {c['locations'][0]}")
        st.markdown(f"👥 {c['group_size']} · {c['duration_hours']}h")

    st.divider()
    has_key = bool(os.getenv("OPENAI_API_KEY"))
    ai_color = "var(--green)" if has_key else "var(--amber)"
    ai_label = "GPT-4o Active" if has_key else "Fallback Mode"
    st.markdown(
        f"<div style='font-size:0.75rem;color:var(--muted)'>"
        f"AI Status: <span style='color:{ai_color}'>"
        f"{ai_label}</span></div>",
        unsafe_allow_html=True,
    )

    has_gmaps = bool(os.getenv("GOOGLE_MAPS_API_KEY"))
    gmaps_color = "var(--green)" if has_gmaps else "var(--amber)"
    gmaps_label = "Google Maps Active" if has_gmaps else "Catalog-only Mode"
    st.markdown(
        f"<div style='font-size:0.75rem;color:var(--muted)'>"
        f"Maps: <span style='color:{gmaps_color}'>"
        f"{gmaps_label}</span></div>",
        unsafe_allow_html=True,
    )

# ── Header ───────────────────────────────────────────────────────────────────
session_id = st.session_state.get("client", {}).get("session_id") if "client" in st.session_state else None
render_header(logo_b64=_logo_b64, session_id=session_id)

# ══════════════════════════════════════════════════════════════════════════════
# Tabs — EMAIL PARSER is the first tab (AI showcase)
# ══════════════════════════════════════════════════════════════════════════════
tab_email, tab_plan, tab_price, tab_final = st.tabs(
    ["EMAIL PARSER", "PLANNER", "PRICING", "FINALIZE"]
)

# ── Tab 0 — Email Parser (AI-powered intake) ─────────────────────────────────
with tab_email:
    st.markdown("<div class='section-title'>AI Email Parser</div>", unsafe_allow_html=True)

    col_input, col_output = st.columns([1, 1], gap="large")

    with col_input:
        st.markdown("**Client Email**")
        email_text = st.text_area(
            "Paste email",
            value=st.session_state.get("email_draft", ""),
            height=350,
            key="email_input",
            label_visibility="collapsed",
            placeholder="Paste the client's email here...",
        )

        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            parse_clicked = st.button(
                "🤖 Parse with AI",
                use_container_width=True,
                type="primary",
            )
        with btn_col2:
            if st.button("Load Sample Email", use_container_width=True):
                st.session_state.email_draft = SAMPLE_EMAIL
                st.rerun()

    with col_output:
        st.markdown("**Extracted Data**")

        if parse_clicked and email_text.strip():
            with st.spinner("GPT-4o is analyzing the email..."):
                try:
                    parsed = parse_email(email_text)
                    st.session_state.parsed_email = parsed
                    st.rerun()
                except Exception as e:
                    st.error(f"Parsing failed: {e}")

        if "parsed_email" in st.session_state:
            parsed = st.session_state.parsed_email

            # ── Editable form fields ──────────────────────────────────
            with st.form("parsed_email_form"):
                edit_name = st.text_input("Client Name", value=parsed.get("client_name", ""))
                edit_email = st.text_input("Email", value=parsed.get("email", ""))
                fc1, fc2 = st.columns(2)
                with fc1:
                    edit_group = st.number_input("Group Size", value=int(parsed.get("group_size", 10)), min_value=1)
                with fc2:
                    edit_date = st.text_input("Date", value=format_date_display(parsed.get("date", "")), help="dd/mm/yyyy")
                edit_location = st.text_input("Location", value=parsed.get("locations", [""])[0] if parsed.get("locations") else "")
                fc3, fc4 = st.columns(2)
                with fc3:
                    edit_duration = st.number_input("Duration (hours)", value=int(parsed.get("duration_hours", 6)), min_value=1)
                with fc4:
                    raw_budget = parsed.get("budget_per_person")
                    edit_budget = st.number_input(
                        "Budget per Person (€)",
                        value=int(raw_budget) if raw_budget else 0,
                        min_value=0,
                        help="Set to 0 for no budget cap",
                    )
                edit_prefs = st.text_input(
                    "Preferences",
                    value=", ".join(parsed.get("preferences", [])),
                    help="Comma-separated: adventure, cultural, food",
                )
                edit_special = st.text_area("Special Requests", value=parsed.get("special_requests", ""), height=80)

                start_planning = st.form_submit_button("Start Planning", type="primary", use_container_width=True)

            if start_planning:
                data = {
                    "client_name": edit_name,
                    "email": edit_email,
                    "group_size": edit_group,
                    "date": parse_date_input(edit_date),
                    "locations": [edit_location] if edit_location else ["Porto"],
                    "duration_hours": edit_duration,
                    "preferences": [p.strip() for p in edit_prefs.split(",") if p.strip()],
                    "budget_per_person": edit_budget if edit_budget > 0 else None,
                    "special_requests": edit_special,
                    "session_id": "evt-2026001",
                }
                st.session_state.client = data
                st.session_state.proposals = {
                    "A": {
                        "name": "Adventure Mix",
                        "itinerary": [],
                        "activities": [],
                        "price_overrides": {},
                        "tour_type": "walking",
                        "start_time": "09:30",
                    }
                }
                st.session_state.active_proposal = "A"
                st.session_state.chat_history = [
                    {"role": "bot", "text": f"Loaded {data['client_name']} from email! Ready to plan their event."}
                ]
                st.rerun()
        else:
            st.markdown(
                "<div style='text-align:center;padding:3rem 0;color:var(--muted)'>"
                "<div style='font-size:2.5rem;opacity:0.3'>📧</div>"
                "<div style='font-size:0.85rem;margin-top:0.5rem'>"
                "Parsed data will appear here</div></div>",
                unsafe_allow_html=True,
            )

# ── Guard for remaining tabs — need active session ───────────────────────────
if "client" not in st.session_state:
    with tab_plan:
        st.markdown("""
        <div style="text-align:center;padding:5rem 0;color:var(--muted)">
          <div style="font-size:3.5rem">🏔️</div>
          <div style="font-family:'Montserrat',sans-serif;font-size:1.4rem;
                      color:var(--white);text-transform:uppercase">No Active Session</div>
          <div style="font-size:0.85rem;margin-top:0.5rem">
            Use the Email Parser tab to load a client</div>
        </div>
        """, unsafe_allow_html=True)
    with tab_price:
        st.info("Load a client first to see pricing.")
    with tab_final:
        st.info("Load a client first to finalize.")
    st.stop()

# ── Session data ─────────────────────────────────────────────────────────────
client       = st.session_state.client
proposals    = st.session_state.get("proposals", {})
chat_log     = st.session_state.get("chat_history", [])
group        = client["group_size"]
location     = client["locations"][0]

# ── Extract active proposal data (no UI — used by all tabs) ──────────────────
active_prop = st.session_state.get("active_proposal", "A")
if active_prop not in proposals:
    active_prop = next(iter(proposals))
    st.session_state.active_proposal = active_prop
current_proposal = proposals[active_prop]
itin = current_proposal.get("itinerary", [])
activities = current_proposal.get("activities", [])
price_overrides = current_proposal.get("price_overrides", {})
tour_type = current_proposal.get("tour_type", "walking")

# ── Build coords_map for travel durations ────────────────────────────────────
coords_map: dict[str, tuple[float, float]] = {}
for item in itin:
    name = item.get("activity", "")
    if "user_lat" in item:
        coords_map[name] = (item["user_lat"], item["user_lng"])

travel_mode = "WALK" if tour_type == "walking" else "DRIVE"

# ── Financial aggregates ─────────────────────────────────────────────────────
totals = compute_totals(
    activities=activities,
    group_size=group,
    price_overrides=price_overrides,
    budget_per_person=client.get("budget_per_person"),
)

# ── Metrics bar ──────────────────────────────────────────────────────────────
render_metrics_bar(
    client=client,
    per_pp=totals["per_pp"],
    final_total=totals["final_total"],
    budget_ok=totals["budget_ok"],
)

# ── Tab 1 — Planner ─────────────────────────────────────────────────────────
with tab_plan:
    # ── Proposal selector (only on Planner tab) ──────────────────────────
    active_prop, current_proposal, itin = render_proposal_selector(
        proposals, get_itinerary_for_client, client
    )
    activities = current_proposal.get("activities", [])
    price_overrides = current_proposal.get("price_overrides", {})
    tour_type = current_proposal.get("tour_type", "walking")
    travel_mode = "WALK" if tour_type == "walking" else "DRIVE"

    # ── Route editor (map waypoints) ─────────────────────────────────────
    itin = render_itinerary_editor(
        itin=itin,
        active_prop=active_prop,
        proposals=proposals,
        location=location,
        tour_type=tour_type,
        coords_map=coords_map,
    )

    st.markdown("---")

    # ── Activities editor (billable services) ────────────────────────────
    activities, tour_type = render_activities_editor(
        activities=activities,
        active_prop=active_prop,
        proposals=proposals,
        group_size=group,
        tour_type=tour_type,
        duration_hours=client["duration_hours"],
        location=location,
    )

    st.markdown("---")

    # ── Recalculate totals with latest activities ────────────────────────
    totals = compute_totals(
        activities=activities,
        group_size=group,
        price_overrides=price_overrides,
        budget_per_person=client.get("budget_per_person"),
    )

    # ── Build context for AI chat ────────────────────────────────────────
    chat_context = {
        "client": client["client_name"],
        "group_size": group,
        "location": location,
        "budget_per_person": client.get("budget_per_person"),
        "total_cost": totals["final_total"],
        "per_person_cost": totals["per_pp"],
        "budget_ok": totals["budget_ok"],
        "tour_type": tour_type,
        "itinerary": [
            {"time": a.get("time", ""), "activity": a.get("activity", ""), "type": a.get("type", "")}
            for a in itin
        ],
        "activities": [
            {"name": a.get("name", ""), "total": a.get("total", 0)}
            for a in activities
        ],
    }

    # ── Map + Chat ───────────────────────────────────────────────────────
    col_map, col_chat = st.columns([3, 2], gap="large")
    with col_map:
        render_map(itin=itin, location=location, travel_mode=travel_mode)
    with col_chat:
        chat_log = render_chat_panel(
            chat_log=chat_log,
            context=chat_context,
        )

# ── Tab 2 — Pricing ─────────────────────────────────────────────────────────
with tab_price:
    render_proposal_indicator(proposals, active_prop)

    # Re-read proposal data for this tab
    _p_prop = proposals[active_prop]
    _p_activities = _p_prop.get("activities", [])
    _p_overrides = _p_prop.get("price_overrides", {})

    totals = compute_totals(
        activities=_p_activities,
        group_size=group,
        price_overrides=_p_overrides,
        budget_per_person=client.get("budget_per_person"),
    )

    price_overrides = render_pricing_panel(
        activities=_p_activities,
        group_size=group,
        price_overrides=_p_overrides,
        grand_total=totals["grand_total"],
        discount=totals["discount"],
        final_total=totals["final_total"],
        per_pp=totals["per_pp"],
    )

    # Write overrides back to proposal
    proposals[active_prop]["price_overrides"] = price_overrides
    st.session_state.proposals = proposals

# ── Tab 3 — Finalize ────────────────────────────────────────────────────────
with tab_final:
    render_proposal_indicator(proposals, active_prop)
    st.markdown("<div class='section-title'>Generate Proposal</div>", unsafe_allow_html=True)

    _f_prop = proposals[active_prop]
    _f_activities = _f_prop.get("activities", [])
    _f_overrides = _f_prop.get("price_overrides", {})

    _f_totals = compute_totals(
        activities=_f_activities,
        group_size=group,
        price_overrides=_f_overrides,
        budget_per_person=client.get("budget_per_person"),
    )

    # Summary before finalize
    st.markdown(
        f"""
        <div class='ea-card'>
          <div class='price-row'><span>Client</span><span style='color:var(--white);font-weight:600'>{client['client_name']}</span></div>
          <div class='price-row'><span>Event Date</span><span style='color:var(--white)'>{format_date_display(client['date'])}</span></div>
          <div class='price-row'><span>Group Size</span><span style='color:var(--white)'>{group} people</span></div>
          <div class='price-row'><span>Location</span><span style='color:var(--white)'>{location}</span></div>
          <div class='price-row total'><span>Final Cost</span><span class='price-val'>€{_f_totals["final_total"]:,.2f}</span></div>
          <div class='price-row'><span>Per Person</span><span class='price-val'>€{_f_totals["per_pp"]:,.2f}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    if st.button(
        "GENERATE PDF PROPOSAL",
        use_container_width=True,
        type="primary",
    ):
        with st.spinner("Generating PDF proposal..."):
            import time
            time.sleep(2)
