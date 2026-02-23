"""Google Maps geocoding, places autocomplete & routing service.

Uses the new Google APIs (Places API New, Routes API) via direct HTTP calls.
All functions degrade gracefully when APIs are not enabled.
"""

from __future__ import annotations

import json
import os
import urllib.request

import streamlit as st


def _api_post(url: str, body: dict, headers: dict, timeout: int = 5) -> dict | None:
    """Make a POST request and return parsed JSON, or None on failure."""
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        method="POST",
        headers={"Content-Type": "application/json", **headers},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


@st.cache_data(ttl=3600)
def geocode_location(location_str: str) -> tuple[float, float] | None:
    """Geocode a location string via Google Maps Geocoding API.

    Returns (lat, lng) or None if the key is missing or lookup fails.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key or not location_str or not location_str.strip():
        return None

    try:
        import googlemaps

        gmaps = googlemaps.Client(key=api_key)
        results = gmaps.geocode(location_str)
        if results:
            loc = results[0]["geometry"]["location"]
            return (loc["lat"], loc["lng"])
    except Exception as e:
        st.warning(f"Geocoding failed for '{location_str}': {e}")

    return None


def _decode_polyline(encoded: str) -> list[tuple[float, float]]:
    """Decode a Google encoded polyline string into a list of (lat, lng)."""
    points: list[tuple[float, float]] = []
    idx, lat, lng = 0, 0, 0
    while idx < len(encoded):
        for is_lng in (False, True):
            shift, result = 0, 0
            while True:
                b = ord(encoded[idx]) - 63
                idx += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            delta = ~(result >> 1) if (result & 1) else (result >> 1)
            if is_lng:
                lng += delta
            else:
                lat += delta
        points.append((lat / 1e5, lng / 1e5))
    return points


def search_places(query: str) -> list[str]:
    """Search for places using Google Places Autocomplete (New API).

    Returns a list of place description strings.
    Called by streamlit-searchbox on each keystroke.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key or not query or len(query) < 2:
        return []

    data = _api_post(
        url="https://places.googleapis.com/v1/places:autocomplete",
        body={"input": query},
        headers={"X-Goog-Api-Key": api_key},
    )
    if not data:
        return []

    return [
        s["placePrediction"]["text"]["text"]
        for s in data.get("suggestions", [])
        if "placePrediction" in s
    ]


@st.cache_data(ttl=3600)
def get_place_coordinates(place_description: str) -> tuple[float, float] | None:
    """Get coordinates for a place using Places API searchText.

    Uses the same Places API (New) as autocomplete — no extra API needed.
    Returns (lat, lng) or None.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key or not place_description:
        return None

    data = _api_post(
        url="https://places.googleapis.com/v1/places:searchText",
        body={"textQuery": place_description},
        headers={
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.location",
        },
    )
    if not data:
        return None

    try:
        loc = data["places"][0]["location"]
        return (loc["latitude"], loc["longitude"])
    except (KeyError, IndexError):
        return None


@st.cache_data(ttl=3600)
def get_travel_duration(
    origin: tuple[float, float],
    destination: tuple[float, float],
    travel_mode: str = "DRIVE",
) -> int | None:
    """Get travel duration between two points via the Google Routes API.

    Args:
        origin: (lat, lng) of start point.
        destination: (lat, lng) of end point.
        travel_mode: "DRIVE" or "WALK".

    Returns duration in minutes, or None if the API call fails.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return None

    data = _api_post(
        url="https://routes.googleapis.com/directions/v2:computeRoutes",
        body={
            "origin": {
                "location": {
                    "latLng": {"latitude": origin[0], "longitude": origin[1]},
                },
            },
            "destination": {
                "location": {
                    "latLng": {"latitude": destination[0], "longitude": destination[1]},
                },
            },
            "travelMode": travel_mode,
        },
        headers={
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "routes.duration",
        },
    )
    if not data:
        return None

    try:
        duration_str = data["routes"][0]["duration"]  # e.g. "600s"
        return int(duration_str.rstrip("s")) // 60
    except (KeyError, IndexError, ValueError):
        return None


@st.cache_data(ttl=3600)
def get_route_polyline(
    origin: tuple[float, float],
    destination: tuple[float, float],
    travel_mode: str = "DRIVE",
) -> list[tuple[float, float]] | None:
    """Get route via the Google Routes API (v2).

    Args:
        origin: (lat, lng) of start point.
        destination: (lat, lng) of end point.
        travel_mode: "DRIVE" or "WALK".

    Returns a list of (lat, lng) points tracing the route, or None.
    Falls back silently if the Routes API is not enabled.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return None

    data = _api_post(
        url="https://routes.googleapis.com/directions/v2:computeRoutes",
        body={
            "origin": {
                "location": {
                    "latLng": {"latitude": origin[0], "longitude": origin[1]},
                },
            },
            "destination": {
                "location": {
                    "latLng": {"latitude": destination[0], "longitude": destination[1]},
                },
            },
            "travelMode": travel_mode,
        },
        headers={
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "routes.polyline.encodedPolyline",
        },
    )
    if not data:
        return None

    try:
        encoded = data["routes"][0]["polyline"]["encodedPolyline"]
        return _decode_polyline(encoded)
    except (KeyError, IndexError):
        return None
