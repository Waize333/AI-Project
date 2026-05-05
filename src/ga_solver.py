"""
Genetic Algorithm solver for itinerary planning (comparison baseline).

Algorithm design
----------------
Chromosome: A permutation of POI indices [0, 1, ..., n-1].
            The permutation is split into num_days segments of approximately
            equal size to determine day assignments. Visit order within each
            day is taken as the chromosome order (no A* routing for speed).

Fitness:    Itinerary score from scorer.py, with heavy penalties for
            constraint violations (budget, time, must_include misses).
            A feasible CSP solution always dominates any GA solution that
            violates constraints, so the GA serves as a comparison baseline.

Operators:
  Selection:  Tournament selection (size 3) — balances exploration/exploitation.
  Crossover:  Order Crossover (OX) — preserves relative ordering of elements,
              critical for permutation-based chromosomes.
  Mutation:   Swap mutation (random pair swap) + day-boundary shift (shift
              where one segment ends/begins).

Parameters (from spec):
  Population: 100, Generations: 200, Crossover rate: 0.8, Mutation rate: 0.15.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Optional

from .config import (
    GA_CROSSOVER_RATE,
    GA_MUTATION_RATE,
    GA_NUM_GENERATIONS,
    GA_POPULATION_SIZE,
    GA_TOURNAMENT_SIZE,
    MAX_POIS_PER_DAY,
    RANDOM_SEED,
)
from .data_loader import POI
from .preferences import UserPreferences
from .scorer import (
    DayRoute,
    Itinerary,
    preference_match,
    score_itinerary,
    _ALPHA,
    _BETA,
    _GAMMA,
)
from .utils import travel_time_minutes, day_of_week


# ---------------------------------------------------------------------------
# Chromosome helpers
# ---------------------------------------------------------------------------

def _split_chromosome(
    chromosome: list[int],
    num_days: int,
    all_pois: list[POI],
) -> dict[int, list[POI]]:
    """
    Split a permutation chromosome into num_days segments.

    Segment boundaries are approximately equal-size splits, which allows the
    GA to explore different day-group sizes through day-boundary shift mutation.
    """
    n = len(chromosome)
    segment_size = max(1, n // num_days)
    day_pois: dict[int, list[POI]] = {}

    for d in range(1, num_days + 1):
        start = (d - 1) * segment_size
        end = d * segment_size if d < num_days else n
        day_pois[d] = [all_pois[i] for i in chromosome[start:end]][:MAX_POIS_PER_DAY]

    return day_pois


def _chromosome_to_itinerary(
    chromosome: list[int],
    all_pois: list[POI],
    prefs: UserPreferences,
) -> Itinerary:
    """Decode a chromosome into an Itinerary object."""
    day_assignment = _split_chromosome(chromosome, prefs.num_days, all_pois)

    days: dict[int, DayRoute] = {}
    total_cost = 0.0
    total_travel = 0.0

    hotel = prefs.hotel_location or (0.0, 0.0)

    for d, pois in day_assignment.items():
        cost = sum(p.avg_cost_usd for p in pois)
        activity = sum(p.avg_duration_minutes for p in pois)

        # Estimate travel time (linear chain from hotel)
        travel = 0.0
        prev = hotel
        for poi in pois:
            travel += travel_time_minutes(prev[0], prev[1], poi.lat, poi.lon, mode="transit")
            prev = (poi.lat, poi.lon)
        if pois:
            travel += travel_time_minutes(prev[0], prev[1], hotel[0], hotel[1], mode="transit")

        days[d] = DayRoute(
            day=d,
            pois=pois,
            total_cost_usd=cost,
            total_activity_minutes=activity,
            total_travel_minutes=travel,
        )
        total_cost += cost
        total_travel += travel

    itinerary = Itinerary(
        destination=prefs.destination,
        days=days,
        total_cost_usd=total_cost,
        total_travel_minutes=total_travel,
        score=0.0,
        solver="GA",
    )
    itinerary.score = score_itinerary(itinerary, prefs, _ALPHA, _BETA, _GAMMA)
    return itinerary


# ---------------------------------------------------------------------------
# Fitness
# ---------------------------------------------------------------------------

def _fitness(
    chromosome: list[int],
    all_pois: list[POI],
    prefs: UserPreferences,
) -> float:
    """
    Fitness = itinerary score − hard constraint violation penalties.

    Violations are penalised heavily so infeasible solutions lose to any
    feasible solution, enabling constraint-satisfaction comparison with CSP.
    """
    day_assignment = _split_chromosome(chromosome, prefs.num_days, all_pois)
    hotel = prefs.hotel_location or (0.0, 0.0)

    itinerary = _chromosome_to_itinerary(chromosome, all_pois, prefs)
    score = itinerary.score

    # Penalty: budget overshoot
    if itinerary.total_cost_usd > prefs.budget_usd:
        score -= 50.0 * (itinerary.total_cost_usd - prefs.budget_usd) / max(prefs.budget_usd, 1)

    # Penalty: daily time overshoot
    for day_route in itinerary.days.values():
        if day_route.total_activity_minutes > prefs.daily_minutes:
            score -= 20.0 * (day_route.total_activity_minutes - prefs.daily_minutes) / 60.0

    # Penalty: must_include POIs not appearing
    placed_ids = {p.id for dr in itinerary.days.values() for p in dr.pois}
    for must_id in prefs.must_include:
        if must_id not in placed_ids:
            score -= 100.0

    # Penalty: opening hours violation
    for d, day_route in itinerary.days.items():
        dow = day_of_week(prefs.start_date, d - 1)
        for poi in day_route.pois:
            if not poi.is_open_on(dow):
                score -= 30.0

    return score


# ---------------------------------------------------------------------------
# Genetic operators
# ---------------------------------------------------------------------------

def _tournament_selection(
    population: list[list[int]],
    fitnesses: list[float],
    rng: random.Random,
) -> list[int]:
    """Tournament selection: sample GA_TOURNAMENT_SIZE individuals, return best."""
    candidates = rng.sample(range(len(population)), k=GA_TOURNAMENT_SIZE)
    winner = max(candidates, key=lambda i: fitnesses[i])
    return list(population[winner])


def _order_crossover(parent1: list[int], parent2: list[int], rng: random.Random) -> list[int]:
    """
    Order Crossover (OX):
    1. Select a random subsequence from parent1.
    2. Fill remaining positions in parent2's order (skipping already-placed genes).

    OX preserves relative ordering from both parents, which is critical for
    permutation chromosomes where absolute position matters less than order.
    """
    n = len(parent1)
    a, b = sorted(rng.sample(range(n), 2))

    child = [None] * n
    child[a:b+1] = parent1[a:b+1]

    fill = [gene for gene in parent2 if gene not in child[a:b+1]]
    pos = 0
    for i in range(n):
        if child[i] is None:
            child[i] = fill[pos]
            pos += 1

    return child


def _swap_mutation(chromosome: list[int], rng: random.Random) -> list[int]:
    """Randomly swap two genes (positions) in the chromosome."""
    c = list(chromosome)
    i, j = rng.sample(range(len(c)), 2)
    c[i], c[j] = c[j], c[i]
    return c


def _day_boundary_shift_mutation(
    chromosome: list[int],
    num_days: int,
    rng: random.Random,
) -> list[int]:
    """
    Shift a gene from one day segment to an adjacent segment.
    This explores different day-boundary configurations that pure swap mutation
    cannot reach efficiently.
    """
    n = len(chromosome)
    segment_size = max(1, n // num_days)

    # Pick a boundary between two adjacent segments
    boundary_options = [
        segment_size * d for d in range(1, num_days) if segment_size * d < n
    ]
    if not boundary_options:
        return _swap_mutation(chromosome, rng)

    boundary = rng.choice(boundary_options)
    c = list(chromosome)

    # Move the element just before the boundary to just after it (or vice versa)
    if boundary < n - 1 and rng.random() < 0.5:
        c.insert(boundary + 1, c.pop(boundary - 1))
    elif boundary > 0:
        c.insert(boundary - 1, c.pop(boundary))

    return c


# ---------------------------------------------------------------------------
# GA Solver class
# ---------------------------------------------------------------------------

class GASolver:
    """
    Genetic Algorithm solver for the travel itinerary problem.

    Exposes the same interface as CSPSolver for benchmarking.
    """

    def __init__(self, random_seed: int = RANDOM_SEED) -> None:
        self._rng = random.Random(random_seed)

    def solve(
        self,
        pois: list[POI],
        preferences: UserPreferences,
    ) -> tuple[Itinerary, float]:
        """
        Run the GA and return the best itinerary found.

        Args:
            pois: All candidate POIs (pre-filtered by clustering/CSP stage).
            preferences: User preferences.

        Returns:
            (best_itinerary, runtime_seconds)
        """
        start_time = time.time()

        n = len(pois)
        if n == 0:
            empty = Itinerary(
                destination=preferences.destination,
                days={d: DayRoute(day=d) for d in range(1, preferences.num_days + 1)},
                total_cost_usd=0.0,
                total_travel_minutes=0.0,
                score=0.0,
                solver="GA",
            )
            return empty, 0.0

        # Initialise population: random permutations of [0..n-1]
        population = [
            self._rng.sample(range(n), n)
            for _ in range(GA_POPULATION_SIZE)
        ]

        fitnesses = [_fitness(c, pois, preferences) for c in population]
        best_idx = max(range(len(population)), key=lambda i: fitnesses[i])
        best_chromosome = list(population[best_idx])
        best_fitness = fitnesses[best_idx]

        for generation in range(GA_NUM_GENERATIONS):
            new_population = []

            # Elitism: carry forward the best individual unchanged
            new_population.append(list(best_chromosome))

            while len(new_population) < GA_POPULATION_SIZE:
                parent1 = _tournament_selection(population, fitnesses, self._rng)
                parent2 = _tournament_selection(population, fitnesses, self._rng)

                # Crossover
                if self._rng.random() < GA_CROSSOVER_RATE:
                    child = _order_crossover(parent1, parent2, self._rng)
                else:
                    child = list(parent1)

                # Mutation
                if self._rng.random() < GA_MUTATION_RATE:
                    if self._rng.random() < 0.5:
                        child = _swap_mutation(child, self._rng)
                    else:
                        child = _day_boundary_shift_mutation(child, preferences.num_days, self._rng)

                new_population.append(child)

            population = new_population
            fitnesses = [_fitness(c, pois, preferences) for c in population]

            gen_best_idx = max(range(len(population)), key=lambda i: fitnesses[i])
            if fitnesses[gen_best_idx] > best_fitness:
                best_fitness = fitnesses[gen_best_idx]
                best_chromosome = list(population[gen_best_idx])

        runtime = time.time() - start_time
        best_itinerary = _chromosome_to_itinerary(best_chromosome, pois, preferences)
        best_itinerary.solver = "GA"
        best_itinerary.runtime_seconds = runtime

        return best_itinerary, runtime
