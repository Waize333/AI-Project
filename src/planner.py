"""
Planner orchestrator: end-to-end pipeline from preferences to Itinerary.

Pipeline:
  1. Load city POI data
  2. Validate preferences
  3. K-Means clustering → day-partitioned POI sets
  4. CSP solving → daily POI assignments respecting all constraints
  5. A* routing → optimal visit order within each day
  6. Itinerary construction and scoring

The Streamlit UI never calls solvers directly — it goes through this module.
"""

from __future__ import annotations

import time
from typing import Optional

from .astar_router import route_day, compute_day_travel_time
from .clustering import cluster_pois_by_day, get_city_center
from .csp_solver import CSPSolver, DayPlan, InfeasibilityReport
from .data_loader import load_city, POI
from .ga_solver import GASolver
from .preferences import UserPreferences
from .scorer import (
    DayRoute,
    Itinerary,
    score_with_trained_coefficients,
    _ALPHA,
    _BETA,
    _GAMMA,
)


# ---------------------------------------------------------------------------
# CSP + A* pipeline
# ---------------------------------------------------------------------------

def plan_csp_astar(
    preferences: UserPreferences,
) -> tuple[Optional[Itinerary], Optional[InfeasibilityReport]]:
    """
    Full CSP + A* pipeline.

    Args:
        preferences: Validated user preferences.

    Returns:
        (itinerary, None)           — success
        (None, InfeasibilityReport) — infeasible problem; report contains suggestions
    """
    start_time = time.time()

    # 1. Load data
    pois = load_city(preferences.destination)

    # 2. Set hotel to city centre if not provided
    if preferences.hotel_location is None:
        preferences.hotel_location = get_city_center(pois)

    hotel = preferences.hotel_location

    # 3. Cluster POIs into day groups
    pois_by_day = cluster_pois_by_day(pois, preferences.num_days, preferences)

    # 4. CSP solving
    solver = CSPSolver(pois_by_day, preferences, hotel)
    day_plans, infeasibility = solver.solve()

    if infeasibility is not None:
        return None, infeasibility

    assert day_plans is not None

    # 5. A* routing for each day
    days: dict[int, DayRoute] = {}
    total_cost = 0.0
    total_travel = 0.0

    for day_num, day_plan in day_plans.items():
        if not day_plan.pois:
            days[day_num] = DayRoute(day=day_num)
            continue

        ordered_pois = route_day(day_plan.pois, hotel)
        travel_time = compute_day_travel_time(ordered_pois, hotel)
        cost = sum(p.avg_cost_usd for p in ordered_pois)
        activity = sum(p.avg_duration_minutes for p in ordered_pois)

        days[day_num] = DayRoute(
            day=day_num,
            pois=ordered_pois,
            total_cost_usd=cost,
            total_activity_minutes=activity,
            total_travel_minutes=travel_time,
        )
        total_cost += cost
        total_travel += travel_time

    runtime = time.time() - start_time

    itinerary = Itinerary(
        destination=preferences.destination,
        days=days,
        total_cost_usd=total_cost,
        total_travel_minutes=total_travel,
        score=0.0,
        solver="CSP+A*",
        runtime_seconds=runtime,
    )
    itinerary.score = score_with_trained_coefficients(itinerary, preferences)

    return itinerary, None


# ---------------------------------------------------------------------------
# GA pipeline
# ---------------------------------------------------------------------------

def plan_ga(
    preferences: UserPreferences,
) -> tuple[Itinerary, float]:
    """
    Full Genetic Algorithm pipeline.

    Args:
        preferences: Validated user preferences.

    Returns:
        (itinerary, runtime_seconds)
    """
    pois = load_city(preferences.destination)

    if preferences.hotel_location is None:
        preferences.hotel_location = get_city_center(pois)

    # Pre-filter same as clustering (for fair comparison)
    filtered = [
        p for p in pois
        if p.category not in preferences.must_avoid_categories
        and preferences.interest_weights.get(p.category, 0.5) > 0.0
    ]

    ga = GASolver()
    return ga.solve(filtered, preferences)


# ---------------------------------------------------------------------------
# Combined pipeline (for comparison view)
# ---------------------------------------------------------------------------

def plan_both(
    preferences: UserPreferences,
) -> dict[str, Optional[Itinerary | InfeasibilityReport]]:
    """
    Run both CSP+A* and GA and return results for side-by-side comparison.

    Returns:
        Dict with keys 'csp' and 'ga', each holding an Itinerary or error info.
    """
    csp_result, infeasibility = plan_csp_astar(preferences)
    ga_result, _ = plan_ga(preferences)

    return {
        "csp": csp_result,
        "csp_error": infeasibility,
        "ga": ga_result,
    }
