"""Spatial summaries for one day of detections.

Equal-degree bins are not equal-area bins. Overlap is the nearest-neighbor
chord length on a sphere. A neighbor inside a radius is a proximity between
archived detections, not a shared fire and not a harmonization factor.
"""

from __future__ import annotations

import numpy as np

EARTH_RADIUS_M = 6_371_008.8
EARTH_RADIUS_KM = EARTH_RADIUS_M / 1000.0

OVERLAP_METHOD = (
    "Spatial overlap is a proximity count between archived detections. "
    "For each ordered pair of satellites, every detection in A is assigned the nearest detection in B. "
    "The distance is the Euclidean chord length between Earth-centered coordinates on a sphere of radius "
    f"{EARTH_RADIUS_M:.1f} m. At a 5 km threshold this chord is within a millimeter of the great-circle length. "
    "A detection is counted at a threshold when that nearest distance is less than or equal to the threshold. "
    "The thresholds are configurable proximity radii, not sensor footprints. "
    "They do not account for scan-dependent pixel growth, geolocation error, or the time between acquisitions. "
    "One detection can be close to more than one other satellite. "
    "The relation is ordered, so A's share with a neighbor in B can differ from B's share with a neighbor in A. "
    "Self-pairs are omitted. Terra and Aqua are separate groups. "
    "The result is not a unique-fire match rate and no harmonization factor is calculated."
)

DENSITY_METHOD = (
    "Global density uses equal-degree longitude and latitude bins. "
    "A cell near a pole covers less ground than a cell at the equator, so the maps are not equal-area. "
    "The companion rate divides each cell count by its spherical zone area on a sphere of radius "
    f"{EARTH_RADIUS_KM:.4f} km and reports detections per 1,000 km². "
    "Both quantities count archived detections for this date. They do not count unique fires."
)


def degree_edges(bin_degrees: float, start: float, stop: float) -> np.ndarray:
    steps = int(round((stop - start) / bin_degrees))
    if steps <= 0 or not np.isclose(steps * bin_degrees, stop - start):
        raise ValueError("Bin width must divide the axis exactly")
    edges = np.linspace(start, stop, steps + 1)
    edges[0] = start
    edges[-1] = stop
    return edges


def count_grid(
    latitude: np.ndarray,
    longitude: np.ndarray,
    bin_degrees: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return counts with latitude rows from south to north and longitude columns from west to east."""

    lat_edges = degree_edges(bin_degrees, -90.0, 90.0)
    lon_edges = degree_edges(bin_degrees, -180.0, 180.0)
    counts, _, _ = np.histogram2d(
        np.asarray(longitude, dtype=np.float64),
        np.asarray(latitude, dtype=np.float64),
        bins=[lon_edges, lat_edges],
    )
    grid = counts.T
    if int(grid.sum()) != int(np.asarray(latitude).size):
        raise ValueError("One or more coordinates fell outside the degree grid")
    return grid, lat_edges, lon_edges


def cell_area_km2(lat_edges: np.ndarray, lon_edges: np.ndarray) -> np.ndarray:
    """Spherical zone area of each latitude row for one equal longitude bin."""

    dlon = np.radians(np.diff(lon_edges))
    if dlon.size == 0 or not np.allclose(dlon, dlon[0]):
        raise ValueError("Longitude bins must share one width")
    lat0 = np.radians(lat_edges[:-1])
    lat1 = np.radians(lat_edges[1:])
    area = (EARTH_RADIUS_KM**2) * dlon[0] * (np.sin(lat1) - np.sin(lat0))
    if np.any(area <= 0):
        raise ValueError("Cell area must be positive")
    return area


def detections_per_1000_km2(grid: np.ndarray, lat_edges: np.ndarray, lon_edges: np.ndarray) -> np.ndarray:
    area = cell_area_km2(lat_edges, lon_edges)
    return grid / area[:, None] * 1000.0


def lonlat_to_ecef(latitude: np.ndarray, longitude: np.ndarray) -> np.ndarray:
    lat = np.radians(np.asarray(latitude, dtype=np.float64))
    lon = np.radians(np.asarray(longitude, dtype=np.float64))
    cos_lat = np.cos(lat)
    return np.column_stack(
        (
            EARTH_RADIUS_M * cos_lat * np.cos(lon),
            EARTH_RADIUS_M * cos_lat * np.sin(lon),
            EARTH_RADIUS_M * np.sin(lat),
        )
    )


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = EARTH_RADIUS_M
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2.0) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2.0) ** 2
    return float(2.0 * radius * np.arcsin(np.sqrt(a)))


def pairwise_nearest_distances(
    coordinates: dict[str, tuple[np.ndarray, np.ndarray]],
    max_distance_m: float,
) -> dict[tuple[str, str], np.ndarray]:
    """Nearest chord for every ordered pair, building each satellite tree once."""

    from scipy.spatial import cKDTree

    ecef = {name: lonlat_to_ecef(latitude, longitude) for name, (latitude, longitude) in coordinates.items()}
    trees = {name: cKDTree(points) for name, points in ecef.items()}
    distances: dict[tuple[str, str], np.ndarray] = {}
    for name_a, points_a in ecef.items():
        for name_b, tree in trees.items():
            if name_a == name_b:
                continue
            measured, _ = tree.query(points_a, k=1, distance_upper_bound=float(max_distance_m), workers=1)
            distances[(name_a, name_b)] = np.atleast_1d(np.asarray(measured, dtype=np.float64))
    return distances


def nearest_distances_m(
    latitude_a: np.ndarray,
    longitude_a: np.ndarray,
    latitude_b: np.ndarray,
    longitude_b: np.ndarray,
    max_distance_m: float,
) -> np.ndarray:
    """Nearest ECEF chord from each point in A to B.

    Distances above ``max_distance_m`` are returned as infinity. The query asks
    only for the nearest neighbor, which is enough to test a radius and does
    not materialize every pair.
    """

    from scipy.spatial import cKDTree

    count_a = int(np.asarray(latitude_a).size)
    if count_a == 0 or int(np.asarray(latitude_b).size) == 0:
        return np.full(count_a, np.inf)
    tree = cKDTree(lonlat_to_ecef(latitude_b, longitude_b))
    distances, _ = tree.query(
        lonlat_to_ecef(latitude_a, longitude_a),
        k=1,
        distance_upper_bound=float(max_distance_m),
        workers=1,
    )
    return np.atleast_1d(np.asarray(distances, dtype=np.float64))
