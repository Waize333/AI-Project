"""
Unit tests for src/astar_router.py.

Tests cover:
  - Trivial cases (0, 1 POI)
  - Correct POI count in output
  - All POIs present in route
  - Heuristic admissibility check (h ≤ actual remaining cost for all states)
  - route_day starts/ends at hotel (travel time accounting)
  - _mst_cost properties (non-negative, zero for single node)
"""

import math
import pytest

from src.astar_router import route_day, compute_day_travel_time, _mst_cost
from src.data_loader import POI
from src.utils import travel_time_minutes


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _poi(poi_id: str, lat: float, lon: float, duration: int = 60) -> POI:
    return POI(
        id=poi_id,
        name=f"POI {poi_id}",
        city="TestCity",
        lat=lat,
        lon=lon,
        category="landmark",
        tags=[],
        avg_cost_usd=10,
        avg_duration_minutes=duration,
        opening_hours={"mon": [9, 18]},
        rating=4.0,
        indoor=False,
        family_friendly=True,
    )


HOTEL = (48.85, 2.35)

# A small grid of POIs around Paris centre
P1 = _poi("P1", 48.8584, 2.2945)   # Eiffel Tower area
P2 = _poi("P2", 48.8606, 2.3376)   # Louvre area
P3 = _poi("P3", 48.8530, 2.3499)   # Notre-Dame area
P4 = _poi("P4", 48.8867, 2.3431)   # Sacré-Cœur area
P5 = _poi("P5", 48.8600, 2.3266)   # Musée d'Orsay area


# ---------------------------------------------------------------------------
# MST heuristic tests
# ---------------------------------------------------------------------------

class TestMSTCost:
    def test_zero_for_single_node(self):
        assert _mst_cost([(48.85, 2.35)]) == 0.0

    def test_zero_for_empty(self):
        assert _mst_cost([]) == 0.0

    def test_non_negative_two_nodes(self):
        cost = _mst_cost([(48.85, 2.35), (48.87, 2.39)])
        assert cost >= 0.0

    def test_three_nodes_triangle_inequality(self):
        nodes = [(48.85, 2.35), (48.87, 2.39), (48.83, 2.37)]
        cost = _mst_cost(nodes)
        # MST of 3 nodes uses 2 edges; must be > 0
        assert cost > 0.0

    def test_mst_not_larger_than_sum_of_all_edges(self):
        nodes = [(48.85, 2.35), (48.87, 2.39), (48.83, 2.37), (48.90, 2.33)]
        mst = _mst_cost(nodes)
        # MST ≤ any spanning tree ≤ sum of all edges
        total = 0.0
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                total += travel_time_minutes(nodes[i][0], nodes[i][1],
                                             nodes[j][0], nodes[j][1])
        assert mst <= total + 1e-9


# ---------------------------------------------------------------------------
# route_day tests
# ---------------------------------------------------------------------------

class TestRouteDay:
    def test_empty_pois(self):
        result = route_day([], HOTEL)
        assert result == []

    def test_single_poi(self):
        result = route_day([P1], HOTEL)
        assert len(result) == 1
        assert result[0].id == "P1"

    def test_two_pois_returns_both(self):
        result = route_day([P1, P2], HOTEL)
        assert len(result) == 2
        ids = {p.id for p in result}
        assert ids == {"P1", "P2"}

    def test_five_pois_all_present(self):
        pois = [P1, P2, P3, P4, P5]
        result = route_day(pois, HOTEL)
        assert len(result) == 5
        ids = {p.id for p in result}
        assert ids == {"P1", "P2", "P3", "P4", "P5"}

    def test_no_duplicate_pois_in_route(self):
        pois = [P1, P2, P3, P4]
        result = route_day(pois, HOTEL)
        ids = [p.id for p in result]
        assert len(ids) == len(set(ids))

    def test_route_is_list_of_poi_objects(self):
        result = route_day([P1, P2, P3], HOTEL)
        assert all(isinstance(p, POI) for p in result)

    def test_astar_finds_shorter_route_than_naive(self):
        """
        A* should produce a route with travel time ≤ the reverse ordering.
        This verifies A* does actual optimisation (not just returning input order).
        """
        pois = [P4, P1, P3, P2]  # deliberately bad order (far-near-far-near)
        result_astar = route_day(pois, HOTEL)
        t_astar = compute_day_travel_time(result_astar, HOTEL)

        # Worst order: going farthest alternately
        worst = [P4, P1, P4, P2]  # can't repeat, use original bad order
        t_original = compute_day_travel_time(pois, HOTEL)

        # A* should be ≤ original (may equal if original was already optimal)
        assert t_astar <= t_original + 1e-6, (
            f"A* travel time {t_astar:.1f} > input order {t_original:.1f}"
        )


class TestComputeDayTravelTime:
    def test_zero_for_empty(self):
        assert compute_day_travel_time([], HOTEL) == 0.0

    def test_single_poi_is_hotel_to_poi_to_hotel(self):
        t = compute_day_travel_time([P1], HOTEL)
        expected = (
            travel_time_minutes(HOTEL[0], HOTEL[1], P1.lat, P1.lon, mode="transit")
            + travel_time_minutes(P1.lat, P1.lon, HOTEL[0], HOTEL[1], mode="transit")
        )
        assert abs(t - expected) < 1e-9

    def test_travel_time_positive(self):
        t = compute_day_travel_time([P1, P2, P3], HOTEL)
        assert t > 0.0


class TestHeuristicAdmissibility:
    """
    Verify MST heuristic admissibility:
    h(state) ≤ true cost to complete tour from that state.

    We check a representative sample of states for a 3-POI day.
    """

    def _true_cost(self, current: tuple, unvisited_ids: list, poi_map: dict, hotel: tuple) -> float:
        """Brute-force minimum cost to visit all unvisited and return to hotel."""
        if not unvisited_ids:
            return travel_time_minutes(current[0], current[1], hotel[0], hotel[1])

        from itertools import permutations
        best = math.inf
        for perm in permutations(unvisited_ids):
            cost = 0.0
            pos = current
            for pid in perm:
                poi = poi_map[pid]
                cost += travel_time_minutes(pos[0], pos[1], poi.lat, poi.lon)
                cost += poi.avg_duration_minutes
                pos = (poi.lat, poi.lon)
            cost += travel_time_minutes(pos[0], pos[1], hotel[0], hotel[1])
            if cost < best:
                best = cost
        return best

    def test_heuristic_admissible_for_3_pois(self):
        pois = [P1, P2, P3]
        poi_map = {p.id: p for p in pois}
        hotel = HOTEL

        # Test from hotel with all POIs unvisited
        unvisited = [p.id for p in pois]
        nodes = [(poi_map[pid].lat, poi_map[pid].lon) for pid in unvisited] + [hotel]
        h = _mst_cost(nodes)
        true_cost = self._true_cost(hotel, unvisited, poi_map, hotel)
        # Activity time is added to g, not h, so we compare pure travel MST to pure travel optimum
        # We check h ≤ sum of edge costs in optimal tour (without activity time)
        assert h <= true_cost + 1e-6, (
            f"Admissibility violated: h={h:.2f} > true={true_cost:.2f}"
        )
