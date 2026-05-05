"""
Utility functions: Haversine distance, travel-time helpers, date utilities.
"""

import math
from datetime import date, timedelta
from typing import Tuple

from .config import WALKING_SPEED_KMH, TRANSIT_SPEED_KMH, DAY_ABBREVIATIONS

EARTH_RADIUS_KM = 6371.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Compute great-circle distance between two coordinates in kilometres.

    Uses the Haversine formula, which gives exact results on a spherical Earth.
    Accurate to within ~0.5% for distances up to a few hundred kilometres,
    which is sufficient for intra-city routing.

    Args:
        lat1, lon1: Origin latitude and longitude in decimal degrees.
        lat2, lon2: Destination latitude and longitude in decimal degrees.

    Returns:
        Distance in kilometres.
    """
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


def travel_time_minutes(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
    mode: str = "walking",
) -> float:
    """
    Estimate point-to-point travel time in minutes.

    Args:
        lat1, lon1: Origin coordinates.
        lat2, lon2: Destination coordinates.
        mode: 'walking' or 'transit'.

    Returns:
        Estimated travel time in minutes.
    """
    dist_km = haversine_distance(lat1, lon1, lat2, lon2)
    speed = WALKING_SPEED_KMH if mode == "walking" else TRANSIT_SPEED_KMH
    return (dist_km / speed) * 60.0


def day_of_week(start_date: date, day_offset: int = 0) -> str:
    """
    Return the three-letter weekday abbreviation for start_date + day_offset.

    Args:
        start_date: The trip start date.
        day_offset: 0-indexed day offset (0 = first day of trip).

    Returns:
        Abbreviation such as 'mon', 'tue', etc.
    """
    target = start_date + timedelta(days=day_offset)
    return DAY_ABBREVIATIONS[target.weekday()]


def centroid(coords: list[Tuple[float, float]]) -> Tuple[float, float]:
    """
    Compute the geographic centroid (arithmetic mean) of a list of (lat, lon) pairs.
    Acceptable for small city-scale areas where spherical distortion is negligible.
    """
    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    return (sum(lats) / len(lats), sum(lons) / len(lons))


def minutes_to_hhmm(minutes: float) -> str:
    """Convert a float number of minutes to a 'H:MM' string for display."""
    total = int(minutes)
    h, m = divmod(total, 60)
    return f"{h}h {m:02d}m"
