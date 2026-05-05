"""
Custom Constraint Satisfaction Problem solver for itinerary planning.

CSP Formulation
---------------
Variables:  One variable X_i per candidate POI. Value = which day (1..num_days)
            to visit it, or None (excluded).

Domains:    D(X_i) = {1, 2, ..., num_days} restricted to days when POI i is
            actually open. Days that would bust the per-day budget or time limit
            even in isolation are pruned by AC-3 before search.

Constraints:
  c1 — Budget:       Σ cost(X_i = d) ≤ budget_usd  (global)
  c2 — Daily time:   Σ duration(X_i = d) + travel_time(d) ≤ daily_minutes
  c3 — Opening hrs:  POI i must be open on the weekday of day d
  c4 — Must-include: ∀ id in must_include, X_id ≠ None
  c5 — Uniqueness:   each POI assigned to at most one day (implicit in variable def)

Search strategy:
  - Backtracking with forward checking
  - MRV (Minimum Remaining Values) variable ordering: pick POI with fewest
    feasible days first (most constrained = fail early)
  - LCV (Least Constraining Value) value ordering: prefer the day assignment
    that removes the fewest options from remaining POIs
  - AC-3 arc-consistency as pre-processing to prune domains before search
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

from .config import ALLOWED_CATEGORIES, MAX_POIS_PER_DAY
from .data_loader import POI
from .preferences import UserPreferences
from .utils import travel_time_minutes, day_of_week


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class DayPlan:
    """An ordered list of POIs assigned to one day of the trip."""
    day: int
    pois: list[POI] = field(default_factory=list)
    total_cost_usd: float = 0.0
    total_minutes: float = 0.0


@dataclass
class InfeasibilityReport:
    """
    Structured explanation of why no feasible itinerary could be found.

    The UI should render this as a helpful suggestion, not a raw error.
    """
    constraint_violated: str   # c1 / c2 / c3 / c4
    message: str               # User-readable explanation
    suggestion: str            # Concrete remediation
    suggested_budget: Optional[float] = None
    suggested_days: Optional[int] = None


# ---------------------------------------------------------------------------
# CSP Solver
# ---------------------------------------------------------------------------

class CSPSolver:
    """
    Custom backtracking CSP solver with MRV, LCV, forward checking, and AC-3.

    Attributes:
        pois_by_day: POIs available per cluster-day from K-Means.
        preferences: User preferences (budget, pace, must_include, etc.).
        num_days: Number of trip days.
        hotel: Hotel (lat, lon) for travel-time estimation.
    """

    def __init__(
        self,
        pois_by_day: dict[int, list[POI]],
        preferences: UserPreferences,
        hotel: tuple[float, float],
    ) -> None:
        self.pois_by_day = pois_by_day
        self.prefs = preferences
        self.num_days = preferences.num_days
        self.hotel = hotel

        # Flatten all candidates; we'll assign each to a day
        self._all_pois: list[POI] = [p for lst in pois_by_day.values() for p in lst]
        # POI id → list of candidate days (pruned by AC-3)
        self._domains: dict[str, list[int]] = {}
        # POI id → POI object for fast lookup
        self._poi_map: dict[str, POI] = {p.id: p for p in self._all_pois}

        self._build_initial_domains()

    # -------------------------------------------------------------------
    # Domain initialisation
    # -------------------------------------------------------------------

    def _build_initial_domains(self) -> None:
        """
        Assign each POI a domain of feasible days based on opening hours.
        POIs originating from cluster d start with {d} but may be relaxed
        to adjacent days if the cluster is over-capacity.
        """
        for day, pois in self.pois_by_day.items():
            for poi in pois:
                feasible = []
                for d in range(1, self.num_days + 1):
                    dow = day_of_week(self.prefs.start_date, d - 1)
                    if poi.is_open_on(dow):
                        feasible.append(d)
                self._domains[poi.id] = feasible if feasible else [day]

    # -------------------------------------------------------------------
    # AC-3 Arc Consistency
    # -------------------------------------------------------------------

    def _ac3(self) -> bool:
        """
        Apply AC-3 (arc-consistency algorithm 3) to prune domains.

        For each (POI_i, day_d) pair, check whether assigning POI_i to day_d
        is locally consistent with the budget and time constraints. If no
        remaining POIs could ever be placed without violating c1 or c2, the
        arc is removed.

        Returns:
            False if any domain becomes empty (problem is immediately infeasible).
        """
        for poi_id, domain in list(self._domains.items()):
            poi = self._poi_map[poi_id]
            pruned = []
            for d in domain:
                # c1: even this POI alone must not exceed total budget
                if poi.avg_cost_usd > self.prefs.budget_usd:
                    continue  # skip this day for this POI
                # c2: single POI duration must fit inside a day
                if poi.avg_duration_minutes > self.prefs.daily_minutes:
                    continue
                pruned.append(d)
            self._domains[poi_id] = pruned
            if not pruned:
                # Only truly infeasible if a must_include POI has no valid day
                if poi_id in set(self.prefs.must_include):
                    return False
                # Optional POI: exclude it from the problem entirely
        return True

    # -------------------------------------------------------------------
    # Public solve entry point
    # -------------------------------------------------------------------

    def solve(self) -> tuple[Optional[dict[int, DayPlan]], Optional[InfeasibilityReport]]:
        """
        Run AC-3 then backtracking search.

        Returns:
            (assignment, None)        — feasible solution found
            (None, InfeasibilityReport) — no solution exists
        """
        # Pre-processing
        if not self._ac3():
            return None, self._build_infeasibility_report("c1", "Pre-processing")

        # Check must_include feasibility
        for poi_id in self.prefs.must_include:
            if poi_id not in self._domains or not self._domains[poi_id]:
                poi_name = self._poi_map.get(poi_id, None)
                name_str = poi_name.name if poi_name else poi_id
                return None, InfeasibilityReport(
                    constraint_violated="c4",
                    message=f"Must-include POI '{name_str}' has no feasible day "
                            f"(likely closed every day of your trip, or too expensive).",
                    suggestion="Remove this POI from must_include, adjust trip dates, or increase budget.",
                )

        # Build initial partial assignment (empty days)
        initial: dict[int, DayPlan] = {
            d: DayPlan(day=d) for d in range(1, self.num_days + 1)
        }

        # Sort POIs: must_include first, then by preference weight descending
        unassigned = sorted(
            list(self._all_pois),
            key=lambda p: (
                0 if p.id in self.prefs.must_include else 1,
                -self.prefs.interest_weights.get(p.category, 0.5),
            ),
        )

        result = self._backtrack(
            unassigned=unassigned,
            assignment=initial,
            domains=copy.deepcopy(self._domains),
        )

        if result is None:
            return None, self._build_infeasibility_report("c1/c2", "Backtracking")

        return result, None

    # -------------------------------------------------------------------
    # Backtracking
    # -------------------------------------------------------------------

    def _backtrack(
        self,
        unassigned: list[POI],
        assignment: dict[int, DayPlan],
        domains: dict[str, list[int]],
    ) -> Optional[dict[int, DayPlan]]:
        """
        Recursive backtracking search.

        Args:
            unassigned: POIs not yet placed (or excluded).
            assignment: Current partial day → DayPlan mapping.
            domains: Current domains (mutable, restored on backtrack).

        Returns:
            Complete assignment if found, else None.
        """
        if not unassigned:
            # All POIs processed — verify must_include are all placed
            placed_ids = {p.id for dp in assignment.values() for p in dp.pois}
            for must_id in self.prefs.must_include:
                if must_id not in placed_ids:
                    return None
            return assignment

        # MRV: pick POI with fewest remaining domain values
        poi = self._select_mrv(unassigned, domains)
        remaining = [p for p in unassigned if p.id != poi.id]

        # LCV: order day assignments by how little they constrain others
        ordered_days = self._order_days_lcv(poi, domains, assignment)

        # Try assigning poi to each day
        for day in ordered_days:
            if self._is_consistent(poi, day, assignment):
                # Assign
                assignment[day].pois.append(poi)
                assignment[day].total_cost_usd += poi.avg_cost_usd
                assignment[day].total_minutes += poi.avg_duration_minutes

                # Forward checking: prune domains of remaining POIs
                new_domains = copy.deepcopy(domains)
                new_domains[poi.id] = [day]
                fc_ok = self._forward_check(poi, day, remaining, new_domains, assignment)

                if fc_ok:
                    result = self._backtrack(remaining, assignment, new_domains)
                    if result is not None:
                        return result

                # Undo assignment
                assignment[day].pois.remove(poi)
                assignment[day].total_cost_usd -= poi.avg_cost_usd
                assignment[day].total_minutes -= poi.avg_duration_minutes

        # Try excluding this POI (if not must_include)
        if poi.id not in self.prefs.must_include:
            excl_domains = copy.deepcopy(domains)
            excl_domains[poi.id] = []
            return self._backtrack(remaining, assignment, excl_domains)

        return None

    # -------------------------------------------------------------------
    # MRV — variable ordering
    # -------------------------------------------------------------------

    def _select_mrv(self, unassigned: list[POI], domains: dict[str, list[int]]) -> POI:
        """
        Return the unassigned POI with the fewest remaining domain values
        (ties broken by highest user preference weight).
        """
        return min(
            unassigned,
            key=lambda p: (
                len(domains.get(p.id, [])),
                -self.prefs.interest_weights.get(p.category, 0.5),
            ),
        )

    # -------------------------------------------------------------------
    # LCV — value ordering
    # -------------------------------------------------------------------

    def _order_days_lcv(
        self,
        poi: POI,
        domains: dict[str, list[int]],
        assignment: dict[int, DayPlan],
    ) -> list[int]:
        """
        Order days in POI's domain by Least Constraining Value:
        prefer days that remove the fewest options from other POIs.
        """
        candidate_days = domains.get(poi.id, [])

        def constraint_count(day: int) -> int:
            # Count how many (other_poi, day) pairs would be blocked
            blocked = 0
            for other in self._all_pois:
                if other.id == poi.id:
                    continue
                if day in domains.get(other.id, []):
                    # Would assigning poi to this day block other from this day?
                    dp = assignment[day]
                    hypothetical_cost = dp.total_cost_usd + poi.avg_cost_usd + other.avg_cost_usd
                    hypothetical_time = dp.total_minutes + poi.avg_duration_minutes + other.avg_duration_minutes
                    if (
                        hypothetical_cost > self.prefs.budget_usd
                        or hypothetical_time > self.prefs.daily_minutes
                        or len(dp.pois) + 1 >= MAX_POIS_PER_DAY
                    ):
                        blocked += 1
            return blocked

        return sorted(candidate_days, key=constraint_count)

    # -------------------------------------------------------------------
    # Forward checking
    # -------------------------------------------------------------------

    def _forward_check(
        self,
        assigned_poi: POI,
        assigned_day: int,
        remaining: list[POI],
        domains: dict[str, list[int]],
        assignment: dict[int, DayPlan],
    ) -> bool:
        """
        After assigning assigned_poi to assigned_day, prune remaining domains.

        Returns False if any must_include POI's domain becomes empty.
        """
        dp = assignment[assigned_day]

        for poi in remaining:
            if assigned_day not in domains.get(poi.id, []):
                continue

            # Check if this day is still feasible for poi
            projected_cost = dp.total_cost_usd + poi.avg_cost_usd
            projected_time = dp.total_minutes + poi.avg_duration_minutes

            if (
                projected_cost > self.prefs.budget_usd
                or projected_time > self.prefs.daily_minutes
                or len(dp.pois) >= MAX_POIS_PER_DAY
            ):
                domains[poi.id].remove(assigned_day)

            if not domains[poi.id]:
                if poi.id in self.prefs.must_include:
                    return False  # must_include POI has no valid day
        return True

    # -------------------------------------------------------------------
    # Constraint check
    # -------------------------------------------------------------------

    def _is_consistent(
        self,
        poi: POI,
        day: int,
        assignment: dict[int, DayPlan],
    ) -> bool:
        """
        Return True if adding poi to day satisfies all hard constraints.
        """
        dp = assignment[day]

        # c1 — global budget
        total_spent = sum(d.total_cost_usd for d in assignment.values())
        if total_spent + poi.avg_cost_usd > self.prefs.budget_usd:
            return False

        # c2 — daily time
        if dp.total_minutes + poi.avg_duration_minutes > self.prefs.daily_minutes:
            return False

        # c2b — per-day POI cap (A* tractability)
        if len(dp.pois) >= MAX_POIS_PER_DAY:
            return False

        # c3 — opening hours
        dow = day_of_week(self.prefs.start_date, day - 1)
        if not poi.is_open_on(dow):
            return False

        # c5 — uniqueness (already guaranteed by variable formulation, but double-check)
        placed_ids = {p.id for d, plan in assignment.items() for p in plan.pois}
        if poi.id in placed_ids:
            return False

        return True

    # -------------------------------------------------------------------
    # Infeasibility reporting
    # -------------------------------------------------------------------

    def _build_infeasibility_report(
        self, constraint: str, phase: str
    ) -> InfeasibilityReport:
        """Generate a user-friendly infeasibility report with suggestions."""
        all_costs = sorted(
            p.avg_cost_usd
            for pois in self.pois_by_day.values()
            for p in pois
            if p.avg_cost_usd > 0
        )
        per_day_median = all_costs[len(all_costs) // 2] if all_costs else 20.0
        suggested_budget = round(per_day_median * self.prefs.num_days * 1.5, 0)
        suggested_days = self.prefs.num_days + 1

        return InfeasibilityReport(
            constraint_violated=constraint,
            message=(
                f"No feasible itinerary found for {self.prefs.num_days} days in "
                f"{self.prefs.destination} within ${self.prefs.budget_usd:.0f} "
                f"(detected in {phase} phase)."
            ),
            suggestion=(
                f"Try increasing your budget to at least ${suggested_budget:.0f}, "
                f"extending to {suggested_days} days, or relaxing must_include constraints."
            ),
            suggested_budget=suggested_budget,
            suggested_days=suggested_days,
        )
