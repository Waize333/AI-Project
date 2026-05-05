"""
POI data loading, schema validation, and the POI dataclass.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .config import ALLOWED_CATEGORIES, DATA_DIR, DAY_ABBREVIATIONS


@dataclass
class POI:
    """
    A single Point of Interest.

    All fields correspond directly to the JSON schema documented in data/schema.md.
    Use load_city() to construct validated instances from disk.
    """

    id: str
    name: str
    city: str
    lat: float
    lon: float
    category: str
    tags: list[str]
    avg_cost_usd: float
    avg_duration_minutes: int
    opening_hours: dict[str, list[int]]  # e.g. {"mon": [9, 22]}
    rating: float
    indoor: bool
    family_friendly: bool

    def is_open_on(self, day_abbr: str) -> bool:
        """
        Return True if the POI is open on the given weekday.

        Args:
            day_abbr: Three-letter abbreviation, e.g. 'mon', 'sat'.
        """
        return day_abbr in self.opening_hours

    def open_window(self, day_abbr: str) -> Optional[tuple[int, int]]:
        """
        Return (open_hour, close_hour) for the given day, or None if closed.
        """
        hours = self.opening_hours.get(day_abbr)
        if hours is None:
            return None
        return (hours[0], hours[1])


def _validate_poi_dict(data: dict, source: str) -> None:
    """
    Raise ValueError if a raw POI dictionary violates the schema.

    Args:
        data: The raw dictionary loaded from JSON.
        source: File path string for error messages.
    """
    required_str_fields = ["id", "name", "city"]
    required_float_fields = ["lat", "lon", "avg_cost_usd", "rating"]
    required_int_fields = ["avg_duration_minutes"]
    required_bool_fields = ["indoor", "family_friendly"]

    for f in required_str_fields:
        if f not in data or not isinstance(data[f], str):
            raise ValueError(f"[{source}] Missing or invalid string field '{f}'.")

    for f in required_float_fields:
        if f not in data or not isinstance(data[f], (int, float)):
            raise ValueError(f"[{source}] Missing or invalid numeric field '{f}'.")

    for f in required_int_fields:
        if f not in data or not isinstance(data[f], int):
            raise ValueError(f"[{source}] Missing or invalid integer field '{f}'.")

    for f in required_bool_fields:
        if f not in data or not isinstance(data[f], bool):
            raise ValueError(f"[{source}] Missing or invalid boolean field '{f}'.")

    if data.get("category") not in ALLOWED_CATEGORIES:
        raise ValueError(
            f"[{source}] POI '{data.get('id')}' has unknown category '{data.get('category')}'. "
            f"Allowed: {ALLOWED_CATEGORIES}."
        )

    if not isinstance(data.get("tags"), list):
        raise ValueError(f"[{source}] 'tags' must be a list.")

    hours = data.get("opening_hours", {})
    if not isinstance(hours, dict):
        raise ValueError(f"[{source}] 'opening_hours' must be a dict.")
    for day, window in hours.items():
        if day not in DAY_ABBREVIATIONS:
            raise ValueError(f"[{source}] Unknown day key '{day}' in opening_hours.")
        if (
            not isinstance(window, list)
            or len(window) != 2
            or not all(isinstance(v, int) for v in window)
        ):
            raise ValueError(
                f"[{source}] opening_hours['{day}'] must be [open_hour, close_hour]."
            )

    if not (-90 <= data["lat"] <= 90):
        raise ValueError(f"[{source}] Latitude {data['lat']} out of range.")
    if not (-180 <= data["lon"] <= 180):
        raise ValueError(f"[{source}] Longitude {data['lon']} out of range.")
    if not (0.0 <= data["rating"] <= 5.0):
        raise ValueError(f"[{source}] Rating {data['rating']} must be in [0, 5].")
    if data["avg_cost_usd"] < 0:
        raise ValueError(f"[{source}] avg_cost_usd must be non-negative.")
    if data["avg_duration_minutes"] <= 0:
        raise ValueError(f"[{source}] avg_duration_minutes must be positive.")


def _dict_to_poi(data: dict) -> POI:
    """Convert a validated raw dictionary to a POI dataclass instance."""
    return POI(
        id=data["id"],
        name=data["name"],
        city=data["city"],
        lat=float(data["lat"]),
        lon=float(data["lon"]),
        category=data["category"],
        tags=list(data.get("tags", [])),
        avg_cost_usd=float(data["avg_cost_usd"]),
        avg_duration_minutes=int(data["avg_duration_minutes"]),
        opening_hours=data["opening_hours"],
        rating=float(data["rating"]),
        indoor=bool(data["indoor"]),
        family_friendly=bool(data["family_friendly"]),
    )


def load_city(city_name: str, data_dir: Optional[Path] = None) -> list[POI]:
    """
    Load and validate all POIs for a city from its JSON file.

    Args:
        city_name: City name (case-insensitive), must match a file in data/cities/.
        data_dir: Override the default data directory (useful for tests).

    Returns:
        List of validated POI objects.

    Raises:
        FileNotFoundError: If the city JSON file does not exist.
        ValueError: If any POI fails schema validation.
    """
    base = data_dir or DATA_DIR
    path = base / f"{city_name.lower()}.json"

    if not path.exists():
        available = [p.stem for p in base.glob("*.json")]
        raise FileNotFoundError(
            f"No data file found for city '{city_name}'. "
            f"Available cities: {available}."
        )

    with path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)

    if not isinstance(raw, list):
        raise ValueError(f"Expected a JSON array in {path}, got {type(raw).__name__}.")

    pois: list[POI] = []
    seen_ids: set[str] = set()

    for entry in raw:
        _validate_poi_dict(entry, str(path))
        poi = _dict_to_poi(entry)
        if poi.id in seen_ids:
            raise ValueError(f"Duplicate POI id '{poi.id}' in {path}.")
        seen_ids.add(poi.id)
        pois.append(poi)

    if len(pois) < 20:
        raise ValueError(
            f"City '{city_name}' has only {len(pois)} POIs — minimum is 20 for meaningful clustering."
        )

    return pois


def available_cities(data_dir: Optional[Path] = None) -> list[str]:
    """Return the list of city names that have data files."""
    base = data_dir or DATA_DIR
    return sorted(p.stem.capitalize() for p in base.glob("*.json"))
