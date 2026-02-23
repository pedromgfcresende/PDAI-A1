"""Itinerary editor — AgGrid with drag-and-drop reordering + per-row delete.

The itinerary contains route stops (waypoints) that appear on the map.
Billable activities are managed separately in the Activities Editor.
"""

from __future__ import annotations

import datetime

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, DataReturnMode, GridOptionsBuilder, GridUpdateMode
from streamlit_searchbox import st_searchbox

from data.engine import rebuild_times
from services.geocoding import get_place_coordinates, search_places

# Column widths
_COL_W = {
    "#": 50,
    "Time": 65,
    "Activity": 200,
    "Google Maps Location": 220,
    "Duration (min)": 105,
    "Travel (min)": 90,
    "Notes": 200,
    "Delete": 45,
}


def _save_and_rerun(
    itin: list[dict],
    active_prop: str,
    proposals: dict,
    coords_map: dict[str, tuple[float, float]] | None = None,
    travel_mode: str = "DRIVE",
    start_time: str = "09:30",
) -> None:
    """Persist itinerary to session state and rerun."""
    rebuild_times(itin, coords_map=coords_map, travel_mode=travel_mode, start_time=start_time)
    proposals[active_prop]["itinerary"] = itin
    st.session_state.proposals = proposals
    st.rerun()


def render_itinerary_editor(
    itin: list[dict],
    active_prop: str,
    proposals: dict,
    location: str,
    tour_type: str = "walking",
    coords_map: dict[str, tuple[float, float]] | None = None,
) -> list[dict]:
    """Render the itinerary AgGrid table (route stops only).

    Returns the (possibly updated) itinerary list.
    """
    st.markdown("<div class='section-title'>Itinerary Editor</div>", unsafe_allow_html=True)

    travel_mode = "WALK" if tour_type == "walking" else "DRIVE"

    # Event start time picker (per-proposal)
    current_proposal = proposals[active_prop]
    stored_start = current_proposal.get("start_time", "09:30")
    h, m = (int(x) for x in stored_start.split(":"))
    start_val = datetime.time(h, m)

    new_start = st.time_input(
        "Event Start Time",
        value=start_val,
        step=datetime.timedelta(minutes=15),
        key=f"start_time_{active_prop}",
    )
    start_time = new_start.strftime("%H:%M")

    # Persist if changed and recalculate times
    if start_time != stored_start:
        current_proposal["start_time"] = start_time
        st.session_state.proposals = proposals
        if itin:
            rebuild_times(itin, coords_map=coords_map, travel_mode=travel_mode, start_time=start_time)
            current_proposal["itinerary"] = itin
            st.session_state.proposals = proposals
            st.rerun()

    if not itin:
        st.info("No route stops yet — click '+ Add Stop' to build your route.")
        _render_action_buttons(itin, active_prop, proposals, location, coords_map, travel_mode, start_time)
        return itin

    # Build DataFrame
    rows = []
    for idx, item in enumerate(itin):
        rows.append(
            {
                "#": idx + 1,
                "Time": item.get("time", "--:--"),
                "Activity": item.get("activity", ""),
                "Google Maps Location": item.get("gmaps_location", ""),
                "Duration (min)": item.get("duration_min", 60),
                "Travel (min)": item.get("travel_duration_min", 0),
                "Notes": item.get("notes", ""),
                "Delete": False,
            }
        )
    df = pd.DataFrame(rows)

    # AgGrid options
    gb = GridOptionsBuilder.from_dataframe(df)

    gb.configure_column(
        "#",
        header_name="#",
        width=_COL_W["#"],
        editable=False,
        filter=False,
        sortable=False,
        resizable=False,
        suppressHeaderMenuButton=True,
        lockPosition="left",
        rowDrag=True,
    )
    gb.configure_column(
        "Time",
        width=_COL_W["Time"],
        editable=False,
        filter=False,
        sortable=False,
        suppressHeaderMenuButton=True,
    )
    gb.configure_column("Activity", width=_COL_W["Activity"], editable=True, singleClickEdit=True)
    gb.configure_column(
        "Google Maps Location",
        width=_COL_W["Google Maps Location"],
        editable=False,
    )
    gb.configure_column(
        "Duration (min)",
        width=_COL_W["Duration (min)"],
        editable=True,
        singleClickEdit=True,
        type=["numericColumn"],
    )
    gb.configure_column(
        "Travel (min)",
        width=_COL_W["Travel (min)"],
        editable=False,
        filter=False,
        sortable=False,
        suppressHeaderMenuButton=True,
    )
    gb.configure_column("Notes", width=_COL_W["Notes"], editable=True, singleClickEdit=True)

    # Delete column — checkbox acts as ✕ trigger
    gb.configure_column(
        "Delete",
        header_name="✕",
        width=_COL_W["Delete"],
        editable=True,
        singleClickEdit=True,
        cellRenderer="agCheckboxCellRenderer",
        cellEditor="agCheckboxCellEditor",
        filter=False,
        sortable=False,
        resizable=False,
        suppressHeaderMenuButton=True,
        lockPosition="right",
        suppressSizeToFit=True,
    )

    gb.configure_grid_options(
        animateRows=True,
        suppressRowClickSelection=True,
        rowSelection="single",
        rowDragManaged=True,
        rowDragEntireRow=True,
    )

    # Render grid
    grid_resp = AgGrid(
        df,
        gridOptions=gb.build(),
        update_mode=GridUpdateMode.VALUE_CHANGED | GridUpdateMode.MODEL_CHANGED,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        fit_columns_on_grid_load=False,
        allow_unsafe_jscode=True,
        height=min(46 * len(itin) + 58, 500),
        theme="streamlit",
        custom_css={
            "[col-id='Delete'] .ag-header-cell-label": {
                "justify-content": "center",
                "color": "#666 !important",
            },
            "[col-id='Delete'] .ag-cell-value": {"text-align": "center"},
        },
    )

    # Process grid response (value edits + deletions + reorder)
    result = grid_resp.get("data")
    if result is not None and isinstance(result, pd.DataFrame) and not result.empty:
        del_mask = result["Delete"].astype(bool)
        if del_mask.any():
            result = result[~del_mask].reset_index(drop=True)

        new_itin = _df_to_itin(result, itin)
        changed = _detect_change(itin, new_itin)

        if changed:
            rebuild_times(new_itin, coords_map=coords_map, travel_mode=travel_mode, start_time=start_time)
            itin = new_itin
            proposals[active_prop]["itinerary"] = itin
            st.session_state.proposals = proposals
            st.rerun()

    # Update Location (Google Places autocomplete)
    if itin:
        _render_location_editor(itin, active_prop, proposals)

    # Action buttons
    _render_action_buttons(itin, active_prop, proposals, location, coords_map, travel_mode, start_time)

    return itin


# Helpers


def _resolve_and_store_coords(
    item: dict,
    place_description: str,
) -> None:
    """Resolve coordinates for a place and store them on the item."""
    item["gmaps_location"] = place_description

    coords = get_place_coordinates(place_description)
    if coords:
        item["user_lat"] = coords[0]
        item["user_lng"] = coords[1]


def _render_location_editor(
    itin: list[dict],
    active_prop: str,
    proposals: dict,
) -> None:
    """Render the Google Places autocomplete location editor."""
    st.markdown(
        "<div style='font-size:0.78rem;color:var(--muted);margin-top:0.5rem'>"
        "Update Location</div>",
        unsafe_allow_html=True,
    )
    col_sel, col_search, col_apply = st.columns([2, 4, 1])

    with col_sel:
        activity_names = [item["activity"] for item in itin]
        selected_activity = st.selectbox(
            "Activity",
            activity_names,
            key="loc_edit_activity",
            label_visibility="collapsed",
        )

    with col_search:
        selected_place = st_searchbox(
            search_places,
            key="loc_edit_searchbox",
            placeholder="Search Google Maps location...",
            clear_on_submit=False,
        )

    with col_apply:
        st.markdown("<div style='height:0.35rem'></div>", unsafe_allow_html=True)
        apply_clicked = st.button("Set", key="loc_edit_apply", use_container_width=True)

    if apply_clicked and selected_place and selected_activity:
        for item in itin:
            if item["activity"] == selected_activity:
                _resolve_and_store_coords(item, selected_place)
                break
        proposals[active_prop]["itinerary"] = itin
        st.session_state.proposals = proposals
        st.rerun()


def _df_to_itin(df: pd.DataFrame, orig_itin: list[dict]) -> list[dict]:
    """Convert grid DataFrame back into itinerary dicts (route stops only)."""
    orig_by_name = {a.get("activity", ""): a for a in orig_itin}
    new_itin = []
    for _, row in df.iterrows():
        name = str(row["Activity"])
        orig = orig_by_name.get(name, {})
        entry = {
            "time": str(row.get("Time", "--:--")),
            "activity": name,
            "gmaps_location": str(row.get("Google Maps Location", "")),
            "type": orig.get("type", "adventure"),
            "duration_min": int(row.get("Duration (min)") or 60),
            "notes": str(row.get("Notes", "")),
            "travel_duration_min": int(row.get("Travel (min)") or 0),
        }
        if "user_lat" in orig:
            entry["user_lat"] = orig["user_lat"]
            entry["user_lng"] = orig["user_lng"]
        new_itin.append(entry)
    return new_itin


def _detect_change(old: list[dict], new: list[dict]) -> bool:
    """Return True if the two itinerary lists differ in any meaningful way."""
    if len(old) != len(new):
        return True
    for o, n in zip(old, new):
        if (
            o.get("activity") != n.get("activity")
            or o.get("gmaps_location") != n.get("gmaps_location")
            or o.get("duration_min") != n.get("duration_min")
            or o.get("notes") != n.get("notes")
        ):
            return True
    return False


def _render_action_buttons(
    itin: list[dict],
    active_prop: str,
    proposals: dict,
    location: str,
    coords_map: dict[str, tuple[float, float]] | None = None,
    travel_mode: str = "DRIVE",
    start_time: str = "09:30",
) -> None:
    """Render Recalculate Times and + Add Stop buttons."""
    col_a, col_b = st.columns(2)

    with col_a:
        if st.button("↺  Recalculate Times", use_container_width=True, key="btn_recalc"):
            rebuild_times(itin, coords_map=coords_map, travel_mode=travel_mode, start_time=start_time)
            proposals[active_prop]["itinerary"] = itin
            st.session_state.proposals = proposals
            st.rerun()

    with col_b:
        if st.button("+ Add Stop", use_container_width=True, key="btn_add_activity"):
            st.session_state.show_add_form = True

    # Add Stop form
    if st.session_state.get("show_add_form"):
        st.markdown("**Add Route Stop**")

        activity_name = st.text_input("Activity name", placeholder="e.g. Ribeira Walk", key="add_custom_name")

        gmaps_loc = st_searchbox(
            search_places,
            key="add_location_searchbox",
            placeholder="Search Google Maps location...",
            clear_on_submit=False,
        )

        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            submitted = st.button("Add to Route", use_container_width=True, key="btn_add_submit")
        with btn_col2:
            cancelled = st.button("Cancel", use_container_width=True, key="btn_add_cancel")

        if submitted:
            if not activity_name.strip():
                st.error("Please enter an activity name.")
            else:
                gmaps_loc_str = gmaps_loc or ""
                new_act = {
                    "time": "--:--",
                    "activity": activity_name.strip(),
                    "gmaps_location": gmaps_loc_str,
                    "type": "adventure",
                    "duration_min": 60,
                    "notes": "",
                    "travel_duration_min": 15,
                }
                if new_act["gmaps_location"]:
                    coords = get_place_coordinates(new_act["gmaps_location"])
                    if coords:
                        new_act["user_lat"] = coords[0]
                        new_act["user_lng"] = coords[1]
                itin.append(new_act)
                rebuild_times(itin, coords_map=coords_map, travel_mode=travel_mode, start_time=start_time)
                proposals[active_prop]["itinerary"] = itin
                st.session_state.proposals = proposals
                st.session_state.show_add_form = False
                st.rerun()

        if cancelled:
            st.session_state.show_add_form = False
            st.rerun()
