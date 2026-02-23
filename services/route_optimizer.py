"""Nearest-neighbor TSP with 2-opt improvement using Haversine distance.

Pure Python — no external dependencies beyond ``math``.
"""

from __future__ import annotations

import math


def _haversine(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Return distance in km between two (lat, lng) points."""
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def _route_distance(order: list[int], coords: list[tuple[float, float]]) -> float:
    """Total travel distance for an ordered sequence of coordinate indices."""
    return sum(_haversine(coords[order[i]], coords[order[i + 1]]) for i in range(len(order) - 1))


def _nearest_neighbor(coords: list[tuple[float, float]]) -> list[int]:
    """Build a route using the nearest-neighbor heuristic starting from index 0."""
    n = len(coords)
    visited = [False] * n
    order = [0]
    visited[0] = True
    for _ in range(n - 1):
        last = order[-1]
        best_idx, best_dist = -1, float("inf")
        for j in range(n):
            if not visited[j]:
                d = _haversine(coords[last], coords[j])
                if d < best_dist:
                    best_dist = d
                    best_idx = j
        order.append(best_idx)
        visited[best_idx] = True
    return order


def _two_opt(order: list[int], coords: list[tuple[float, float]]) -> list[int]:
    """Improve a route with 2-opt swaps until no improvement is found."""
    improved = True
    best = list(order)
    while improved:
        improved = False
        for i in range(1, len(best) - 1):
            for j in range(i + 1, len(best)):
                new = best[:i] + best[i : j + 1][::-1] + best[j + 1 :]
                if _route_distance(new, coords) < _route_distance(best, coords):
                    best = new
                    improved = True
        # Break after a single full pass with at least one improvement
        if improved:
            improved = True  # continue loop
    return best


def optimize_route(
    items: list[dict],
    coords_map: dict[str, tuple[float, float]],
) -> list[dict]:
    """Reorder *items* to minimize travel distance.

    *coords_map* maps ``item["activity"]`` to ``(lat, lng)``.
    Items without coordinates are appended at the end in their original order.
    """
    with_coords = [(i, item) for i, item in enumerate(items) if item["activity"] in coords_map]
    without_coords = [item for item in items if item["activity"] not in coords_map]

    if len(with_coords) < 2:
        return items  # nothing to optimize

    coords = [coords_map[item["activity"]] for _, item in with_coords]
    nn_order = _nearest_neighbor(coords)
    optimized_order = _two_opt(nn_order, coords)

    result = [with_coords[idx][1] for idx in optimized_order]
    result.extend(without_coords)
    return result
