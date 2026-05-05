"""
A* search for optimal intra-day POI visit ordering.

Problem formulation
-------------------
State:   (current_location: tuple[float,float], unvisited: frozenset[str])
         current_location is either the hotel or the last visited POI.
         unvisited is the set of POI IDs not yet visited this day.

Actions: Visit any POI in unvisited, transitioning to that POI's location
         and removing it from unvisited.

g(n):    Cumulative travel time in minutes (Haversine / walking speed).

h(n):    MST lower bound on remaining travel to complete the day.

         Admissibility proof:
         The optimal path from current location through all unvisited POIs
         and back to the hotel forms a Hamiltonian path on the node set
         {unvisited POIs ∪ hotel}. Any Hamiltonian path is a spanning tree
         (n nodes, n-1 edges), so its cost ≥ MST cost on those nodes.
         Therefore h(n) = MST({unvisited ∪ hotel}) ≤ true remaining cost,
         making h admissible.

         We use Prim's algorithm for MST (O(n²) — fast enough for n ≤ 7).

Goal:    unvisited == frozenset() AND current_location == hotel.
         Equivalently: all POIs visited, returned to hotel.
"""

from __future__ import annotations

import heapq
import math
from typing import Optional

from .config import MAX_POIS_PER_DAY
from .data_loader import POI
from .utils import travel_time_minutes


# ---------------------------------------------------------------------------
# MST heuristic (Prim's algorithm)
# ---------------------------------------------------------------------------

def _mst_cost(nodes: list[tuple[float, float]]) -> float:
    """
    Compute the Minimum Spanning Tree cost for a set of (lat, lon) nodes
    using Prim's algorithm with travel-time (minutes) as edge weight.

    Returns 0.0 for fewer than 2 nodes.
    """
    n = len(nodes)
    if n < 2:
        return 0.0

    in_tree = [False] * n
    min_edge = [math.inf] * n
    min_edge[0] = 0.0
    total = 0.0

    for _ in range(n):
        # Pick the node not yet in the tree with minimum edge cost
        u = min(
            (i for i in range(n) if not in_tree[i]),
            key=lambda i: min_edge[i],
        )
        in_tree[u] = True
        total += min_edge[u]

        # Update min_edge for neighbours
        for v in range(n):
            if not in_tree[v]:
                cost = travel_time_minutes(
                    nodes[u][0], nodes[u][1],
                    nodes[v][0], nodes[v][1],
                    mode="transit",
                )
                if cost < min_edge[v]:
                    min_edge[v] = cost

    return total

# ---------------------------------------------------------------------------
# A* state and priority queue entry
# ---------------------------------------------------------------------------

class _State:
    """A* search state: (location, frozenset of unvisited POI IDs)."""

    __slots__ = ("lat", "lon", "unvisited")

    def __init__(self, lat: float, lon: float, unvisited: frozenset[str]) -> None:
        self.lat = lat
        self.lon = lon
        self.unvisited = unvisited

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _State):
            return False
        return (self.lat, self.lon, self.unvisited) == (other.lat, other.lon, other.unvisited)

    def __hash__(self) -> int:
        return hash((self.lat, self.lon, self.unvisited))

class _PQEntry:
    """Priority queue entry: (f_score, tie_breaker, g_score, state, path)."""

    __slots__ = ("f", "seq", "g", "state", "path")
    _counter = 0
    
    def __init__(
        self,
        f: float,
        g: float,
        state: _State,
        path: list[str],
    ) -> None:
        self.f = f
        self.g = g
        self.state = state
        self.path = path
        _PQEntry._counter += 1
        self.seq = _PQEntry._counter

    def __lt__(self, other: "_PQEntry") -> bool:
        return (self.f, self.seq) < (other.f, other.seq)

# ---------------------------------------------------------------------------
# A* router
# ---------------------------------------------------------------------------

def route_day(
    pois: list[POI],
    hotel: tuple[float, float],
) -> list[POI]:
    """
    Find the optimal visit order for a single day's POIs starting and ending
    at the hotel, using A* search with MST admissible heuristic.

    Args:
        pois: POIs to visit (already capped to MAX_POIS_PER_DAY).
        hotel: (lat, lon) of the hotel (start and end point).

    Returns:
        Ordered list of POIs giving the minimum-travel-time route.
        Returns pois unchanged if len(pois) <= 1 (trivial case).
    """
    if len(pois) == 0:
        return []
    if len(pois) == 1:
        return list(pois)

    # Cap POIs to keep state space tractable (should already be done by CSP)
    if len(pois) > MAX_POIS_PER_DAY:
        pois = pois[:MAX_POIS_PER_DAY]

    poi_map: dict[str, POI] = {p.id: p for p in pois}
    hotel_lat, hotel_lon = hotel

    initial_unvisited = frozenset(poi_map.keys())
    initial_state = _State(hotel_lat, hotel_lon, initial_unvisited)

    # h for initial state
    def heuristic(state: _State) -> float:
        nodes = [(poi_map[pid].lat, poi_map[pid].lon) for pid in state.unvisited]
        nodes.append((hotel_lat, hotel_lon))
        return _mst_cost(nodes)

    start_entry = _PQEntry(
        f=heuristic(initial_state),
        g=0.0,
        state=initial_state,
        path=[],
    )

    open_set: list[_PQEntry] = [start_entry]
    heapq.heapify(open_set)
    visited: dict[_State, float] = {}

    while open_set:
        entry = heapq.heappop(open_set)
        state = entry.state

        # Check if already visited with lower cost
        if state in visited and visited[state] <= entry.g:
            continue
        visited[state] = entry.g

        # Goal check: all visited and back at hotel
        if not state.unvisited:
            # Return cost is from current location back to hotel
            return_cost = travel_time_minutes(
                state.lat, state.lon,
                hotel_lat, hotel_lon,
                mode="transit",
            )
            total_g = entry.g + return_cost
            # Reconstruct path
            return [poi_map[pid] for pid in entry.path]

        # Expand: try visiting each unvisited POI
        for next_id in state.unvisited:
            next_poi = poi_map[next_id]
            travel_cost = travel_time_minutes(
                state.lat, state.lon,
                next_poi.lat, next_poi.lon,
                mode="transit",
            )
            new_g = entry.g + travel_cost + next_poi.avg_duration_minutes
            new_unvisited = state.unvisited - {next_id}
            new_state = _State(next_poi.lat, next_poi.lon, new_unvisited)

            if new_state in visited and visited[new_state] <= new_g:
                continue

            # Heuristic: MST on remaining unvisited + hotel
            remaining_nodes = [
                (poi_map[pid].lat, poi_map[pid].lon) for pid in new_unvisited
            ]
            remaining_nodes.append((hotel_lat, hotel_lon))
            # Include return from new_state to hotel
            h = _mst_cost(remaining_nodes)

            new_entry = _PQEntry(
                f=new_g + h,
                g=new_g,
                state=new_state,
                path=entry.path + [next_id],
            )
            heapq.heappush(open_set, new_entry)

    # Fallback: if A* exhausted (should not happen with correct h), return original order
    return list(pois)

def compute_day_travel_time(pois: list[POI], hotel: tuple[float, float]) -> float:
    """
    Compute total travel time (minutes) for an already-ordered list of POIs,
    starting and ending at the hotel.

    Args:
        pois: Ordered list of POIs for the day.
        hotel: (lat, lon) of the hotel.

    Returns:
        Total travel time in minutes.
    """
    if not pois:
        return 0.0

    total = 0.0
    prev_lat, prev_lon = hotel

    for poi in pois:
        total += travel_time_minutes(prev_lat, prev_lon, poi.lat, poi.lon, mode="transit")
        prev_lat, prev_lon = poi.lat, poi.lon

    # Return to hotel
    total += travel_time_minutes(prev_lat, prev_lon, hotel[0], hotel[1], mode="transit")
    return total
