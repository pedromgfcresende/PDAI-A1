"""Pricing engine — cost calculations, group discounts, itinerary helpers.

Business rules enforced here:
- Group discount: >10 people → 5% off total
- Photography surcharge: +€200 flat (handled via ADD_ONS catalog)
- Per-person vs flat activity pricing
- Tour type transport cost: Walking (€10/person/h) or Jeeps (€400/jeep/4h, 6 ppl/jeep)
"""

from __future__ import annotations

import datetime
import math
from typing import Any

from services.geocoding import get_travel_duration


def format_date_display(date_str: str | None) -> str:
    """Convert YYYY-MM-DD to dd/mm/yyyy for display."""
    if not date_str:
        return ""
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return date_str


def parse_date_input(date_str: str) -> str:
    """Accept dd/mm/yyyy or YYYY-MM-DD, always return YYYY-MM-DD for storage."""
    if not date_str:
        return ""
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_str


def calc_cost(item: dict, group_size: int) -> float:
    """Return total cost for one itinerary item given the group size (legacy)."""
    return item["cost_raw"] * group_size if item.get("per_person") else item["cost_raw"]


def rebuild_times(
    itin: list[dict],
    coords_map: dict[str, tuple[float, float]] | None = None,
    travel_mode: str = "DRIVE",
    start_time: str = "09:30",
) -> list[dict]:
    """Recalculate wall-clock start times starting at *start_time*.

    If coords_map is provided, uses Google Maps travel durations between
    consecutive activities; otherwise falls back to a 15-min buffer.
    """
    if not itin:
        return itin
    cur = datetime.datetime.strptime(start_time, "%H:%M")
    for i, item in enumerate(itin):
        item["time"] = cur.strftime("%H:%M")
        mins = item.get("duration_min", 60)

        # Calculate travel time to next activity
        travel = 15  # default fallback
        if coords_map and i < len(itin) - 1:
            this_name = item.get("activity", "")
            next_name = itin[i + 1].get("activity", "")
            this_coords = coords_map.get(this_name)
            next_coords = coords_map.get(next_name)
            if this_coords and next_coords:
                api_travel = get_travel_duration(this_coords, next_coords, travel_mode)
                if api_travel is not None:
                    travel = api_travel

        item["travel_duration_min"] = travel if i < len(itin) - 1 else 0
        cur += datetime.timedelta(minutes=mins + (travel if i < len(itin) - 1 else 0))
    return itin


def get_itinerary_for_client(client_data: dict) -> list[dict]:
    """Return an empty itinerary — staff builds from scratch."""
    return []


def compute_catalog_activity(
    catalog_item: dict,
    group_size: int,
    duration_hours: float,
) -> dict:
    """Build an auto-calculated transport activity from a catalog entry.

    Jeeps:   €400 per jeep for 4h blocks, 6 people per jeep.
    Walking: €10 per person per hour.
    RZR:     €200 per car for 2h blocks, 2 people per car.
    """
    name = catalog_item["name"]
    unit_price = catalog_item["unit_price"]
    block_h = catalog_item["time_block_hours"]

    if catalog_item.get("per_person"):
        # Walking: per person per hour
        blocks = max(1, math.ceil(duration_hours / block_h))
        qty = group_size
        total = unit_price * qty * blocks
        return {
            "name": f"{name} Tour",
            "type": "transport",
            "unit_price": unit_price,
            "quantity": qty,
            "total": total,
            "per_person": True,
            "auto_calc": True,
            "catalog_key": name,
            "notes": f"{qty} ppl x {blocks} block(s) of {block_h}h",
        }
    else:
        # Vehicle-based: Jeeps or RZR
        capacity = catalog_item["capacity_per_unit"]
        n_vehicles = math.ceil(group_size / capacity)
        blocks = max(1, math.ceil(duration_hours / block_h))
        qty = n_vehicles * blocks
        total = unit_price * qty
        return {
            "name": f"{name} Tour",
            "type": "transport",
            "unit_price": unit_price,
            "quantity": qty,
            "total": total,
            "per_person": False,
            "auto_calc": True,
            "catalog_key": name,
            "notes": f"{n_vehicles} vehicle(s) x {blocks} block(s) of {block_h}h",
        }


def activities_total_cost(
    activities: list[dict],
    price_overrides: dict[str, float] | None = None,
) -> float:
    """Sum all activity costs, applying manual price overrides when present."""
    t = 0.0
    for act in activities:
        key = act["name"]
        if price_overrides and key in price_overrides:
            t += price_overrides[key]
        else:
            t += act.get("total", 0.0)
    return t


def compute_totals(
    activities: list[dict],
    group_size: int,
    price_overrides: dict[str, float],
    budget_per_person: float | None = None,
) -> dict[str, Any]:
    """Compute all financial aggregates needed by the dashboard.

    Returns:
        grand_total    — before discount
        discount       — 5% if group > 10, else 0
        final_total    — grand_total minus discount
        per_pp         — final_total / group_size
        budget_ok      — per_pp <= budget_per_person (True when no budget set)
    """
    grand_total = activities_total_cost(activities, price_overrides)
    discount = grand_total * 0.05 if group_size > 10 else 0.0
    final_total = grand_total - discount
    per_pp = final_total / group_size if group_size else 0.0
    budget_ok = per_pp <= budget_per_person if budget_per_person is not None else True
    return {
        "grand_total": grand_total,
        "discount": discount,
        "final_total": final_total,
        "per_pp": per_pp,
        "budget_ok": budget_ok,
    }
