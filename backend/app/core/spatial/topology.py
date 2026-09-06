"""
MemoryVault AI — Household Spatial Topology
============================================
Phase 3, Step 1  |  SRS FR-07 — Spatial Graph Representation

Models the household as a weighted, undirected graph G = (V, E) where:
  V  = 6 domestic zones (matching the ML classifier's target_zone labels exactly)
  E  = bidirectional edges whose weights represent realistic traversal
       distances in metres between adjacent rooms / furniture positions

Zone coordinate system
----------------------
Distances are in metres from an origin at the front door (foyer_credenza).
The coordinate plane is a top-down 2-D floor-plan projection:

         work_desk (1, 6) ──── bedroom_nightstand (2.5, 8)
              │                         │
              │                         │
         kitchen_counter (2, 4) ─────────
              │       ╲
              │         ╲
    foyer_credenza(0, 0)  living_room_coffee_table (4, 1)
                                     │
                               couch_cushion (5, 1.5)

Graph edges (bidirectional, weights in metres)
----------------------------------------------
Specified edges (from SRS FR-07):
  foyer_credenza      ↔ kitchen_counter              4.5 m
  foyer_credenza      ↔ living_room_coffee_table     3.8 m
  living_room_coffee_table ↔ couch_cushion           1.2 m
  kitchen_counter     ↔ work_desk                   2.8 m
  work_desk           ↔ bedroom_nightstand           3.2 m

Additional domestic-realism edges (ensure full connectivity):
  kitchen_counter     ↔ living_room_coffee_table     3.5 m
  kitchen_counter     ↔ bedroom_nightstand           4.5 m
  living_room_coffee_table ↔ work_desk              5.5 m
  foyer_credenza      ↔ work_desk                   6.1 m
  couch_cushion       ↔ bedroom_nightstand           7.0 m

Heuristic function
------------------
euclidean_distance(zone_a, zone_b) computes the straight-line distance
between two zone coordinates.  This is an admissible heuristic for A*
search because Euclidean distance never overestimates the actual path cost
(it is always ≤ the shortest path weight through the graph).

Usage
-----
  from app.core.spatial.topology import (
      get_all_zones,
      get_zone_coordinates,
      get_neighbors,
      euclidean_distance,
      GRAPH,
  )
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import ClassVar


# ===========================================================================
# Zone data model
# ===========================================================================

@dataclass(frozen=True)
class Zone:
    """Represents a single domestic zone node in the spatial graph."""

    identifier:  str    # must match ML target_zone labels exactly
    display_name: str   # human-readable label for the UI
    x:           float  # floor-plan x coordinate (metres from origin)
    y:           float  # floor-plan y coordinate (metres from origin)
    description: str    # contextual description for the Evaluator drawer

    def __str__(self) -> str:
        return f"Zone({self.identifier}, x={self.x}, y={self.y})"


# ===========================================================================
# Zone definitions  (identifiers match ML training labels exactly)
# ===========================================================================

_ZONE_DEFS: list[Zone] = [
    Zone(
        identifier   = "foyer_credenza",
        display_name = "Foyer Credenza",
        x            = 0.0,
        y            = 0.0,
        description  = "Default entry node. Items dropped immediately on arrival.",
    ),
    Zone(
        identifier   = "kitchen_counter",
        display_name = "Kitchen Counter",
        x            = 2.0,
        y            = 4.0,
        description  = "High-traffic surface near food-prep area.",
    ),
    Zone(
        identifier   = "living_room_coffee_table",
        display_name = "Living Room Coffee Table",
        x            = 4.0,
        y            = 1.0,
        description  = "Central relaxation surface in the living area.",
    ),
    Zone(
        identifier   = "couch_cushion",
        display_name = "Couch Cushion",
        x            = 5.0,
        y            = 1.5,
        description  = "Adjacent to the coffee table; common fatigue-drop zone.",
    ),
    Zone(
        identifier   = "work_desk",
        display_name = "Work Desk",
        x            = 1.0,
        y            = 6.0,
        description  = "Home office surface; high daytime item concentration.",
    ),
    Zone(
        identifier   = "bedroom_nightstand",
        display_name = "Bedroom Nightstand",
        x            = 2.5,
        y            = 8.0,
        description  = "Bedside surface; dominant night / high-fatigue zone.",
    ),
]

# Indexed by identifier for O(1) lookup
ZONES: dict[str, Zone] = {z.identifier: z for z in _ZONE_DEFS}


# ===========================================================================
# Adjacency / edge dictionary  (bidirectional, weights in metres)
# ===========================================================================
#
# Edge list: (zone_a, zone_b, distance_metres)
# All edges are inserted in both directions when GRAPH is built.
#
_EDGE_LIST: list[tuple[str, str, float]] = [
    # ── SRS FR-07 specified edges ─────────────────────────────────────────
    ("foyer_credenza",            "kitchen_counter",              4.5),
    ("foyer_credenza",            "living_room_coffee_table",     4.2),
    ("living_room_coffee_table",  "couch_cushion",                1.2),
    ("kitchen_counter",           "work_desk",                    2.8),
    ("work_desk",                 "bedroom_nightstand",           3.2),
    # ── Domestic-realism edges (ensure full graph connectivity) ──────────
    ("kitchen_counter",           "living_room_coffee_table",     3.7),
    ("kitchen_counter",           "bedroom_nightstand",           4.5),
    ("living_room_coffee_table",  "work_desk",                    5.9),
    ("foyer_credenza",            "work_desk",                    6.1),
    ("couch_cushion",             "bedroom_nightstand",           7.0),
]


class HouseholdGraph:
    """
    Weighted, undirected household zone graph G = (V, E).

    Attributes
    ----------
    nodes : dict[str, Zone]
        Zone identifier -> Zone dataclass.
    edges : dict[str, dict[str, float]]
        Adjacency dictionary: edges[zone_a][zone_b] = distance_metres.
    """

    def __init__(self, zones: dict[str, Zone], edges: list[tuple[str, str, float]]) -> None:
        self.nodes: dict[str, Zone]             = zones
        self.edges: dict[str, dict[str, float]] = {z: {} for z in zones}

        for zone_a, zone_b, dist in edges:
            if zone_a not in self.nodes:
                raise ValueError(f"Unknown zone in edge definition: '{zone_a}'")
            if zone_b not in self.nodes:
                raise ValueError(f"Unknown zone in edge definition: '{zone_b}'")
            # Bidirectional
            self.edges[zone_a][zone_b] = dist
            self.edges[zone_b][zone_a] = dist

    def __repr__(self) -> str:
        n = len(self.nodes)
        e = sum(len(v) for v in self.edges.values()) // 2
        return f"HouseholdGraph(|V|={n}, |E|={e})"


# Module-level singleton — import and use directly
GRAPH: HouseholdGraph = HouseholdGraph(ZONES, _EDGE_LIST)


# ===========================================================================
# Public helper API
# ===========================================================================

def get_all_zones() -> list[str]:
    """Return all zone identifiers in definition order."""
    return [z.identifier for z in _ZONE_DEFS]


def get_zone_coordinates(zone: str) -> tuple[float, float]:
    """
    Return the (x, y) floor-plan coordinates for *zone*.

    Raises
    ------
    KeyError if *zone* is not a registered identifier.
    """
    try:
        z = GRAPH.nodes[zone]
    except KeyError:
        raise KeyError(
            f"Unknown zone: '{zone}'. Valid zones: {get_all_zones()}"
        )
    return (z.x, z.y)


def get_neighbors(zone: str) -> dict[str, float]:
    """
    Return a dict mapping each directly adjacent zone to its edge distance.

    Parameters
    ----------
    zone : str
        A registered zone identifier.

    Returns
    -------
    dict[str, float]
        {neighbor_identifier: distance_metres, ...}

    Raises
    ------
    KeyError if *zone* is not a registered identifier.
    """
    if zone not in GRAPH.nodes:
        raise KeyError(
            f"Unknown zone: '{zone}'. Valid zones: {get_all_zones()}"
        )
    return dict(GRAPH.edges[zone])


def euclidean_distance(zone_a: str, zone_b: str) -> float:
    """
    Compute the straight-line (Euclidean) distance between two zones.

    This function serves as the **admissible heuristic** h(n) for A* search:
    Euclidean distance is guaranteed to never overestimate the true shortest
    path cost through the graph, so A* remains optimal when using it.

    Parameters
    ----------
    zone_a, zone_b : str
        Registered zone identifiers.

    Returns
    -------
    float
        Straight-line distance in metres.

    Raises
    ------
    KeyError if either identifier is not registered.
    """
    xa, ya = get_zone_coordinates(zone_a)
    xb, yb = get_zone_coordinates(zone_b)
    return math.sqrt((xb - xa) ** 2 + (yb - ya) ** 2)


# ===========================================================================
# Self-test block
# ===========================================================================

if __name__ == "__main__":
    print()
    print("=" * 62)
    print("  MemoryVault AI — Household Spatial Graph (topology.py)")
    print("=" * 62)

    # ---- Nodes ----
    print(f"\n  Graph: {GRAPH}")
    print("\n  Nodes (zones):")
    print(f"  {'ID':<32} {'x':>5}  {'y':>5}  Description")
    print(f"  {'-'*32} {'-'*5}  {'-'*5}  {'-'*36}")
    for zone in get_all_zones():
        z = GRAPH.nodes[zone]
        print(f"  {zone:<32} {z.x:>5.1f}  {z.y:>5.1f}  {z.description[:36]}")

    # ---- Adjacency ----
    print("\n  Adjacency list (edges, metres):")
    for zone in get_all_zones():
        neighbors = get_neighbors(zone)
        if neighbors:
            nb_str = "  |  ".join(
                f"{nb} ({dist:.1f} m)"
                for nb, dist in sorted(neighbors.items(), key=lambda t: t[1])
            )
            print(f"    {zone}")
            print(f"      -> {nb_str}")

    # ---- Euclidean distances (all pairs) ----
    zones = get_all_zones()
    print(f"\n  Euclidean distances (heuristic h) — metres:")
    hdr = f"  {'FROM \\ TO':<32}" + "".join(f"{z[:6]:>8}" for z in zones)
    print(hdr)
    print(f"  {'-'*32}" + "-" * (8 * len(zones)))
    for za in zones:
        row = f"  {za:<32}"
        for zb in zones:
            d = euclidean_distance(za, zb)
            row += f"{d:>8.2f}" if za != zb else f"{'---':>8}"
        print(row)

    # ---- Admissibility check (h <= actual edge cost for all direct edges) ----
    print("\n  Admissibility check (h(a,b) <= w(a,b) for all edges):")
    all_admissible = True
    for za, zb, w in _EDGE_LIST:
        h = euclidean_distance(za, zb)
        ok = h <= w + 1e-9
        if not ok:
            all_admissible = False
        flag = "[OK]" if ok else "[FAIL]"
        print(f"    {za} <-> {zb}:  h={h:.3f}  w={w:.1f}  {flag}")
    print(f"\n  Heuristic admissibility: {'PASS' if all_admissible else 'FAIL'}")
    print()
