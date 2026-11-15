"""Experiment D: stored footprint proxies and equal-degree versus equal-area cells.

``scan * track`` is a rectangle using the stored kilometre lengths. It is not
an exact ground polygon. H3 is not selected.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from fire_data.eda_figures import COLORS
from fire_data.eda_spatial import EARTH_RADIUS_M, cell_area_km2, count_grid
from fire_data.experiments.common import (
    DISPLAY,
    INDEX,
    SATELLITE_ORDER,
    ExperimentRunError,
    Stopwatch,
    assert_locks,
    base_results,
    begin,
    finish,
    publish_run,
    quantiles,
    read_json,
    require_july_timestamp,
    require_satellite,
    save_figure,
    scan_archives,
    verify_checksum_cache,
    write_json,
)
from fire_data.experiments.prepare import ExperimentConfigError
from fire_data.experiments.validate import SchemaError
from fire_data.monthly_scan import ARCHIVES

EDA_JSON = Path(__file__).resolve().parents[2] / "reports" / "monthly_eda_2024_07.json"
WITHIN_JSON = Path(__file__).resolve().parents[2] / "reports" / "within_sensor_analysis_2024_07.json"
FOOTPRINT_LIMIT = (
    "scan and track are stored lengths in kilometres. Their product treats those lengths as the sides of a rectangle. "
    "The archive does not include the pixel polygon, the scan angle, or the ground orientation. "
    "Adjacent-scan overlap and Earth curvature inside the pixel are not corrected. "
    "scan multiplied by track is a stored-size proxy, not an exact physical pixel area."
)


def _growth(scan: np.ndarray, track: np.ndarray, product: np.ndarray) -> list[dict[str, Any]]:
    edges = np.quantile(scan, np.linspace(0.0, 1.0, 11), method="linear")
    edges = np.unique(edges)
    if edges.size < 2:
        return []
    bins = np.digitize(scan, edges[1:-1], right=True)
    rows = []
    for index in range(edges.size - 1):
        mask = bins == index
        count = int(np.count_nonzero(mask))
        rows.append(
            {
                "scan_bin_start_km": float(edges[index]),
                "scan_bin_end_km": float(edges[index + 1]),
                "rows": count,
                "scan": quantiles(scan[mask]),
                "track": quantiles(track[mask]),
                "scan_times_track": quantiles(product[mask]),
            }
        )
    return rows


def _cell(lat_edges: np.ndarray, lon_edges: np.ndarray, row: int, column: int, grid: np.ndarray, area_row: np.ndarray) -> dict[str, Any]:
    count = int(grid[row, column])
    area = float(area_row[row])
    return {
        "latitude_floor": int(lat_edges[row]),
        "longitude_floor": int(lon_edges[column]),
        "rows": count,
        "cell_area_km2": area,
        "rows_per_1000_km2": None if area == 0 else count / area * 1000.0,
    }


def _grid_report(latitude: np.ndarray, longitude: np.ndarray, bin_degrees: float) -> dict[str, Any]:
    grid, lat_edges, lon_edges = count_grid(latitude, longitude, bin_degrees)
    area_row = cell_area_km2(lat_edges, lon_edges)
    occupied = grid > 0
    count_row, count_column = np.unravel_index(int(np.argmax(grid)), grid.shape)
    rate = np.where(occupied, grid / area_row[:, None] * 1000.0, -1.0)
    rate_row, rate_column = np.unravel_index(int(np.argmax(rate)), rate.shape)
    order = np.argsort(grid.ravel())[::-1]
    top = []
    for position in order[:8]:
        count = int(grid.ravel()[position])
        if count == 0:
            break
        row, column = divmod(int(position), grid.shape[1])
        top.append(_cell(lat_edges, lon_edges, row, column, grid, area_row))
    bands = []
    total_rows = int(grid.sum())
    total_area = float(np.sum(area_row) * grid.shape[1])
    for south in range(-90, 90, 30):
        chosen = (lat_edges[:-1] >= south) & (lat_edges[:-1] < south + 30)
        row_count = int(grid[chosen].sum())
        band_area = float(np.sum(area_row[chosen]) * grid.shape[1])
        bands.append(
            {
                "latitude_start": south,
                "latitude_end": south + 30,
                "rows": row_count,
                "row_share": None if total_rows == 0 else row_count / total_rows,
                "spherical_area_km2": band_area,
                "area_share": None if total_area == 0 else band_area / total_area,
            }
        )
    centers = (lat_edges[:-1] + lat_edges[1:]) / 2.0
    high = np.abs(centers) >= 60.0
    high_rows = int(grid[high].sum())
    high_area = float(np.sum(area_row[high]) * grid.shape[1])
    return {
        "bin_degrees": bin_degrees,
        "equal_degree_cells_are_equal_area": False,
        "occupied_cells": int(np.count_nonzero(occupied)),
        "rows": total_rows,
        "count_maximum_cell": _cell(lat_edges, lon_edges, int(count_row), int(count_column), grid, area_row),
        "rate_maximum_cell": _cell(lat_edges, lon_edges, int(rate_row), int(rate_column), grid, area_row),
        "count_and_rate_maxima_are_the_same_cell": bool(count_row == rate_row and count_column == rate_column),
        "top_cells_by_row_count": top,
        "latitude_bands": bands,
        "high_latitude_abs_at_least_60": {
            "rows": high_rows,
            "row_share": None if total_rows == 0 else high_rows / total_rows,
            "area_share": None if total_area == 0 else high_area / total_area,
            "meaning": "Cells whose latitude centers are at least 60 degrees from the equator. Row share above the area share means equal-degree counts overweight that latitude relative to ground area.",
        },
        "rows_are_archived_detections": True,
        "cells_are_not_fires": True,
        "cells_are_not_analytical_clusters": True,
    }


def _h3_candidate(product: dict[str, Any]) -> dict[str, Any]:
    base = {
        "h3_library_required": False,
        "h3_selected": False,
        "selected_resolution": None,
        "reason": "H3 is an unselected candidate. No resolution is chosen.",
    }
    try:
        import h3
    except ImportError:
        base.update(
            {
                "h3_library_present": False,
                "average_hexagon_area_km2": None,
                "comparison": None,
                "detail": "The h3 package is not installed. No average cell area was read from the library, and none was invented.",
            }
        )
        return base
    areas = []
    reader = getattr(h3, "average_hexagon_area", None)
    if reader is None:
        base.update(
            {
                "h3_library_present": True,
                "average_hexagon_area_km2": None,
                "comparison": None,
                "detail": "h3 imported, but average_hexagon_area was not available. No resolution was selected.",
            }
        )
        return base
    try:
        for resolution in range(0, 11):
            areas.append(
                {
                    "resolution": resolution,
                    "average_hexagon_area_km2": float(reader(resolution, unit="km^2")),
                    "selected": False,
                }
            )
    except (TypeError, ValueError) as exc:
        base.update(
            {
                "h3_library_present": True,
                "average_hexagon_area_km2": None,
                "comparison": None,
                "detail": f"h3 imported, but its area function could not be read in square kilometres ({exc}). No area was invented and no resolution was selected.",
            }
        )
        return base
    median_product = product.get("p50")
    base.update(
        {
            "h3_library_present": True,
            "average_hexagon_area_km2": areas,
            "observed_scan_times_track_p50_km2": median_product,
            "comparison": "Average H3 hexagon areas are library constants. They are not a selected cell size for this month.",
            "detail": "The table is a comparison only. h3_selected remains false.",
        }
    )
    return base


def _collect(config: dict[str, Any]) -> tuple[dict[str, dict[str, np.ndarray]], int, int]:
    specs = {str(spec["sensor"]): spec for spec in ARCHIVES}
    capacity = {
        satellite: int(count)
        for archive in config["inputs"]["archives"]
        for satellite, count in archive["satellites"].items()
    }
    columns = {
        satellite: {name: np.empty(count, dtype=np.float64) for name in ("latitude", "longitude", "scan", "track")}
        for satellite, count in capacity.items()
    }
    cursor = {satellite: 0 for satellite in capacity}

    def consume(sensor: str, row: list[str], index: dict[str, int]) -> None:
        del index
        satellite = require_satellite(row, specs[sensor]["satellites"], sensor)
        require_july_timestamp(row, sensor, satellite)
        position = cursor[satellite]
        if position >= capacity[satellite]:
            raise ExperimentRunError(f"{satellite} exceeded the configuration row count")
        bucket = columns[satellite]
        bucket["latitude"][position] = float(row[INDEX["latitude"]])
        bucket["longitude"][position] = float(row[INDEX["longitude"]])
        bucket["scan"][position] = float(row[INDEX["scan"]])
        bucket["track"][position] = float(row[INDEX["track"]])
        cursor[satellite] = position + 1

    counts = scan_archives(tuple(spec["sensor"] for spec in ARCHIVES), consume)
    for satellite, count in capacity.items():
        if cursor[satellite] != count:
            raise ExperimentRunError(f"{satellite} has {cursor[satellite]} rows; the configuration records {count}")
    rows_read = sum(item for key, item in counts.items() if key != "source_bytes_read")
    return columns, int(rows_read), int(counts["source_bytes_read"])


def _satellite(name: str, table: dict[str, np.ndarray], eda: dict[str, Any], within: dict[str, Any]) -> dict[str, Any]:
    scan = table["scan"]
    track = table["track"]
    product = scan * track
    product_summary = quantiles(product)
    scan_summary = quantiles(scan)
    track_summary = quantiles(track)
    product_of_medians = float(scan_summary["p50"]) * float(track_summary["p50"])
    grid_1 = _grid_report(table["latitude"], table["longitude"], 1.0)
    grid_2 = _grid_report(table["latitude"], table["longitude"], 2.0)
    published_spatial = eda["spatial"][name]
    published_scan = within["characteristics"]["all"]["scan"]
    published_track = within["characteristics"]["all"]["track"]
    return {
        "satellite": name,
        "display": DISPLAY[name],
        "rows": int(scan.size),
        "scan": scan_summary,
        "track": track_summary,
        "scan_times_track": product_summary,
        "product_of_medians_km2": product_of_medians,
        "median_of_products_km2": product_summary["p50"],
        "product_of_medians_is_median_of_products": False,
        "product_of_medians_equals_median_of_products_numerically": bool(
            np.isclose(product_of_medians, float(product_summary["p50"]), rtol=0.0, atol=1e-9)
        ),
        "footprint_proxy": "scan_times_track_km2_distribution",
        "footprint_limitation": FOOTPRINT_LIMIT,
        "thresholds_are_sensor_footprints": False,
        "growth_with_scan": _growth(scan, track, product),
        "grid_1_degree": grid_1,
        "grid_2_degree": grid_2,
        "published_monthly_1_degree": {
            "recomputed": False,
            "occupied_cells": published_spatial["occupied_cells"],
            "rows_in_cells": published_spatial["rows_in_cells"],
            "top_cell": published_spatial["top_cells"][0],
        },
        "published_within_sensor_scan_track": {
            "recomputed": False,
            "scan_p50_km": published_scan["p50"],
            "track_p50_km": published_track["p50"],
        },
        "one_degree_occupied_cells_match_published_floor_count": int(grid_1["occupied_cells"]) == int(published_spatial["occupied_cells"]),
        "same_fire": "not_assessed",
        "cells_are_not_analytical_clusters": True,
    }


def _figures(results: dict[str, Any], directory: Path) -> list[str]:
    directory.mkdir(parents=True, exist_ok=True)
    names = []
    labels = [sensor["display"] for sensor in results["satellites"]]
    positions = np.arange(len(labels))
    figure, axis = plt.subplots(figsize=(8.2, 4.6))
    medians = [sensor["scan_times_track"]["p50"] for sensor in results["satellites"]]
    products = [sensor["product_of_medians_km2"] for sensor in results["satellites"]]
    axis.bar(positions - 0.18, medians, width=0.36, color="#3d8b7a", label="Median of scan × track")
    axis.bar(positions + 0.18, products, width=0.36, color="#c8c1b4", label="Product of medians")
    axis.set_xticks(positions)
    axis.set_xticklabels(labels)
    axis.set_ylabel("Square kilometres")
    axis.set_title("Stored-size proxy, not an exact pixel area")
    axis.legend(frameon=False)
    path = directory / "footprint_proxy.png"
    save_figure(figure, path)
    plt.close(figure)
    names.append(path.name)

    figure, axis = plt.subplots(figsize=(8.4, 4.8))
    for sensor in results["satellites"]:
        growth = [item for item in sensor["growth_with_scan"] if item["rows"] > 0 and item["scan_times_track"]["p50"] is not None]
        axis.plot(
            [item["scan"]["p50"] for item in growth],
            [item["scan_times_track"]["p50"] for item in growth],
            marker="o",
            color=COLORS[sensor["satellite"]],
            label=sensor["display"],
        )
    axis.set_xlabel("Median scan in the bin (km)")
    axis.set_ylabel("Median scan × track (km²)")
    axis.set_title("The stored-size proxy grows toward larger scan")
    axis.legend(ncol=3, frameon=False)
    path = directory / "proxy_versus_scan.png"
    save_figure(figure, path)
    plt.close(figure)
    names.append(path.name)

    figure, axis = plt.subplots(figsize=(8.2, 4.6))
    row_share = [sensor["grid_1_degree"]["high_latitude_abs_at_least_60"]["row_share"] for sensor in results["satellites"]]
    area_share = [sensor["grid_1_degree"]["high_latitude_abs_at_least_60"]["area_share"] for sensor in results["satellites"]]
    axis.bar(positions - 0.18, row_share, width=0.36, color="#8c4a2f", label="Share of rows")
    axis.bar(positions + 0.18, area_share, width=0.36, color="#d9d3c7", label="Share of spherical area")
    axis.set_xticks(positions)
    axis.set_xticklabels(labels)
    axis.set_ylabel("Share")
    axis.set_title("Latitudes at or beyond 60°")
    axis.legend(frameon=False)
    path = directory / "high_latitude_share.png"
    save_figure(figure, path)
    plt.close(figure)
    names.append(path.name)
    return names


def _markdown(results: dict[str, Any]) -> str:
    lines = [
        "# Experiment D: spatial resolution and aggregation candidates",
        "",
        "Question: how large are the stored MODIS and VIIRS sizes in this month, how uneven is the geographic sample, and which aggregations are only candidates?",
        "",
        FOOTPRINT_LIMIT,
        "",
        "The product of the medians is reported beside the median of the products. Those two numbers are not treated as the same quantity. Search radii are not footprints. Equal-degree cells are not equal-area cells. No H3 resolution is selected. A cell is not an analytical cluster and not a fire.",
        "",
        f"Cell area uses the spherical zone on a sphere of radius {results['earth_radius_m']} m, through the existing `cell_area_km2` calculation. A count in a cell is a count of archived rows.",
        "",
        "## Stored scan, track, and their product",
        "",
        "| Satellite | Scan p50 (km) | Track p50 (km) | Median of products (km²) | Product of medians (km²) | Product p90 (km²) |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for sensor in results["satellites"]:
        lines.append(
            f"| {sensor['display']} | {sensor['scan']['p50']:.3f} | {sensor['track']['p50']:.3f} | "
            f"{sensor['median_of_products_km2']:.3f} | {sensor['product_of_medians_km2']:.3f} | "
            f"{sensor['scan_times_track']['p90']:.3f} |"
        )
    lines.extend(
        [
            "",
            "The growth table in `results.json` bins each satellite's own scan distribution. Median `scan × track` is larger in the upper scan bins. The file contains no scan angle, so none is inferred.",
            "",
            "## One-degree and two-degree cells",
            "",
            "| Satellite | 1° occupied | 1° count cell equals rate cell | 1° row share at |lat| ≥ 60° | 1° area share at |lat| ≥ 60° | 2° occupied |",
            "| --- | ---: | --- | ---: | ---: | ---: |",
        ]
    )
    for sensor in results["satellites"]:
        grid = sensor["grid_1_degree"]
        high = grid["high_latitude_abs_at_least_60"]
        lines.append(
            f"| {sensor['display']} | {grid['occupied_cells']} | {grid['count_and_rate_maxima_are_the_same_cell']} | "
            f"{high['row_share']:.3f} | {high['area_share']:.3f} | {sensor['grid_2_degree']['occupied_cells']} |"
        )
    lines.extend(
        [
            "",
            "When the cell with the most rows is not the cell with the highest rows per 1,000 km², an equal-degree reading and an equal-area reading do not point at the same place. High-latitude bands cover less ground. A raw count there is not a density.",
            "",
            "The published monthly 1° occupancy is cited in the JSON. This run rebuilds the grids with `count_grid` so the spherical area can be attached. A difference from the published floor count, if one appears, is recorded on the satellite and is not silently replaced.",
            "",
            "## Candidate aggregations",
            "",
            "None of these is selected:",
            "",
            "- equal-degree 1° cells",
            "- equal-degree 2° cells",
            "- the same cells converted with the spherical zone area",
            "- H3 cells, unselected",
            "",
            results["h3"]["detail"],
            "",
            "An aggregation cell is not one of Experiment A's components.",
            "",
            "## Limits",
            "",
            "- `scan × track` is not an exact physical pixel area.",
            "- A 1 km search radius is not a MODIS pixel, and a 375 m radius is not a VIIRS pixel.",
            "- Summing satellites would count the same ground more than once when several sensors report it. Densities stay per satellite.",
            "- S-NPP dates with no rows are absent from that satellite's grid. They were not filled.",
            "- No harmonization coefficient was calculated. XGBoost was not trained.",
            "",
        ]
    )
    return "\n".join(lines)


def run(work_root: Path, run_id: str, checksum_cache: Path) -> int:
    clock = Stopwatch()
    destination: Path | None = None
    schema: dict[str, Any] | None = None
    try:
        destination, config, schema = begin("D", work_root, run_id)
        assert_locks(config)
        if config["parameters"]["h3_selected"] or config["parameters"]["h3_library_required"]:
            raise ExperimentRunError("experiment D cannot select H3")
        checksums = verify_checksum_cache(checksum_cache, config)
        eda = read_json(EDA_JSON)
        within = {sensor["satellite"]: sensor for sensor in read_json(WITHIN_JSON)["sensors"]}
        arrays, rows_read, bytes_read = _collect(config)
        satellites = [_satellite(name, arrays[name], eda, within[name]) for name in SATELLITE_ORDER]
        del arrays
        h3_record = _h3_candidate(satellites[0]["scan_times_track"])
        # The H3 comparison is global. Attach each satellite's own product median in the JSON list below.
        h3_record["per_satellite_scan_times_track_p50_km2"] = {
            sensor["satellite"]: sensor["scan_times_track"]["p50"] for sensor in satellites
        }
        results = base_results(config, checksums)
        results.update(
            {
                "earth_radius_m": EARTH_RADIUS_M,
                "footprint_proxy": "scan_times_track_km2_distribution",
                "footprint_limitation": FOOTPRINT_LIMIT,
                "thresholds_are_sensor_footprints": False,
                "equal_degree_cells_are_equal_area": False,
                "product_of_medians_is_median_of_products": False,
                "h3_selected": False,
                "h3_library_required": False,
                "candidate_methods": [
                    "equal_degree_1",
                    "equal_degree_2",
                    "spherical_zone_area",
                    "h3_unselected",
                ],
                "selected_method": None,
                "satellites": satellites,
                "h3": h3_record,
                "records_processed": rows_read,
            }
        )
        checks = [
            {"name": "h3_not_selected", "passed": results["h3_selected"] is False and h3_record["h3_selected"] is False},
            {"name": "identity_lock_is_false", "passed": all(sensor["product_of_medians_is_median_of_products"] is False for sensor in satellites)},
            {"name": "grid_rows_match_satellite_rows", "passed": all(sensor["grid_1_degree"]["rows"] == sensor["rows"] for sensor in satellites)},
            {"name": "source_rows_match_manifest", "passed": rows_read == config["inputs"]["expected_rows"]},
            {"name": "same_fire_not_assessed", "passed": True},
            {
                "name": "published_scan_p50_matches",
                "passed": all(
                    np.isclose(sensor["scan"]["p50"], sensor["published_within_sensor_scan_track"]["scan_p50_km"], rtol=0.0, atol=1e-6)
                    for sensor in satellites
                ),
            },
        ]
        status = "completed" if all(item["passed"] for item in checks) else "failed"
        results["validation"] = checks
        results["figures"] = _figures(results, destination / "figures")
        write_json(destination / "results.json", results)
        (destination / "report.md").write_text(_markdown(results), encoding="utf-8")
        write_json(destination / "validation.json", {"passed": status == "completed", "checks": checks})
        write_json(
            destination / "execution.json",
            {
                "wall_clock_seconds": clock.wall(),
                "cpu_seconds": clock.cpu(),
                "source_rows_read": rows_read,
                "source_bytes_read": bytes_read,
                "records_processed": rows_read,
                "records_per_second": None if clock.wall() == 0 else rows_read / clock.wall(),
                "retries": 0,
                "cancelled": False,
            },
        )
        finish(
            destination,
            schema,
            status=status,
            science_executed=True,
            results=results,
            source_rows_read=rows_read,
            source_bytes_read=bytes_read,
            records_processed=rows_read,
            science_seconds=clock.wall(),
            cpu_seconds=clock.cpu(),
        )
        publish_run(destination, "D")
        return 0 if status == "completed" else 1
    except (OSError, ExperimentRunError, ExperimentConfigError, SchemaError, KeyError, ValueError) as exc:
        if destination is not None and schema is not None:
            _fail(destination, schema, clock, exc)
        return 1


def _fail(destination: Path, schema: dict[str, Any], clock: Stopwatch, exc: Exception) -> None:
    try:
        finish(
            destination,
            schema,
            status="failed",
            science_executed=True,
            results={"error": f"{type(exc).__name__}: {exc}", "same_fire": "not_assessed"},
            source_rows_read=0,
            source_bytes_read=0,
            records_processed=0,
            science_seconds=clock.wall(),
            cpu_seconds=clock.cpu(),
        )
    except (OSError, ExperimentRunError):
        (destination / "error.txt").write_text(str(exc), encoding="utf-8")
    write_json(destination / "validation.json", {"passed": False, "checks": [{"name": "run", "passed": False, "detail": str(exc)}]})
    try:
        publish_run(destination, "D")
    except OSError:
        pass
