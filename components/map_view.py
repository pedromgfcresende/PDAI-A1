"""Route map component using Folium.

Uses Folium + streamlit-folium for the assignment prototype.
Falls back to a styled placeholder if the libraries aren't installed.
"""

from __future__ import annotations

import os

import streamlit as st

from services.geocoding import get_route_polyline

_LOC_CENTERS: dict[str, tuple[float, float]] = {
    "Porto": (41.157, -8.629),
    "Sintra": (38.796, -9.390),
    "Algarve": (37.080, -8.675),
}
_TYPE_COLORS: dict[str, str] = {
    "adventure": "red",
    "cultural": "blue",
    "food": "orange",
    "transport": "gray",
}


def render_map(itin: list[dict], location: str, travel_mode: str = "DRIVE") -> None:
    """Render the route map for the current itinerary.

    Args:
        travel_mode: "DRIVE" or "WALK" — passed to the Routes API for polylines.

    Falls back to a placeholder div when Folium is not available.
    """
    st.markdown("<div class='section-title'>Route Map</div>", unsafe_allow_html=True)

    try:
        import folium
        from streamlit_folium import st_folium

        center = _LOC_CENTERS.get(location, (39.5, -8.0))

        # Use Google Maps tiles if API key is available, otherwise OpenStreetMap
        gmaps_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if gmaps_key:
            m = folium.Map(location=center, zoom_start=11, tiles=None)
            folium.TileLayer(
                tiles=f"https://mt1.google.com/vt/lyrs=m&x={{x}}&y={{y}}&z={{z}}&key={gmaps_key}",
                attr="Google Maps",
                name="Google Maps",
            ).add_to(m)
        else:
            m = folium.Map(location=center, zoom_start=11, tiles="OpenStreetMap")

        coords_seq: list[tuple[float, float]] = []

        for idx, item in enumerate(itin):
            lat, lng = None, None

            if "user_lat" in item and "user_lng" in item:
                lat, lng = item["user_lat"], item["user_lng"]

            if lat is None:
                continue

            coords_seq.append((lat, lng))
            color = _TYPE_COLORS.get(item["type"], "gray")
            folium.Marker(
                location=[lat, lng],
                popup=f"{idx + 1}. {item['activity']}<br>{item['time']}",
                tooltip=f"{idx + 1}. {item['activity']}",
                icon=folium.Icon(color=color, icon="map-marker", prefix="fa"),
            ).add_to(m)

        if len(coords_seq) > 1:
            # Try real road routes via Routes API, fall back to straight lines
            for i in range(len(coords_seq) - 1):
                route_points = get_route_polyline(coords_seq[i], coords_seq[i + 1], travel_mode=travel_mode)
                if route_points:
                    folium.PolyLine(
                        route_points, color="#E86825", weight=4, opacity=0.85,
                    ).add_to(m)
                else:
                    folium.PolyLine(
                        [coords_seq[i], coords_seq[i + 1]],
                        color="#E86825", weight=3, opacity=0.85, dash_array="6",
                    ).add_to(m)
            m.fit_bounds(coords_seq)

        # Build a unique key from the activity order so the map re-renders
        # whenever the itinerary changes (reorder, add, delete, location update)
        map_key = "route_map_" + "_".join(
            f"{item.get('activity','')[:8]}_{item.get('user_lat','')}"
            for item in itin
        )
        st_folium(m, height=400, use_container_width=True, key=map_key)

    except ImportError:
        st.markdown(
            """
            <div class="map-placeholder">
              <div class="map-icon">\U0001f5fa\ufe0f</div>
              <div><strong>Map Preview</strong></div>
              <div style="font-size:0.74rem">Install: pip install streamlit-folium folium</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
