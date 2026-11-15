"""Figures for the one-day FIRMS exploratory summary."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from fire_data.eda_spatial import count_grid, detections_per_1000_km2
from fire_data.eda_summary import DISPLAY_NAME, SATELLITE_ORDER, _satellite_positions
from fire_data.eda_table import DetectionTable

FIGURE_NAMES = (
    "frp_ecdf_by_satellite.png",
    "brightness_bright_t31_ecdf.png",
    "confidence_modis.png",
    "confidence_viirs.png",
    "scan_track_by_satellite.png",
    "daynight_proportions.png",
    "detections_by_utc_hour.png",
    "global_count_density.png",
    "global_area_normalized_density.png",
    "extreme_frp_locations.png",
)

COLORS = {
    "Terra": "#b86b2a",
    "Aqua": "#8c4a2f",
    "N20": "#2f6f8f",
    "N21": "#3d8b7a",
    "SNPP": "#5c4d7a",
    "modis": "#8c4a2f",
    "viirs_noaa20": "#2f6f8f",
    "viirs_noaa21": "#3d8b7a",
    "viirs_snpp": "#5c4d7a",
}


def _scope_title(summary: dict) -> str:
    dates = ", ".join(summary["scope"]["dates"]) or "undated"
    return f"{summary['scope']['label']}, {dates}"


def _series(tables: list[DetectionTable]) -> list[tuple[str, DetectionTable, np.ndarray | None]]:
    series = []
    for table in tables:
        for satellite, positions, _count in _satellite_positions(table):
            series.append((satellite, table, positions))
    ordered = []
    for satellite in SATELLITE_ORDER:
        ordered.extend(item for item in series if item[0] == satellite)
    known = {satellite for satellite in SATELLITE_ORDER}
    ordered.extend(item for item in series if item[0] not in known)
    return ordered


def _column(table: DetectionTable, positions: np.ndarray | None, name: str) -> np.ndarray:
    values = getattr(table, name)
    if positions is None:
        return values
    return values[positions]


def _finish(fig: plt.Figure, path: Path) -> None:
    fig.savefig(path, dpi=140)
    plt.close(fig)


def _ecdf(ax: plt.Axes, values: np.ndarray, label: str, color: str) -> None:
    ordered = np.sort(np.asarray(values, dtype=np.float64))
    ranks = np.arange(1, ordered.size + 1) / ordered.size
    ax.plot(ordered, ranks, color=color, label=label, linewidth=1.3)


def _plot_frp(tables: list[DetectionTable], summary: dict, path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 5.2), constrained_layout=True)
    ecdf, hist = axes
    for satellite, table, positions in _series(tables):
        values = _column(table, positions, "frp")
        color = COLORS.get(satellite, "#444444")
        label = DISPLAY_NAME.get(satellite, satellite)
        _ecdf(ecdf, values, label, color)
        positive = values[values > 0]
        if positive.size == 0 or float(positive.min()) == float(positive.max()):
            continue
        bins = np.logspace(np.log10(float(positive.min())), np.log10(float(positive.max())), 36)
        counts, edges = np.histogram(positive, bins=bins)
        hist.stairs(counts / values.size, edges, color=color, label=label, linewidth=1.3)
    ecdf.set_xscale("symlog", linthresh=0.1)
    ecdf.set_xlabel("FRP, including zeros and extremes")
    ecdf.set_ylabel("Empirical cumulative share of detections")
    ecdf.set_title("All stored FRP values")
    ecdf.legend(frameon=False)
    hist.set_xscale("log")
    hist.set_xlabel("FRP greater than zero")
    hist.set_ylabel("Share of detections in the group")
    hist.set_title("Positive FRP only, because log(0) is undefined")
    hist.legend(frameon=False)
    fig.suptitle(_scope_title(summary) + "\nFRP by satellite. Curves describe detections, not unique fires.")
    _finish(fig, path)


def _plot_brightness(tables: list[DetectionTable], summary: dict, path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 5.2), constrained_layout=True)
    for ax, column, title in (
        (axes[0], "brightness", "brightness, stored column name"),
        (axes[1], "bright_t31", "bright_t31, stored column name"),
    ):
        for satellite, table, positions in _series(tables):
            _ecdf(
                ax,
                _column(table, positions, column),
                DISPLAY_NAME.get(satellite, satellite),
                COLORS.get(satellite, "#444444"),
            )
        ax.set_xlabel(f"{column} (K, as stored)")
        ax.set_ylabel("Empirical cumulative share of detections")
        ax.set_title(title)
        ax.legend(frameon=False)
    fig.suptitle(
        _scope_title(summary)
        + "\nShared column names are not a cross-calibration. Extremes remain in the curves."
    )
    _finish(fig, path)


def _plot_modis_confidence(summary: dict, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(11.5, 4.8), constrained_layout=True)
    x = np.arange(101)
    for satellite in ("Terra", "Aqua"):
        block = summary["satellites"].get(satellite)
        if block is None or block["confidence"]["kind"] != "modis_0_100":
            continue
        counts = block["confidence"]["counts"]
        total = sum(counts.values())
        y = np.array([counts.get(str(value), 0) / total for value in x], dtype=float)
        ax.plot(x, y, color=COLORS[satellite], label=satellite, linewidth=1.3)
    ax.set_xlabel("MODIS confidence integer, 0 through 100")
    ax.set_ylabel("Share of that satellite's detections")
    ax.set_title("MODIS confidence only. VIIRS flags are not on this axis.")
    ax.legend(frameon=False)
    fig.suptitle(_scope_title(summary))
    _finish(fig, path)


def _plot_viirs_confidence(summary: dict, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 4.8), constrained_layout=True)
    flags = ["l", "n", "h"]
    x = np.arange(len(flags))
    satellites = [name for name in ("N20", "N21", "SNPP") if name in summary["satellites"]]
    width = 0.24
    for offset, satellite in enumerate(satellites):
        counts = summary["satellites"][satellite]["confidence"]["counts"]
        total = sum(counts.values()) or 1
        y = [counts.get(flag, 0) / total for flag in flags]
        ax.bar(
            x + (offset - (len(satellites) - 1) / 2) * width,
            y,
            width=width,
            color=COLORS[satellite],
            label=DISPLAY_NAME[satellite],
        )
    ax.set_xticks(x, flags)
    ax.set_xlabel("VIIRS confidence flag, as stored")
    ax.set_ylabel("Share of that satellite's detections")
    ax.set_title("VIIRS flags l, n, and h. They are not rescaled onto 0-100.")
    ax.legend(frameon=False)
    fig.suptitle(_scope_title(summary))
    _finish(fig, path)


def _plot_scan_track(tables: list[DetectionTable], summary: dict, path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 5.0), constrained_layout=True)
    series = _series(tables)
    for ax, column in ((axes[0], "scan"), (axes[1], "track")):
        values = [_column(table, positions, column) for _satellite, table, positions in series]
        labels = [DISPLAY_NAME.get(satellite, satellite) for satellite, _table, _positions in series]
        ax.boxplot(values, tick_labels=labels, whis=(0, 100), showfliers=False)
        ax.set_ylabel(f"{column} (km, as stored)")
        ax.set_title(column)
    fig.suptitle(
        _scope_title(summary)
        + "\nWhiskers run from the stored minimum to the stored maximum. Footprints are not harmonized."
    )
    _finish(fig, path)


def _plot_daynight(summary: dict, path: Path) -> None:
    names = [name for name in SATELLITE_ORDER if name in summary["satellites"]]
    fig, ax = plt.subplots(figsize=(8.5, 4.6), constrained_layout=True)
    y = np.arange(len(names))
    day = [summary["satellites"][name]["daynight"]["proportions"].get("D", 0.0) for name in names]
    night = [summary["satellites"][name]["daynight"]["proportions"].get("N", 0.0) for name in names]
    ax.barh(y, day, color="#d08a3a", label="D")
    ax.barh(y, night, left=day, color="#243044", label="N")
    ax.set_yticks(y, [DISPLAY_NAME[name] for name in names])
    ax.set_xlabel("Share of detections")
    ax.set_xlim(0, 1)
    ax.legend(frameon=False, loc="lower right")
    ax.set_title("Stored daynight flag. Not recomputed from local time.")
    fig.suptitle(_scope_title(summary))
    _finish(fig, path)


def _plot_hours(summary: dict, path: Path) -> None:
    names = [name for name in SATELLITE_ORDER if name in summary["satellites"]]
    fig, ax = plt.subplots(figsize=(11.5, 4.8), constrained_layout=True)
    hours = np.arange(24)
    for name in names:
        counts = summary["satellites"][name]["acquisition_hour_utc"]["counts"]
        ax.plot(hours, counts, color=COLORS[name], label=DISPLAY_NAME[name], linewidth=1.4)
    ax.set_xticks(hours)
    ax.set_xlabel("Acquisition hour (UTC)")
    ax.set_ylabel("Detections")
    ax.set_xlim(0, 23)
    ax.legend(frameon=False, ncol=5)
    ax.set_title("UTC hour from acq_time. This is not a local diurnal cycle and not a fire count.")
    fig.suptitle(_scope_title(summary))
    _finish(fig, path)


def _plot_density(tables: list[DetectionTable], summary: dict, path: Path, *, per_area: bool) -> None:
    count = len(tables)
    cols = 2 if count > 1 else 1
    rows = int(np.ceil(count / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(11.5, 3.5 * rows), constrained_layout=True)
    flat = np.atleast_1d(axes).ravel()
    for ax, table in zip(flat, tables):
        grid, lat_edges, lon_edges = count_grid(table.latitude, table.longitude, 1.0)
        shown = np.full(grid.shape, np.nan, dtype=float)
        positive = grid > 0
        if per_area:
            rate = detections_per_1000_km2(grid, lat_edges, lon_edges)
            shown[positive] = np.log10(rate[positive])
            label = "log10 detections per 1,000 km²"
        else:
            shown[positive] = np.log10(grid[positive].astype(float))
            label = "log10 detections"
        image = ax.imshow(
            np.ma.masked_invalid(shown),
            origin="lower",
            extent=[-180, 180, -90, 90],
            aspect="auto",
            cmap="cividis",
            interpolation="nearest",
        )
        ax.set_title(DISPLAY_NAME.get(table.source_id, table.source_id))
        ax.set_xlabel("Longitude (degrees)")
        ax.set_ylabel("Latitude (degrees)")
        fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04, label=label)
    for ax in flat[count:]:
        ax.set_visible(False)
    note = "Color scales are separate for each archive."
    if per_area:
        note += " Cell area is the spherical zone. Counts are detections, not unique fires."
    else:
        note += " Equal-degree cells are not equal area."
    fig.suptitle(_scope_title(summary) + "\n" + note)
    _finish(fig, path)


def _plot_extremes(summary: dict, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(11.5, 5.4), constrained_layout=True)
    by_satellite: dict[str, list[dict]] = {}
    for record in summary["extreme_frp"]["records"]:
        by_satellite.setdefault(record["satellite"], []).append(record)
    for satellite in SATELLITE_ORDER:
        records = by_satellite.get(satellite, [])
        if not records:
            continue
        ax.scatter(
            [record["longitude"] for record in records],
            [record["latitude"] for record in records],
            s=16,
            color=COLORS[satellite],
            label=f"{DISPLAY_NAME[satellite]} ({len(records)})",
            alpha=0.85,
            linewidths=0,
        )
    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)
    ax.set_xlabel("Longitude (degrees)")
    ax.set_ylabel("Latitude (degrees)")
    ax.set_title("FRP at or above the within-satellite 0.999 quantile. Axes are degrees, not equal area.")
    ax.legend(frameon=False, ncol=3)
    fig.suptitle(_scope_title(summary))
    _finish(fig, path)


def write_figures(tables: list[DetectionTable], summary: dict, figures_dir: Path) -> list[str]:
    figures_dir.mkdir(parents=True, exist_ok=True)
    _plot_frp(tables, summary, figures_dir / FIGURE_NAMES[0])
    _plot_brightness(tables, summary, figures_dir / FIGURE_NAMES[1])
    _plot_modis_confidence(summary, figures_dir / FIGURE_NAMES[2])
    _plot_viirs_confidence(summary, figures_dir / FIGURE_NAMES[3])
    _plot_scan_track(tables, summary, figures_dir / FIGURE_NAMES[4])
    _plot_daynight(summary, figures_dir / FIGURE_NAMES[5])
    _plot_hours(summary, figures_dir / FIGURE_NAMES[6])
    _plot_density(tables, summary, figures_dir / FIGURE_NAMES[7], per_area=False)
    _plot_density(tables, summary, figures_dir / FIGURE_NAMES[8], per_area=True)
    _plot_extremes(summary, figures_dir / FIGURE_NAMES[9])
    return list(FIGURE_NAMES)
