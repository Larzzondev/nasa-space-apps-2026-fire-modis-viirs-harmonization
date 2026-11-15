"""Figures for the July 2024 monthly extracts."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from fire_data.eda_figures import COLORS
from fire_data.ingest import period_dates
from fire_data.monthly_scan import SATELLITE_ORDER

FIGURE_NAMES = (
    "daily_rows_delivered.png",
    "frp_log_hist_by_satellite.png",
    "confidence_modis.png",
    "confidence_viirs.png",
    "daynight_by_satellite.png",
    "brightness_by_satellite.png",
    "spatial_log_counts.png",
)


def _finish(fig: plt.Figure, path: Path) -> None:
    fig.savefig(path, dpi=140)
    plt.close(fig)


def _daily_series(scan: dict, satellite: str) -> np.ndarray:
    counts = scan["daily"].get(satellite, {})
    values = []
    for day in period_dates():
        delivered = counts.get(day, 0)
        values.append(np.nan if delivered == 0 else delivered)
    return np.asarray(values, dtype=np.float64)


def write_figures(scans: list[dict], output_dir: Path) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    by_sensor = {scan["sensor"]: scan for scan in scans}
    written = [
        _daily(scans, output_dir / FIGURE_NAMES[0]),
        _frp(scans, output_dir / FIGURE_NAMES[1]),
        _modis_confidence(by_sensor["modis"], output_dir / FIGURE_NAMES[2]),
        _viirs_confidence(scans, output_dir / FIGURE_NAMES[3]),
        _daynight(scans, output_dir / FIGURE_NAMES[4]),
        _brightness(scans, output_dir / FIGURE_NAMES[5]),
        _spatial(scans, output_dir / FIGURE_NAMES[6]),
    ]
    return [path.name for path in written]


def _daily(scans: list[dict], path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(11.5, 5.2), constrained_layout=True)
    days = np.arange(1, 32)
    for scan in scans:
        for satellite in sorted(scan["daily"]):
            ax.plot(days, _daily_series(scan, satellite), color=COLORS[satellite], label=satellite, linewidth=1.4)
    ax.set_xlabel("July 2024 day")
    ax.set_ylabel("Rows delivered")
    ax.set_title("Rows delivered by acquisition date")
    ax.set_xticks(days[::2])
    ax.legend(frameon=False, ncol=5)
    ax.text(
        0.0,
        -0.18,
        "A break means that archive has no row for the date. It is not a zero-fire measurement.",
        transform=ax.transAxes,
        fontsize=8,
    )
    _finish(fig, path)
    return path


def _frp(scans: list[dict], path: Path) -> Path:
    fig, axes = plt.subplots(1, 5, figsize=(14.5, 3.6), sharey=True, constrained_layout=True)
    satellites = [satellite for scan in scans for satellite in SATELLITE_ORDER if satellite in scan["arrays"]]
    for ax, satellite in zip(axes, satellites):
        scan = next(item for item in scans if satellite in item["arrays"])
        frp = scan["arrays"][satellite]["frp"]
        positive = frp[frp > 0]
        if positive.size:
            ax.hist(np.log10(positive), bins=40, color=COLORS[satellite])
        ax.set_title(satellite)
        ax.set_xlabel("log10 FRP")
    axes[0].set_ylabel("Rows")
    fig.suptitle("FRP among rows with FRP greater than zero. FRP is not fire size.")
    _finish(fig, path)
    return path


def _modis_confidence(scan: dict, path: Path) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), sharey=True, constrained_layout=True)
    for ax, satellite in zip(axes, ("Terra", "Aqua")):
        counts = np.zeros(101, dtype=np.int64)
        for key, count in scan["confidence"].items():
            sat, label = key.split("|", 1)
            if sat == satellite and label.isdigit():
                counts[int(label)] = count
        ax.bar(np.arange(101), counts, color=COLORS[satellite], width=1.0)
        ax.set_title(f"{satellite} confidence, 0–100")
        ax.set_xlabel("Stored integer")
    axes[0].set_ylabel("Rows")
    _finish(fig, path)
    return path


def _viirs_confidence(scans: list[dict], path: Path) -> Path:
    flags = ("l", "n", "h")
    satellites = ("N20", "N21", "SNPP")
    fig, ax = plt.subplots(figsize=(8.2, 4.4), constrained_layout=True)
    x = np.arange(len(satellites))
    width = 0.24
    for offset, flag in enumerate(flags):
        heights = []
        for satellite in satellites:
            scan = next(item for item in scans if satellite in item["daily"])
            heights.append(scan["confidence"].get(f"{satellite}|{flag}", 0))
        ax.bar(x + (offset - 1) * width, heights, width=width, label=flag)
    ax.set_xticks(x, satellites)
    ax.set_ylabel("Rows")
    ax.set_title("VIIRS confidence flags, stored separately from MODIS integers")
    ax.legend(frameon=False, title="flag")
    _finish(fig, path)
    return path


def _daynight(scans: list[dict], path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8.2, 4.4), constrained_layout=True)
    satellites = [satellite for satellite in SATELLITE_ORDER if any(satellite in scan["daily"] for scan in scans)]
    x = np.arange(len(satellites))
    day = []
    night = []
    for satellite in satellites:
        scan = next(item for item in scans if satellite in item["daily"])
        day.append(scan["daynight"].get(f"{satellite}|D", 0))
        night.append(scan["daynight"].get(f"{satellite}|N", 0))
    ax.bar(x, day, color="#d6a35c", label="D")
    ax.bar(x, night, bottom=day, color="#31465a", label="N")
    ax.set_xticks(x, satellites)
    ax.set_ylabel("Rows")
    ax.set_title("Archive day/night flag")
    ax.legend(frameon=False)
    _finish(fig, path)
    return path


def _brightness(scans: list[dict], path: Path) -> Path:
    fig, axes = plt.subplots(1, 5, figsize=(14.5, 3.6), sharey=False, constrained_layout=True)
    satellites = [satellite for satellite in SATELLITE_ORDER if any(satellite in scan["arrays"] for scan in scans)]
    for ax, satellite in zip(axes, satellites):
        scan = next(item for item in scans if satellite in item["arrays"])
        values = scan["arrays"][satellite]["brightness"]
        ax.hist(values, bins=40, color=COLORS[satellite])
        if satellite in {"N20", "N21", "SNPP"}:
            ax.axvline(367.0, color="#111111", linewidth=0.8)
        ax.set_title(satellite)
        ax.set_xlabel("Brightness")
    axes[0].set_ylabel("Rows")
    fig.suptitle("Stored brightness. The line at 367 K marks the exact stored VIIRS value.")
    _finish(fig, path)
    return path


def _spatial(scans: list[dict], path: Path) -> Path:
    fig, axes = plt.subplots(5, 1, figsize=(10.5, 12.5), constrained_layout=True)
    satellites = [satellite for satellite in SATELLITE_ORDER if any(satellite in scan["arrays"] for scan in scans)]
    for ax, satellite in zip(axes, satellites):
        scan = next(item for item in scans if satellite in item["arrays"])
        lat = scan["arrays"][satellite]["latitude"]
        lon = scan["arrays"][satellite]["longitude"]
        counts, lon_edges, lat_edges = np.histogram2d(lon, lat, bins=[360, 180], range=[[-180, 180], [-90, 90]])
        display = np.full(counts.T.shape, np.nan, dtype=np.float64)
        positive = counts.T > 0
        display[positive] = np.log10(counts.T[positive])
        image = ax.imshow(
            display,
            origin="lower",
            extent=[lon_edges[0], lon_edges[-1], lat_edges[0], lat_edges[-1]],
            aspect="auto",
            cmap="YlOrRd",
            interpolation="nearest",
        )
        ax.set_ylabel(satellite)
        ax.set_xlim(-180, 180)
        ax.set_ylim(-90, 90)
        fig.colorbar(image, ax=ax, fraction=0.02, pad=0.01, label="log10 rows")
    axes[-1].set_xlabel("Longitude")
    fig.suptitle("Delivered rows in 1-degree cells. Cell counts are archive rows, not fires.")
    _finish(fig, path)
    return path
