"""
ALAS — Contour Line Generation
Extracts elevation iso-lines from a DTM/DSM raster using matplotlib contouring.
"""

from __future__ import annotations
from typing import Optional
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from app.core.raster_layer import RasterLayer
from app.logger import get_logger

logger = get_logger("processing.contours")


def generate_contours(
    raster: RasterLayer,
    interval: float,
    min_elev: Optional[float] = None,
    max_elev: Optional[float] = None,
) -> list[dict]:
    """
    Extract elevation contour lines from a raster at the given vertical interval.

    Returns a list of dicts:
        {"elevation": float, "xy": np.ndarray shape (N, 2)}
    where xy contains projected XY coordinates matching the raster CRS.
    """

    data = raster.get_band(0)
    nodata = raster.nodata
    bounds = raster.bounds
    if bounds is None:
        raise ValueError("Raster has no defined extent.")

    xmin, ymin, xmax, ymax = bounds
    rows, cols = data.shape

    mask = (data == nodata) | np.isnan(data)
    z = np.ma.array(data, mask=mask).astype(np.float64)

    valid_z = z.compressed()
    if valid_z.size == 0:
        raise ValueError("Raster has no valid data.")

    lo = float(min_elev) if min_elev is not None else float(np.floor(valid_z.min() / interval) * interval)
    hi = float(max_elev) if max_elev is not None else float(np.ceil(valid_z.max() / interval) * interval)

    levels = np.arange(lo, hi + interval * 0.01, interval)
    if levels.size == 0:
        raise ValueError("No contour levels in the elevation range.")
    if levels.size > 2000:
        raise ValueError(
            f"Too many contour levels ({levels.size}). Increase the interval."
        )

    # Pixel-center coordinate grids — row 0 = ymax (north)
    xs = np.linspace(xmin, xmax, cols)
    ys = np.linspace(ymax, ymin, rows)
    xx, yy = np.meshgrid(xs, ys)

    fig, ax = plt.subplots()
    try:
        cs = ax.contour(xx, yy, z, levels=levels)
    finally:
        plt.close(fig)

    contours = []
    for level, segs in zip(cs.levels, cs.allsegs):
        for seg in segs:
            if len(seg) >= 2:
                contours.append({
                    "elevation": float(level),
                    "xy": np.asarray(seg, dtype=np.float64),
                })

    logger.info(
        f"Generated {len(contours)} contour segments at interval {interval} m"
    )
    return contours


def render_contour_figure(contours: list[dict], interval: float,
                          bounds=None) -> str:
    """
    Render the contour lines to a temporary PNG file using matplotlib.
    Returns the path to the PNG file.
    """
    import tempfile
    from matplotlib.cm import get_cmap
    from matplotlib.colors import Normalize

    if not contours:
        raise ValueError("No contours to render.")

    elevations = [c["elevation"] for c in contours]
    lo, hi = min(elevations), max(elevations)
    norm = Normalize(vmin=lo, vmax=hi)
    cmap = get_cmap("terrain")

    fig, ax = plt.subplots(figsize=(10, 8), facecolor="#1a1a2e")
    ax.set_facecolor("#1a1a2e")

    for c in contours:
        xy = c["xy"]
        color = cmap(norm(c["elevation"]))
        ax.plot(xy[:, 0], xy[:, 1], color=color, linewidth=0.8)

    # Label a subset of unique elevations
    unique_elevs = sorted(set(elevations))
    label_step = max(1, len(unique_elevs) // 10)
    labeled = set()
    for c in contours:
        elev = c["elevation"]
        if elev not in labeled and unique_elevs.index(elev) % label_step == 0:
            xy = c["xy"]
            mid = len(xy) // 2
            ax.annotate(
                f"{elev:.0f} m",
                xy=(xy[mid, 0], xy[mid, 1]),
                fontsize=6,
                color="white",
                ha="center",
            )
            labeled.add(elev)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cb = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02)
    cb.set_label("Elevation (m)", color="white", fontsize=9)
    cb.ax.yaxis.set_tick_params(color="white")
    plt.setp(cb.ax.yaxis.get_ticklabels(), color="white")

    ax.set_aspect("equal")
    ax.set_title(f"Contour Lines — interval {interval} m", color="white", fontsize=12)
    ax.tick_params(colors="white", labelsize=7)
    for spine in ax.spines.values():
        spine.set_edgecolor("#444")

    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False, prefix="alas_contours_")
    fig.savefig(tmp.name, dpi=120, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    logger.info(f"Contour figure saved to {tmp.name}")
    return tmp.name


def export_contours(contours: list[dict], path: str, crs_epsg: int = None):
    """Export contour lines as Shapefile, GeoJSON, or GeoPackage by file extension."""
    from shapely.geometry import LineString
    from app.processing.exporters import export_vector

    geometries = []
    attributes = []
    for c in contours:
        xy = c["xy"]
        if len(xy) >= 2:
            geometries.append(LineString(xy.tolist()))
            attributes.append({"elevation": round(c["elevation"], 3)})

    if not geometries:
        raise ValueError("No contour lines to export.")

    export_vector(geometries, attributes, path, crs_epsg=crs_epsg)
    logger.info(f"Exported {len(geometries)} contour lines → {path}")
