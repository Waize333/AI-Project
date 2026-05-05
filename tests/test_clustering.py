"""Unit tests for src/clustering.py."""

import pytest
from datetime import date

from src.clustering import cluster_pois_by_day, get_city_center
from src.data_loader import load_city, POI
from src.preferences import UserPreferences


def _make_prefs(**kwargs) -> UserPreferences:
    defaults = dict(
        destination="Paris",
        num_days=3,
        budget_usd=300,
        traveler_type="solo",
        interest_weights={cat: 0.5 for cat in [
            "landmark", "museum", "food", "nature", "shopping",
            "religious", "nightlife", "adventure", "beach", "cultural",
        ]},
        pace="balanced",
        must_include=[],
        must_avoid_categories=[],
        start_date=date(2025, 6, 1),
        hotel_location=None,
    )
    defaults.update(kwargs)
    return UserPreferences(**defaults)


class TestClusterPoisByDay:
    def test_returns_correct_number_of_clusters(self):
        pois = load_city("paris")
        prefs = _make_prefs(num_days=3)
        result = cluster_pois_by_day(pois, 3, prefs)
        assert len(result) == 3

    def test_all_days_present(self):
        pois = load_city("paris")
        prefs = _make_prefs(num_days=4)
        result = cluster_pois_by_day(pois, 4, prefs)
        assert set(result.keys()) == {1, 2, 3, 4}

    def test_no_poi_appears_twice(self):
        pois = load_city("paris")
        prefs = _make_prefs(num_days=3)
        result = cluster_pois_by_day(pois, 3, prefs)
        all_ids = [p.id for lst in result.values() for p in lst]
        assert len(all_ids) == len(set(all_ids)), "Duplicate POI across days"

    def test_avoids_excluded_categories(self):
        pois = load_city("paris")
        prefs = _make_prefs(must_avoid_categories=["nightlife"])
        result = cluster_pois_by_day(pois, 3, prefs)
        for lst in result.values():
            for poi in lst:
                assert poi.category != "nightlife"

    def test_zero_weight_drops_category(self):
        pois = load_city("paris")
        weights = {cat: 0.5 for cat in [
            "landmark", "museum", "food", "nature", "shopping",
            "religious", "nightlife", "adventure", "beach", "cultural",
        ]}
        weights["nightlife"] = 0.0
        prefs = _make_prefs(interest_weights=weights)
        result = cluster_pois_by_day(pois, 3, prefs)
        for lst in result.values():
            for poi in lst:
                assert poi.category != "nightlife"

    def test_must_include_appears_in_result(self):
        pois = load_city("paris")
        # Use a POI that exists in paris.json
        must_id = pois[0].id
        prefs = _make_prefs(must_include=[must_id])
        result = cluster_pois_by_day(pois, 3, prefs)
        all_ids = {p.id for lst in result.values() for p in lst}
        assert must_id in all_ids

    def test_single_day(self):
        pois = load_city("paris")
        prefs = _make_prefs(num_days=1)
        result = cluster_pois_by_day(pois, 1, prefs)
        assert len(result) == 1

    def test_raises_when_too_few_pois_after_filter(self):
        pois = load_city("paris")
        # Avoid everything except adventure (very few POIs)
        weights = {cat: 0.0 for cat in [
            "landmark", "museum", "food", "nature", "shopping",
            "religious", "nightlife", "adventure", "beach", "cultural",
        ]}
        weights["adventure"] = 1.0
        prefs = _make_prefs(interest_weights=weights, num_days=10)
        with pytest.raises(ValueError, match="not enough"):
            cluster_pois_by_day(pois, 10, prefs)


class TestGetCityCenter:
    def test_centroid_within_reasonable_range(self):
        pois = load_city("paris")
        lat, lon = get_city_center(pois)
        # Paris should be roughly 48.8–48.9, 2.2–2.5
        assert 48.7 < lat < 49.0
        assert 2.1 < lon < 2.5
