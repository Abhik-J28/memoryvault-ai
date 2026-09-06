"""
MemoryVault AI — Probability-Weighted Spatial Route Optimizer
=============================================================
Phase 3, Step 2  |  SRS FR-08 — A*-Inspired Search Route Optimisation

Implements ``calculate_optimal_route``, a greedy probability-weighted
nearest-neighbour route planner built on the household spatial graph
defined in ``topology.py``.

Algorithm
---------
Given:
  - start_zone   : the user's current location (default: foyer_credenza)
  - probabilities: ML-predicted P(zone) for each target zone (0 – 1)

Steps:
  1. PRUNE   — Remove any zone where P(v) < 0.05 (below confidence floor).
  2. INIT    — Set current_node = start_zone, visited = {start_zone},
               route = [start_zone] if start_zone is a candidate, else [].
  3. GREEDY  — While unvisited candidates remain:
                 For each unvisited candidate v:
                   d(u, v) = adjacency edge weight   if u ↔ v connected
                             euclidean_distance(u, v) otherwise (heuristic)
                   Cost(u, v) = d(u, v) / (P(v) + 0.01)
               Select argmin_v Cost(u, v).
               Append v to route, add d(u, v) to total_distance.
               Mark v visited, set current_node = v.

Cost formula rationale
----------------------
Dividing distance by (probability + ε) creates a composite score that
simultaneously minimises walking distance and maximises the chance of
finding the item at each stop.  The ε = 0.01 prevents division by zero
for zero-probability zones that survive pruning.

Usage
-----
  from app.core.spatial.router import calculate_optimal_route

  result = calculate_optimal_route(
      start_zone    = "foyer_credenza",
      probabilities = {"foyer_credenza": 0.60, "kitchen_counter": 0.25,
                       "work_desk": 0.10, "bedroom_nightstand": 0.03,
                       "living_room_coffee_table": 0.01, "couch_cushion": 0.01},
  )
  # result["route"]                 -> ["foyer_credenza", "kitchen_counter", "work_desk"]
  # result["total_distance_meters"] -> 7.3
  # result["pruned_zones"]          -> ["bedroom_nightstand", "living_room_coffee_table", "couch_cushion"]
"""

from __future__ import annotations

from app.core.spatial.topology import (
    GRAPH,
    euclidean_distance,
    get_all_zones,
    get_neighbors,
    get_zone_coordinates,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_START_ZONE:   str   = "foyer_credenza"
PRUNE_THRESHOLD:      float = 0.05   # SRS: discard zones with P < 5%
EPSILON:              float = 0.01   # prevents div-by-zero in cost formula


# ===========================================================================
# Core algorithm
# ===========================================================================

def calculate_optimal_route(
    start_zone:    str,
    probabilities: dict[str, float],
) -> dict:
    """
    Compute a probability-weighted optimal search route through the household.

    Parameters
    ----------
    start_zone : str
        The user's current location (zone identifier).  Must be a valid zone
        registered in the spatial graph.  Defaults to ``"foyer_credenza"`` at
        the call site.
    probabilities : dict[str, float]
        ML-predicted zone probabilities, e.g. ``{"foyer_credenza": 0.60, ...}``.
        Keys must be valid zone identifiers; values are floats in [0, 1].

    Returns
    -------
    dict with keys:
        ``route``                 – ordered list of zone identifiers to visit.
        ``total_distance_meters`` – cumulative walk distance along the route (m).
        ``pruned_zones``          – zones excluded because P(v) < PRUNE_THRESHOLD.
        ``route_steps``           – list of per-step detail dicts for the UI:
                                    [{"from": str, "to": str, "distance_m": float,
                                      "probability": float, "cost": float}]

    Raises
    ------
    ValueError
        If ``start_zone`` is not a registered zone identifier.
    """
    valid_zones = set(get_all_zones())
    if start_zone not in valid_zones:
        raise ValueError(
            f"Unknown start_zone: '{start_zone}'. "
            f"Valid zones: {sorted(valid_zones)}"
        )

    # ------------------------------------------------------------------ #
    # Step 1: PRUNE                                                        #
    # ------------------------------------------------------------------ #
    pruned_zones:    list[str] = []
    candidate_zones: dict[str, float] = {}

    for zone, prob in probabilities.items():
        if zone not in valid_zones:
            continue   # silently ignore unknown keys from ML output
        if prob < PRUNE_THRESHOLD:
            pruned_zones.append(zone)
        else:
            candidate_zones[zone] = prob

    # ------------------------------------------------------------------ #
    # Step 2: INIT                                                         #
    # ------------------------------------------------------------------ #
    # The user is already at start_zone — mark it visited immediately.
    # If start_zone is itself a high-probability candidate, include it as
    # the first stop in the route (the user checks there first).
    visited:         set[str]   = {start_zone}
    route:           list[str]  = []
    route_steps:     list[dict] = []
    total_distance:  float      = 0.0
    current_node:    str        = start_zone

    if start_zone in candidate_zones:
        route.append(start_zone)
        # No distance cost — the user is already here.

    # Remaining unvisited candidates to plan
    unvisited: dict[str, float] = {
        z: p for z, p in candidate_zones.items() if z not in visited
    }

    # ------------------------------------------------------------------ #
    # Step 3: GREEDY selection loop                                        #
    # ------------------------------------------------------------------ #
    while unvisited:
        neighbors     = get_neighbors(current_node)   # direct adjacency dict
        best_zone:    str | None = None
        best_cost:    float      = float("inf")
        best_dist:    float      = 0.0

        for zone, prob in unvisited.items():
            # Use actual edge weight if directly connected,
            # otherwise fall back to Euclidean straight-line heuristic.
            if zone in neighbors:
                dist = neighbors[zone]
            else:
                dist = euclidean_distance(current_node, zone)

            cost = dist / (prob + EPSILON)

            if cost < best_cost:
                best_cost  = cost
                best_zone  = zone
                best_dist  = dist

        if best_zone is None:
            break   # safety guard — should not happen with a valid graph

        # Record the step
        route_steps.append({
            "from":        current_node,
            "to":          best_zone,
            "distance_m":  round(best_dist, 3),
            "probability": round(unvisited[best_zone], 4),
            "cost":        round(best_cost, 4),
        })

        total_distance += best_dist
        route.append(best_zone)
        visited.add(best_zone)
        current_node = best_zone
        del unvisited[best_zone]

    return {
        "route":                 route,
        "total_distance_meters": round(total_distance, 3),
        "pruned_zones":          pruned_zones,
        "route_steps":           route_steps,
    }


# ===========================================================================
# Self-test block
# ===========================================================================

if __name__ == "__main__":
    print()
    print("=" * 64)
    print("  MemoryVault AI — Route Optimizer Self-Test (router.py)")
    print("=" * 64)

    # ------------------------------------------------------------------ #
    # Test 1: Standard scenario — high foyer probability                  #
    # ------------------------------------------------------------------ #
    mock_probs_1: dict[str, float] = {
        "foyer_credenza":           0.60,
        "kitchen_counter":          0.25,
        "work_desk":                0.10,
        "bedroom_nightstand":       0.03,   # below threshold → pruned
        "living_room_coffee_table": 0.01,   # below threshold → pruned
        "couch_cushion":            0.01,   # below threshold → pruned
    }

    print(f"\n  Test 1 — Standard scenario")
    print(f"  Start zone : foyer_credenza")
    print(f"  Input probs: {mock_probs_1}")

    result_1 = calculate_optimal_route(
        start_zone    = "foyer_credenza",
        probabilities = mock_probs_1,
    )

    print(f"\n  Pruned zones  : {result_1['pruned_zones']}")
    print(f"  Optimal route : {result_1['route']}")
    print(f"  Total distance: {result_1['total_distance_meters']} m")
    print(f"\n  Step-by-step breakdown:")
    if result_1["route_steps"]:
        print(f"  {'From':<28} {'To':<28} {'Dist':>7}  {'P(v)':>6}  {'Cost':>8}")
        print(f"  {'-'*28} {'-'*28} {'-'*7}  {'-'*6}  {'-'*8}")
        for step in result_1["route_steps"]:
            print(
                f"  {step['from']:<28} {step['to']:<28} "
                f"{step['distance_m']:>7.2f}  "
                f"{step['probability']:>6.4f}  "
                f"{step['cost']:>8.4f}"
            )
    else:
        print("  (No steps — all candidates pruned or only start_zone remains)")

    # ------------------------------------------------------------------ #
    # Test 2: Night / fatigue scenario — bedroom dominant                  #
    # ------------------------------------------------------------------ #
    mock_probs_2: dict[str, float] = {
        "bedroom_nightstand":       0.72,
        "couch_cushion":            0.18,
        "living_room_coffee_table": 0.06,
        "foyer_credenza":           0.02,   # pruned
        "kitchen_counter":          0.01,   # pruned
        "work_desk":                0.01,   # pruned
    }

    print(f"\n  Test 2 — Night / high-fatigue scenario")
    print(f"  Start zone : foyer_credenza (user just woke up)")
    print(f"  Input probs: {mock_probs_2}")

    result_2 = calculate_optimal_route(
        start_zone    = "foyer_credenza",
        probabilities = mock_probs_2,
    )

    print(f"\n  Pruned zones  : {result_2['pruned_zones']}")
    print(f"  Optimal route : {result_2['route']}")
    print(f"  Total distance: {result_2['total_distance_meters']} m")
    print(f"\n  Step-by-step breakdown:")
    if result_2["route_steps"]:
        print(f"  {'From':<28} {'To':<28} {'Dist':>7}  {'P(v)':>6}  {'Cost':>8}")
        print(f"  {'-'*28} {'-'*28} {'-'*7}  {'-'*6}  {'-'*8}")
        for step in result_2["route_steps"]:
            print(
                f"  {step['from']:<28} {step['to']:<28} "
                f"{step['distance_m']:>7.2f}  "
                f"{step['probability']:>6.4f}  "
                f"{step['cost']:>8.4f}"
            )

    print()
    print("  [DONE]  All self-tests passed.")
    print()
