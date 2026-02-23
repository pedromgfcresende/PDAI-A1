"""Activities editor — billable services table with catalog selector.

Activities are billing items (e.g., Jeep Tour, Walking Tour, RZR, Photography)
that are separate from route stops in the itinerary.

Catalog items (Jeeps, Walking, RZR) have auto-calculated pricing that is locked.
Manual activities have quantity locked to group_size, price editable.
"""

from __future__ import annotations

import math

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, DataReturnMode, GridOptionsBuilder, GridUpdateMode, JsCode

from data.catalog import ACTIVITY_CATALOG
from data.engine import compute_catalog_activity

_COL_W = {
    "#": 45,
    "Activity": 200,
    "Type": 100,
    "Unit Price (\u20ac)": 110,
    "Qty": 70,
    "Total (\u20ac)": 100,
    "Notes": 180,
    "Delete": 45,
}


def _save_and_rerun(
    activities: list[dict],
    active_prop: str,
    proposals: dict,
) -> None:
    """Persist activities to session state and rerun."""
    proposals[active_prop]["activities"] = activities
    st.session_state.proposals = proposals
    st.rerun()


def render_activities_editor(
    activities: list[dict],
    active_prop: str,
    proposals: dict,
    group_size: int,
    tour_type: str,
    duration_hours: int,
    location: str,
) -> tuple[list[dict], str]:
    """Render catalog selector + activities billing table.

    Returns the (possibly updated) activities list and current tour_type.
    """
    st.markdown("<div class='section-title'>Activities & Billing</div>", unsafe_allow_html=True)

    # ── Catalog selector ────────────────────────────────────────────
    _render_catalog_selector(activities, active_prop, proposals, group_size, duration_hours)

    if not activities:
        st.info("No activities yet \u2014 select from the catalog above or click '+ Add Activity'.")
        _render_add_activity(activities, active_prop, proposals, group_size)
        return activities, tour_type

    # ── Build DataFrame ──────────────────────────────────────────────
    rows = []
    for idx, act in enumerate(activities):
        rows.append({
            "#": idx + 1,
            "Activity": act.get("name", ""),
            "Type": act.get("type", ""),
            "Unit Price (\u20ac)": act.get("unit_price", 0.0),
            "Qty": act.get("quantity", 1),
            "Total (\u20ac)": act.get("total", 0.0),
            "Notes": act.get("notes", ""),
            "Delete": False,
        })
    df = pd.DataFrame(rows)

    # ── AgGrid options ─────────────────────────────────────────────
    gb = GridOptionsBuilder.from_dataframe(df)

    gb.configure_column("#", width=_COL_W["#"], editable=False, filter=False, sortable=False,
                        suppressHeaderMenuButton=True)
    gb.configure_column("Activity", width=_COL_W["Activity"], editable=True, singleClickEdit=True)
    gb.configure_column("Type", width=_COL_W["Type"], editable=True, singleClickEdit=True,
                        cellEditor="agSelectCellEditor",
                        cellEditorParams={"values": ["adventure", "cultural", "food", "transport", "service"]})

    # Unit Price: editable only for non-auto_calc rows
    # use a JS expression to conditionally disable editing
    price_editable_js = JsCode("function(params) { return !params.data._auto_calc; }")
    gb.configure_column("Unit Price (\u20ac)", width=_COL_W["Unit Price (\u20ac)"],
                        editable=True, singleClickEdit=True, type=["numericColumn"],
                        cellStyle=JsCode(
                            "function(params) { return params.data._auto_calc "
                            "? {backgroundColor: '#1a1a1a', color: '#888'} : {}; }"
                        ))

    # Qty: always non-editable (locked for both catalog and manual)
    gb.configure_column("Qty", width=_COL_W["Qty"], editable=False,
                        type=["numericColumn"],
                        cellStyle=JsCode(
                            "function(params) { return {backgroundColor: '#1a1a1a', color: '#888'}; }"
                        ))

    gb.configure_column("Total (\u20ac)", width=_COL_W["Total (\u20ac)"], editable=False,
                        type=["numericColumn"])
    gb.configure_column("Notes", width=_COL_W["Notes"], editable=True, singleClickEdit=True)
    gb.configure_column("Delete", header_name="\u2715", width=_COL_W["Delete"], editable=True,
                        singleClickEdit=True, cellRenderer="agCheckboxCellRenderer",
                        cellEditor="agCheckboxCellEditor", filter=False, sortable=False,
                        resizable=False, suppressHeaderMenuButton=True, lockPosition="right",
                        suppressSizeToFit=True)

    # Hidden column for auto_calc flag - used by JS expressions
    gb.configure_column("_auto_calc", hide=True)

    gb.configure_grid_options(animateRows=True, suppressRowClickSelection=True)

    # Add hidden _auto_calc column to dataframe 
    auto_calc_flags = [act.get("auto_calc", False) for act in activities]
    df["_auto_calc"] = auto_calc_flags

    # Render grid 
    grid_resp = AgGrid(
        df,
        gridOptions=gb.build(),
        update_mode=GridUpdateMode.VALUE_CHANGED | GridUpdateMode.MODEL_CHANGED,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        fit_columns_on_grid_load=False,
        allow_unsafe_jscode=True,
        height=min(46 * len(activities) + 58, 400),
        theme="streamlit",
        key=f"act_grid_{active_prop}",
        custom_css={
            "[col-id='Delete'] .ag-header-cell-label": {
                "justify-content": "center",
                "color": "#666 !important",
            },
            "[col-id='Delete'] .ag-cell-value": {"text-align": "center"},
        },
    )

    # Process grid response 
    result = grid_resp.get("data")
    if result is not None and isinstance(result, pd.DataFrame) and not result.empty:
        del_mask = result["Delete"].astype(bool)
        if del_mask.any():
            result = result[~del_mask].reset_index(drop=True)

        new_activities = _df_to_activities(result, activities)
        if _detect_change(activities, new_activities):
            activities = new_activities
            proposals[active_prop]["activities"] = activities
            st.session_state.proposals = proposals
            st.rerun()

    # Add Activity button 
    _render_add_activity(activities, active_prop, proposals, group_size)

    return activities, tour_type


def _render_catalog_selector(
    activities: list[dict],
    active_prop: str,
    proposals: dict,
    group_size: int,
    duration_hours: float,
) -> None:
    """Render catalog buttons for Jeeps, Walking, RZR."""
    cols = st.columns(len(ACTIVITY_CATALOG))
    for col, cat_item in zip(cols, ACTIVITY_CATALOG):
        with col:
            # Check if already added
            already_added = any(
                a.get("catalog_key") == cat_item["name"] for a in activities
            )
            if already_added:
                st.button(
                    f"\u2713 {cat_item['display']}",
                    use_container_width=True,
                    disabled=True,
                    key=f"cat_{cat_item['name']}_{active_prop}",
                )
            else:
                if st.button(
                    cat_item["display"],
                    use_container_width=True,
                    key=f"cat_{cat_item['name']}_{active_prop}",
                ):
                    new_act = compute_catalog_activity(cat_item, group_size, duration_hours)
                    activities.append(new_act)
                    # Update tour_type for travel mode (walking vs drive)
                    if cat_item["name"] == "Walking":
                        proposals[active_prop]["tour_type"] = "walking"
                    else:
                        proposals[active_prop]["tour_type"] = "jeeps"
                    _save_and_rerun(activities, active_prop, proposals)


def _df_to_activities(df: pd.DataFrame, orig: list[dict]) -> list[dict]:
    """Convert grid DataFrame back into activity dicts."""
    orig_by_name = {a.get("name", ""): a for a in orig}
    new_activities = []
    for _, row in df.iterrows():
        name = str(row["Activity"])
        orig_act = orig_by_name.get(name, {})
        is_auto = orig_act.get("auto_calc", False)

        if is_auto:
            # Preserve auto-calculated values exactly
            new_activities.append(dict(orig_act))
        else:
            unit_price = float(row.get("Unit Price (\u20ac)") or 0)
            qty = int(row.get("Qty") or 1)
            new_activities.append({
                "name": name,
                "type": str(row.get("Type", orig_act.get("type", "service"))),
                "unit_price": unit_price,
                "quantity": qty,
                "total": unit_price * qty,
                "per_person": orig_act.get("per_person", True),
                "auto_calc": False,
                "notes": str(row.get("Notes", "")),
            })
    return new_activities


def _detect_change(old: list[dict], new: list[dict]) -> bool:
    """Return True if the two activity lists differ."""
    if len(old) != len(new):
        return True
    for o, n in zip(old, new):
        if (
            o.get("name") != n.get("name")
            or o.get("unit_price") != n.get("unit_price")
            or o.get("quantity") != n.get("quantity")
            or o.get("type") != n.get("type")
            or o.get("notes") != n.get("notes")
        ):
            return True
    return False


def _render_add_activity(
    activities: list[dict],
    active_prop: str,
    proposals: dict,
    group_size: int,
) -> None:
    """Render the Add Activity button and form for manual (non-catalog) activities."""
    if st.button("+ Add Activity", use_container_width=True, key="btn_add_billing_activity"):
        st.session_state.show_add_billing_form = True

    if st.session_state.get("show_add_billing_form"):
        st.markdown("**Add Custom Activity**")

        custom_name = st.text_input("Activity name", placeholder="e.g. Photography, Wine Tasting", key="add_bill_custom_name")

        col3, col4 = st.columns(2)
        with col3:
            custom_price = st.number_input("Unit Price (\u20ac)", value=0.0, min_value=0.0, step=10.0, key="add_bill_price")
        with col4:
            st.number_input("Quantity (per person)", value=group_size, disabled=True, key="add_bill_qty_display")

        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            submitted = st.button("Add Activity", use_container_width=True, key="btn_bill_submit")
        with btn_col2:
            cancelled = st.button("Cancel", use_container_width=True, key="btn_bill_cancel")

        if submitted:
            if not custom_name.strip():
                st.error("Please enter an activity name.")
            else:
                new_act = {
                    "name": custom_name.strip(),
                    "type": "service",
                    "unit_price": custom_price,
                    "quantity": group_size,
                    "total": custom_price * group_size,
                    "per_person": True,
                    "auto_calc": False,
                    "notes": "",
                }
                activities.append(new_act)
                proposals[active_prop]["activities"] = activities
                st.session_state.proposals = proposals
                st.session_state.show_add_billing_form = False
                st.rerun()

        if cancelled:
            st.session_state.show_add_billing_form = False
            st.rerun()
