"""
User preference model and validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal, Optional

from .config import (
    ALLOWED_CATEGORIES,
    ALLOWED_TRAVELER_TYPES,
    ALLOWED_PACE_VALUES,
    PACE_HOURS,
)

TravelerType = Literal["solo", "couple", "family", "friends"]
PaceType = Literal["relaxed", "balanced", "packed"]


@dataclass
class UserPreferences:
    """
    Encapsulates all user-provided constraints and preferences for a trip.

    Attributes:
        destination: City name matching a JSON file in data/cities/.
        num_days: Trip length in days (1–14).
        budget_usd: Total budget across all days in US dollars.
        traveler_type: Affects family-friendliness filtering.
        interest_weights: Weight in [0, 1] per allowed category. A weight of 0
            means the user has no interest — those POIs are dropped by clustering.
        pace: Maps to daily activity hours: relaxed=6h, balanced=8h, packed=10h.
        must_include: List of POI IDs that must appear in the itinerary.
        must_avoid_categories: Categories excluded from consideration entirely.
        start_date: Calendar start date, used to resolve weekday opening hours.
        hotel_location: (lat, lon) of the hotel; defaults to city centroid if None.
    """

    destination: str
    num_days: int
    budget_usd: float
    traveler_type: TravelerType
    interest_weights: dict[str, float]
    pace: PaceType
    must_include: list[str] = field(default_factory=list)
    must_avoid_categories: list[str] = field(default_factory=list)
    start_date: date = field(default_factory=date.today)
    hotel_location: Optional[tuple[float, float]] = None

    # ------- derived properties -------

    @property
    def daily_budget_usd(self) -> float:
        """Per-day budget (evenly split)."""
        return self.budget_usd / self.num_days

    @property
    def daily_minutes(self) -> float:
        """Maximum activity minutes per day based on pace."""
        return PACE_HOURS[self.pace] * 60.0

    # ------- validation -------

    def validate(self) -> None:
        """
        Raise ValueError with a user-friendly message for any infeasible input.

        Checks:
        - num_days in [1, 14]
        - budget_usd > 0
        - traveler_type and pace are known values
        - interest_weights keys are allowed categories with values in [0, 1]
        - must_avoid_categories are valid categories
        - must_include is a list of strings
        """
        if not 1 <= self.num_days <= 14:
            raise ValueError(f"Number of days must be between 1 and 14, got {self.num_days}.")

        if self.budget_usd <= 0:
            raise ValueError("Budget must be positive.")

        if self.traveler_type not in ALLOWED_TRAVELER_TYPES:
            raise ValueError(
                f"Traveler type '{self.traveler_type}' is not valid. "
                f"Choose from: {ALLOWED_TRAVELER_TYPES}."
            )

        if self.pace not in ALLOWED_PACE_VALUES:
            raise ValueError(
                f"Pace '{self.pace}' is not valid. "
                f"Choose from: {ALLOWED_PACE_VALUES}."
            )

        for category, weight in self.interest_weights.items():
            if category not in ALLOWED_CATEGORIES:
                raise ValueError(
                    f"Unknown category '{category}' in interest_weights. "
                    f"Allowed: {ALLOWED_CATEGORIES}."
                )
            if not 0.0 <= weight <= 1.0:
                raise ValueError(
                    f"Weight for '{category}' must be in [0, 1], got {weight}."
                )

        for cat in self.must_avoid_categories:
            if cat not in ALLOWED_CATEGORIES:
                raise ValueError(
                    f"Unknown category '{cat}' in must_avoid_categories. "
                    f"Allowed: {ALLOWED_CATEGORIES}."
                )

        if not isinstance(self.must_include, list):
            raise ValueError("must_include must be a list of POI ID strings.")

    @classmethod
    def default_weights(cls) -> dict[str, float]:
        """Return equal interest weights across all categories."""
        return {cat: 0.5 for cat in ALLOWED_CATEGORIES}
