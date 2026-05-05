"""
K-Means day-partitioning for AI Travel Planner.

Academic notes
--------------
**Why K-Means over DBSCAN?**
We know the target number of clusters (k = num_days) in advance, making
K-Means the natural choice. DBSCAN discovers an unknown number of clusters
based on density, which would require post-hoc merging/splitting to hit
exactly num_days groups. K-Means directly optimises for k groups.

**Why Euclidean distance on lat/lon?**
Euclidean distance on raw lat/lon coordinates is acceptable for intra-city
distances (~30 km radius) because the spherical distortion is < 0.5%. For
continental-scale clustering, projecting to UTM or using Haversine would be
preferable. K-Means requires Euclidean space by construction (it centres
clusters via arithmetic mean, which is not meaningful on a sphere).

**Cluster imbalance:**
K-Means minimises within-cluster inertia, so clusters may have unequal
cardinalities. The CSP solver handles over-full days by dropping
low-preference POIs; under-full days receive fewer POIs, which is fine.
"""

from __future__ import annotations

import numpy as np
from sklearn.cluster import KMeans

from .config import RANDOM_SEED
from .data_loader import POI
from .preferences import UserPreferences

def cluster_pois_by_day(
    pois: list[POI],
    num_days: int,
    preferences: UserPreferences,
) -> dict[int, list[POI]]:
    """
    Partition POIs into num_days geographic clusters using K-Means.

    Steps:
    1. Pre-filter: remove POIs in must_avoid_categories or with zero interest weight.
    2. Run K-Means (k = num_days) on (lat, lon) coordinates.
    3. Assign each POI to its cluster (day_index + 1 → day number).
    4. Ensure must_include POIs appear in the result (re-add if filtered).

    Args:
        pois: All POIs for the destination city.
        num_days: Number of travel days (= desired number of clusters).
        preferences: User preferences for filtering and must_include.

    Returns:
        Dict mapping day number (1-indexed) to list of POIs in that cluster.

    Raises:
        ValueError: If too few POIs remain after filtering to form num_days clusters.
    """
    must_include_ids = set(preferences.must_include)

    # Step 1 — pre-filter
    filtered: list[POI] = []
    forced: list[POI] = []  # must_include POIs that were filtered out

    for poi in pois:
        if poi.category in preferences.must_avoid_categories:
            if poi.id in must_include_ids:
                forced.append(poi)
            continue

        weight = preferences.interest_weights.get(poi.category, 0.5)
        if weight == 0.0:
            if poi.id in must_include_ids:
                forced.append(poi)
            continue

        # Family travellers: skip non-family-friendly POIs
        if preferences.traveler_type == "family" and not poi.family_friendly:
            if poi.id in must_include_ids:
                forced.append(poi)
            continue

        filtered.append(poi)

    # Re-add forced must_include POIs (de-duplicated)
    filtered_ids = {p.id for p in filtered}
    for poi in forced:
        if poi.id not in filtered_ids:
            filtered.append(poi)

    if len(filtered) < num_days:
        raise ValueError(
            f"After filtering, only {len(filtered)} POIs remain — "
            f"not enough to fill {num_days} days. "
            f"Try reducing must_avoid_categories or lowering interest weight thresholds."
        )

    # Step 2 — K-Means clustering
    coords = np.array([[p.lat, p.lon] for p in filtered])

    k = min(num_days, len(filtered))
    kmeans = KMeans(n_clusters=k, random_state=RANDOM_SEED, n_init=10)
    labels = kmeans.fit_predict(coords)

    # Step 3 — group by cluster
    clusters: dict[int, list[POI]] = {day: [] for day in range(1, k + 1)}
    for poi, label in zip(filtered, labels):
        clusters[label + 1].append(poi)

    # Ensure every cluster has at least one POI (K-Means guarantees this
    # when len(filtered) >= k, but be defensive)
    empty_days = [d for d, lst in clusters.items() if len(lst) == 0]
    if empty_days:
        # Move one POI from the largest cluster to each empty day
        all_pois_sorted = sorted(
            filtered,
            key=lambda p: preferences.interest_weights.get(p.category, 0.5),
        )
        for empty_day in empty_days:
            for poi in all_pois_sorted:
                assigned_day = next(
                    d for d, lst in clusters.items() if any(x.id == poi.id for x in lst)
                )
                if len(clusters[assigned_day]) > 1:
                    clusters[assigned_day].remove(poi)
                    clusters[empty_day].append(poi)
                    break

    return clusters


def get_city_center(pois: list[POI]) -> tuple[float, float]:
    """
    Compute geographic centroid of all POIs as a default hotel location.

    Args:
        pois: List of POIs for a city.

    Returns:
        (lat, lon) of the centroid.
    """
    lats = [p.lat for p in pois]
    lons = [p.lon for p in pois]
    return (sum(lats) / len(lats), sum(lons) / len(lons))
