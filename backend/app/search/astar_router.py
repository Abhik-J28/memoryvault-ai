"""
MemoryVault AI — A* Search Router
===================================
Phase 3

Implements a modified A* graph-search algorithm that generates an
optimal room-search checklist.  The cost function incorporates both
physical walking distance and the ML-predicted probability of finding
the item in each room:

    Cost(u, v) = distance(u, v) / (P(v) + ε)     where ε = 0.01

Business Rules
--------------
- BR-03: Rooms with P(v) < 0.05 are pruned from the search space.

Exports
-------
- ``compute_search_route(start, probabilities)`` → ordered checklist
- ``get_layout()`` → raw graph data (for frontend visualization)
"""

from __future__ import annotations

import heapq
import json
import math
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Load graph
# ---------------------------------------------------------------------------

_LAYOUT_PATH = Path(__file__).resolve().parent.parent / "data" / "home_layout.json"

_EPSILON = 0.01
_PRUNE_THRESHOLD = 0.05


def _load_layout() -> dict:
    with open(_LAYOUT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_layout() -> dict:
    """Return the raw home layout JSON for frontend consumption."""
    return _load_layout()


# ---------------------------------------------------------------------------
# Graph helpers
# ---------------------------------------------------------------------------


def _build_adjacency(layout: dict) -> dict[str, list[tuple[str, float]]]:
    """Build an undirected adjacency list from the layout edges."""
    adj: dict[str, list[tuple[str, float]]] = {
        room: [] for room in layout["rooms"]
    }
    for edge in layout["edges"]:
        adj[edge["from"]].append((edge["to"], edge["distance"]))
        adj[edge["to"]].append((edge["from"], edge["distance"]))
    return adj


def _euclidean_heuristic(
    rooms: dict, a: str, b: str
) -> float:
    """Pixel-space Euclidean distance as an admissible A* heuristic."""
    ax, ay = rooms[a]["x"], rooms[a]["y"]
    bx, by = rooms[b]["x"], rooms[b]["y"]
    return math.sqrt((ax - bx) ** 2 + (ay - by) ** 2)


# ---------------------------------------------------------------------------
# A* shortest path (standard, used internally)
# ---------------------------------------------------------------------------


def _astar_path(
    adj: dict[str, list[tuple[str, float]]],
    rooms: dict,
    start: str,
    goal: str,
) -> tuple[list[str], float]:
    """
    Standard A* from *start* to *goal*.

    Returns ``(path, total_distance)``.  If unreachable, returns ``([], inf)``.
    """

    open_set: list[tuple[float, str]] = [(0.0, start)]
    came_from: dict[str, str | None] = {start: None}
    g_score: dict[str, float] = {start: 0.0}

    while open_set:
        _, current = heapq.heappop(open_set)

        if current == goal:
            # Reconstruct path
            path: list[str] = []
            node: str | None = current
            while node is not None:
                path.append(node)
                node = came_from[node]
            path.reverse()
            return path, g_score[current]

        for neighbour, dist in adj.get(current, []):
            tentative = g_score[current] + dist
            if tentative < g_score.get(neighbour, float("inf")):
                g_score[neighbour] = tentative
                priority = tentative + _euclidean_heuristic(rooms, neighbour, goal)
                heapq.heappush(open_set, (priority, neighbour))
                came_from[neighbour] = current

    return [], float("inf")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_search_route(
    start: str,
    probabilities: dict[str, float],
) -> list[dict[str, Any]]:
    """
    Compute an optimal search-route checklist.

    Parameters
    ----------
    start : str
        The room where the user currently is (e.g. ``"entrance_hallway"``).
    probabilities : dict[str, float]
        ML-predicted probability for each room.

    Returns
    -------
    list of dicts, each containing:
        ``room``, ``label``, ``probability``, ``distance_from_previous``,
        ``cumulative_distance``, ``x``, ``y``, ``path_from_previous``

    The list is ordered by decreasing cost-effectiveness
    (highest probability rooms that are closest are checked first).
    """

    layout = _load_layout()
    rooms = layout["rooms"]
    adj = _build_adjacency(layout)

    # --- BR-03: Prune rooms below threshold ---
    candidates = {
        room: prob
        for room, prob in probabilities.items()
        if prob >= _PRUNE_THRESHOLD and room in rooms
    }

    if not candidates:
        # Fallback: include all rooms with any probability
        candidates = {
            room: prob
            for room, prob in probabilities.items()
            if prob > 0 and room in rooms
        }

    # --- Greedy nearest-neighbour with probability-weighted cost ---
    # We visit rooms greedily, always picking the unvisited candidate
    # with the lowest modified-A* cost from the current position.

    visited_order: list[dict[str, Any]] = []
    current = start
    remaining = dict(candidates)
    cumulative_dist = 0.0

    while remaining:
        best_room = None
        best_cost = float("inf")
        best_path: list[str] = []
        best_dist = 0.0

        for room, prob in remaining.items():
            path, dist = _astar_path(adj, rooms, current, room)
            # Modified cost: distance / (probability + ε)
            cost = dist / (prob + _EPSILON)
            if cost < best_cost:
                best_cost = cost
                best_room = room
                best_path = path
                best_dist = dist

        if best_room is None:
            break

        cumulative_dist += best_dist
        visited_order.append(
            {
                "room": best_room,
                "label": rooms[best_room]["label"],
                "probability": round(remaining[best_room], 4),
                "distance_from_previous": round(best_dist, 2),
                "cumulative_distance": round(cumulative_dist, 2),
                "x": rooms[best_room]["x"],
                "y": rooms[best_room]["y"],
                "path_from_previous": best_path,
            }
        )

        current = best_room
        del remaining[best_room]

    return visited_order
