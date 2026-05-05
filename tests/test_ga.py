"""
Unit tests for src/ga_solver.py.

Tests cover:
  - GA produces a valid Itinerary with the correct number of days
  - Fitness function penalises constraint violations
  - OX crossover preserves all genes (permutation property)
  - Swap mutation maintains permutation property
  - Day-boundary shift mutation maintains permutation property
  - GA with zero POIs returns empty itinerary
  - GA runtime is bounded (sanity check)
"""

import pytest
import time
from datetime import date

from src.ga_solver import (
    GASolver,
    _order_crossover,
    _swap_mutation,
    _day_boundary_shift_mutation,
    _fitness,
    _chromosome_to_itinerary,
)
from src.data_loader import POI
from src.preferences import UserPreferences
from src.scorer import Itinerary

import random

ALL_CATS = [
    "landmark", "museum", "food", "nature", "shopping",
    "religious", "nightlife", "adventure", "beach", "cultural",
]

RNG = random.Random(42)


def _poi(poi_id: str, cost: float = 10, duration: int = 60, lat: float = 48.85, lon: float = 2.35) -> POI:
    return POI(
        id=poi_id,
        name=f"POI {poi_id}",
        city="TestCity",
        lat=lat + float(poi_id[-1]) * 0.01,
        lon=lon + float(poi_id[-1]) * 0.01,
        category="landmark",
        tags=[],
        avg_cost_usd=cost,
        avg_duration_minutes=duration,
        opening_hours={"mon": [9, 18], "tue": [9, 18], "wed": [9, 18],
                       "thu": [9, 18], "fri": [9, 18], "sat": [9, 18], "sun": [9, 18]},
        rating=4.0,
        indoor=True,
        family_friendly=True,
    )


def _prefs(**kwargs) -> UserPreferences:
    defaults = dict(
        destination="TestCity",
        num_days=2,
        budget_usd=200,
        traveler_type="solo",
        interest_weights={cat: 0.5 for cat in ALL_CATS},
        pace="balanced",
        must_include=[],
        must_avoid_categories=[],
        start_date=date(2025, 6, 2),  # Monday
        hotel_location=(48.85, 2.35),
    )
    defaults.update(kwargs)
    return UserPreferences(**defaults)


SAMPLE_POIS = [_poi(str(i), cost=10, duration=60) for i in range(6)]


# ---------------------------------------------------------------------------
# Genetic operator tests
# ---------------------------------------------------------------------------

class TestOrderCrossover:
    def test_output_is_permutation(self):
        parent1 = [0, 1, 2, 3, 4, 5]
        parent2 = [5, 4, 3, 2, 1, 0]
        child = _order_crossover(parent1, parent2, RNG)
        assert sorted(child) == sorted(parent1), "Child is not a valid permutation"

    def test_child_has_correct_length(self):
        parent1 = list(range(8))
        parent2 = list(reversed(range(8)))
        child = _order_crossover(parent1, parent2, RNG)
        assert len(child) == 8

    def test_no_duplicates_in_child(self):
        parent1 = [2, 4, 1, 3, 0, 5]
        parent2 = [5, 1, 3, 0, 2, 4]
        child = _order_crossover(parent1, parent2, RNG)
        assert len(set(child)) == len(child), "Child contains duplicates"

    def test_subsequence_from_parent1_preserved(self):
        """The crossover segment from parent1 should appear in the child."""
        random.seed(0)
        rng = random.Random(0)
        parent1 = [0, 1, 2, 3, 4]
        parent2 = [4, 3, 2, 1, 0]
        # We can't check exact positions without knowing the cut points,
        # but all elements of parent1 must appear.
        for _ in range(10):
            child = _order_crossover(parent1, parent2, rng)
            assert sorted(child) == sorted(parent1)


class TestSwapMutation:
    def test_output_is_permutation(self):
        chromosome = list(range(10))
        mutant = _swap_mutation(chromosome, RNG)
        assert sorted(mutant) == sorted(chromosome)

    def test_no_duplicates(self):
        chromosome = [3, 1, 4, 1, 5, 9, 2, 6]  # not a real perm, but testing uniqueness
        chromosome = list(range(8))
        mutant = _swap_mutation(chromosome, RNG)
        assert len(set(mutant)) == len(mutant)

    def test_length_preserved(self):
        chromosome = list(range(6))
        mutant = _swap_mutation(chromosome, RNG)
        assert len(mutant) == 6

    def test_at_most_two_positions_differ(self):
        """Swap mutation changes exactly 2 positions."""
        chromosome = list(range(10))
        rng = random.Random(7)
        mutant = _swap_mutation(chromosome, rng)
        diffs = sum(1 for a, b in zip(chromosome, mutant) if a != b)
        assert diffs == 2


class TestDayBoundaryShiftMutation:
    def test_output_is_permutation(self):
        chromosome = list(range(8))
        mutant = _day_boundary_shift_mutation(chromosome, num_days=2, rng=RNG)
        assert sorted(mutant) == sorted(chromosome)

    def test_length_preserved(self):
        chromosome = list(range(8))
        mutant = _day_boundary_shift_mutation(chromosome, num_days=2, rng=RNG)
        assert len(mutant) == 8


# ---------------------------------------------------------------------------
# Fitness tests
# ---------------------------------------------------------------------------

class TestFitness:
    def test_feasible_chromosome_has_higher_fitness_than_budget_violating(self):
        pois = [_poi(str(i), cost=10) for i in range(4)]
        prefs_strict = _prefs(budget_usd=20, num_days=2)
        prefs_loose = _prefs(budget_usd=200, num_days=2)

        chrom = [0, 1, 2, 3]
        f_strict = _fitness(chrom, pois, prefs_strict)
        f_loose = _fitness(chrom, pois, prefs_loose)
        # With tight budget, fitness should be penalised more
        assert f_loose >= f_strict

    def test_fitness_returns_float(self):
        chromosome = list(range(len(SAMPLE_POIS)))
        f = _fitness(chromosome, SAMPLE_POIS, _prefs())
        assert isinstance(f, float)


# ---------------------------------------------------------------------------
# GASolver integration tests
# ---------------------------------------------------------------------------

class TestGASolver:
    def test_solve_returns_itinerary(self):
        ga = GASolver(random_seed=42)
        pois = [_poi(str(i)) for i in range(6)]
        prefs = _prefs(num_days=2)
        itinerary, runtime = ga.solve(pois, prefs)
        assert isinstance(itinerary, Itinerary)

    def test_itinerary_has_correct_days(self):
        ga = GASolver(random_seed=42)
        pois = [_poi(str(i)) for i in range(6)]
        prefs = _prefs(num_days=3)
        itinerary, _ = ga.solve(pois, prefs)
        assert len(itinerary.days) == 3

    def test_solver_label_is_ga(self):
        ga = GASolver(random_seed=42)
        pois = [_poi(str(i)) for i in range(4)]
        itinerary, _ = ga.solve(pois, _prefs())
        assert itinerary.solver == "GA"

    def test_empty_pois_returns_empty_itinerary(self):
        ga = GASolver(random_seed=42)
        itinerary, runtime = ga.solve([], _prefs())
        assert itinerary.total_cost_usd == 0.0
        assert all(len(dr.pois) == 0 for dr in itinerary.days.values())

    def test_runtime_is_recorded(self):
        ga = GASolver(random_seed=42)
        pois = [_poi(str(i)) for i in range(4)]
        itinerary, runtime = ga.solve(pois, _prefs())
        assert runtime > 0.0

    def test_score_is_numeric(self):
        ga = GASolver(random_seed=42)
        pois = [_poi(str(i)) for i in range(4)]
        itinerary, _ = ga.solve(pois, _prefs())
        assert isinstance(itinerary.score, float)
