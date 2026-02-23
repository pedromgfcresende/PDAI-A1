"""Cost breakdown panel with manual price overrides.

Reads from the activities list (billable services) — not the itinerary (route stops).
"""

from __future__ import annotations

import streamlit as st


def render_pricing_panel(
    activities: list[dict],
    group_size: int,
    price_overrides: dict[str, float],
    grand_total: float,
    discount: float,
    final_total: float,
    per_pp: float,
) -> dict[str, float]:
    """Render the pricing breakdown and return updated price_overrides."""
    st.markdown("<div class='section-title'>Cost Breakdown</div>", unsafe_allow_html=True)

    if not activities:
        st.info("No activities yet — add activities in the Planner tab to see pricing.")
        return price_overrides

    pricing_rows: list[dict] = []

    for act in activities:
        catalog_price = act.get("total", 0.0)
        override_key = act["name"]
        has_override = override_key in price_overrides
        pricing_rows.append({
            "category": act.get("type", "service").title(),
            "item": act["name"],
            "catalog_price": catalog_price,
            "your_price": price_overrides.get(override_key, catalog_price),
            "has_override": has_override,
            "overridable": True,
            "override_key": override_key,
            "auto_calc": act.get("auto_calc", False),
            "notes": act.get("notes", ""),
        })

    for idx, row in enumerate(pricing_rows):
        col1, col2, col3, col4 = st.columns([3, 2, 1, 2])
        with col1:
            label = f"**{row['item']}**"
            if row.get("auto_calc"):
                label += " (auto)"
            st.write(label)
            detail = row["category"]
            if row.get("notes"):
                detail += f" · {row['notes']}"
            st.caption(detail)
        with col2:
            st.write(f"€{row['catalog_price']:,.2f}")
            st.caption("Calculated")
        with col3:
            override = (
                st.checkbox(
                    "Edit",
                    value=row.get("has_override", False),
                    key=f"override_{idx}",
                    label_visibility="collapsed",
                )
                if row["overridable"]
                else False
            )
        with col4:
            ok = row.get("override_key", row["item"])
            if row["overridable"] and override:
                new_price = st.number_input(
                    "Price",
                    value=float(row["your_price"]),
                    min_value=0.0,
                    step=10.0,
                    key=f"price_{idx}",
                    label_visibility="collapsed",
                )
                price_overrides[ok] = new_price
            else:
                st.write(f"€{row['your_price']:,.2f}")
                if ok in price_overrides:
                    del price_overrides[ok]

        st.markdown("---")

    discount_html = (
        f"<div class='price-row'><span>Group Discount (5%)</span>"
        f"<span class='price-val' style='color:var(--orange)'>−€{discount:,.2f}</span></div>"
        if discount > 0
        else ""
    )
    st.markdown(
        f"""
        <div class='ea-card'>
          <div class='price-row'><span>Subtotal</span><span class='price-val'>€{grand_total:,.2f}</span></div>
          {discount_html}
          <div class='price-row total'><span>TOTAL</span><span class='price-val'>€{final_total:,.2f}</span></div>
          <div class='price-row'><span>Per Person</span><span class='price-val'>€{per_pp:,.2f}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    return price_overrides
