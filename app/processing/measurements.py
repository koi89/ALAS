"""
ALAS — Measurements
Topographic profiles, distances, areas, and volumetric calculations.
"""

import numpy as np
from typing import Tuple, Optional
from scipy.interpolate import RegularGridInterpolator

from app.core.point_cloud import PointCloudData
from app.core.raster_layer import RasterLayer
from app.config import DEFAULT_NODATA
from app.logger import get_logger

logger = get_logger("processing.measurements")


def extract_profile(raster: RasterLayer,
                     start: Tuple[float, float],
                     end: Tuple[float, float],
                     n_samples: int = 200) -> Tuple[np.ndarray, np.ndarray]:
    """
    Extracts a topographic profile between two points.
    Returns (distances, elevations).
    """
    logger.info(f"Profile: ({start[0]:.1f},{start[1]:.1f}) → ({end[0]:.1f},{end[1]:.1f})")

    data = raster.get_band(0)
    bounds = raster.bounds
    if bounds is None:
        raise ValueError("Raster without defined extent.")

    xmin, ymin, xmax, ymax = bounds
    rows, cols = data.shape

    # Create interpolator
    x_coords = np.linspace(xmin, xmax, cols)
    y_coords = np.linspace(ymax, ymin, rows)  # Y inverted

    valid_data = data.copy().astype(np.float64)
    valid_data[valid_data == raster.nodata] = np.nan

    interpolator = RegularGridInterpolator(
        (y_coords[::-1], x_coords), valid_data[::-1, :],
        method='linear', bounds_error=False, fill_value=np.nan
    )

    # Sample along the line
    xs = np.linspace(start[0], end[0], n_samples)
    ys = np.linspace(start[1], end[1], n_samples)
    sample_points = np.column_stack([ys, xs])

    elevations = interpolator(sample_points)

    # Cumulative distances
    dx = np.diff(xs)
    dy = np.diff(ys)
    segment_dists = np.sqrt(dx**2 + dy**2)
    distances = np.concatenate([[0], np.cumsum(segment_dists)])

    total_dist = distances[-1]
    logger.info(f"Profile: {total_dist:.1f}m, Z: {np.nanmin(elevations):.1f}-{np.nanmax(elevations):.1f}m")

    return distances, elevations


def extract_profile_from_cloud(pc: PointCloudData,
                                start: Tuple[float, float],
                                end: Tuple[float, float],
                                width: float = 1.0,
                                n_bins: int = 200) -> Tuple[np.ndarray, np.ndarray]:
    """
    Extracts a profile directly from the point cloud.
    Cuts a band of width 'width' between start and end.
    """
    logger.info(f"Cloud profile: ({start[0]:.1f},{start[1]:.1f}) → ({end[0]:.1f},{end[1]:.1f})")

    x, y, z = pc.xyz[:, 0], pc.xyz[:, 1], pc.xyz[:, 2]

    # Line direction
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = np.sqrt(dx**2 + dy**2)
    if length == 0:
        raise ValueError("Start and end are the same point.")

    # Normalize
    ux, uy = dx / length, dy / length
    # Perpendicular
    px, py = -uy, ux

    # Project points onto the line
    rx = x - start[0]
    ry = y - start[1]
    along = rx * ux + ry * uy   # Distance along
    across = rx * px + ry * py  # Perpendicular distance

    # Filter points within the width
    mask = (along >= 0) & (along <= length) & (np.abs(across) <= width / 2)

    along_filt = along[mask]
    z_filt = z[mask]

    if len(along_filt) == 0:
        raise ValueError("No points within the profile.")

    # Bin into segments
    bins = np.linspace(0, length, n_bins + 1)
    bin_idx = np.digitize(along_filt, bins) - 1
    bin_idx = np.clip(bin_idx, 0, n_bins - 1)

    distances = (bins[:-1] + bins[1:]) / 2
    elevations = np.full(n_bins, np.nan)

    for i in range(n_bins):
        points_in_bin = z_filt[bin_idx == i]
        if len(points_in_bin) > 0:
            elevations[i] = np.mean(points_in_bin)

    return distances, elevations


def measure_3d_distance(point_a: Tuple[float, float, float],
                         point_b: Tuple[float, float, float]) -> dict:
    """Calculates 3D distance, horizontal distance, and elevation difference between two points."""
    dx = point_b[0] - point_a[0]
    dy = point_b[1] - point_a[1]
    dz = point_b[2] - point_a[2]

    dist_2d = np.sqrt(dx**2 + dy**2)
    dist_3d = np.sqrt(dx**2 + dy**2 + dz**2)
    slope_pct = (dz / dist_2d * 100) if dist_2d > 0 else 0
    slope_deg = np.degrees(np.arctan2(dz, dist_2d))

    return {
        "distance_3d": float(dist_3d),
        "distance_2d": float(dist_2d),
        "dz": float(dz),
        "slope_percent": float(slope_pct),
        "slope_degrees": float(slope_deg),
    }


def measure_area(raster: RasterLayer, polygon: np.ndarray) -> dict:
    """
    Calculates the real surface area (considering relief) within a polygon.
    polygon: (N, 2) array of vertices [x, y].
    """
    from matplotlib.path import Path as MplPath

    data = raster.get_band(0)
    bounds = raster.bounds
    if bounds is None:
        raise ValueError("Raster without extent.")

    xmin, ymin, xmax, ymax = bounds
    rows, cols = data.shape
    res_x = (xmax - xmin) / cols
    res_y = (ymax - ymin) / rows

    # Create coordinate grid
    xs = np.linspace(xmin + res_x/2, xmax - res_x/2, cols)
    ys = np.linspace(ymax - res_y/2, ymin + res_y/2, rows)
    xx, yy = np.meshgrid(xs, ys)

    # Polygon mask
    points = np.column_stack([xx.ravel(), yy.ravel()])
    path = MplPath(polygon)
    mask = path.contains_points(points).reshape(rows, cols)

    # Planimetric area
    plan_area = np.sum(mask) * res_x * res_y

    # Surface area (considering slope)
    valid = mask & (data != raster.nodata)
    if np.sum(valid) > 0:
        dy, dx = np.gradient(data, res_y, res_x)
        slope_factor = np.sqrt(1 + dx**2 + dy**2)
        surface_area = np.sum(slope_factor[valid]) * res_x * res_y
    else:
        surface_area = plan_area

    return {
        "planimetric_area_m2": float(plan_area),
        "surface_area_m2": float(surface_area),
        "planimetric_area_ha": float(plan_area / 10000),
    }


def calculate_volume(raster: RasterLayer, reference_z: float,
                      polygon: np.ndarray = None) -> dict:
    """
    Calculates cut and fill volumes relative to a Z reference plane.
    """
    logger.info(f"Calculating volume (ref_z={reference_z:.2f}m)")

    data = raster.get_band(0).copy()
    res = raster.resolution
    if res is None:
        raise ValueError("Unknown resolution.")

    cell_area = res[0] * res[1]

    if polygon is not None:
        from matplotlib.path import Path as MplPath
        bounds = raster.bounds
        if bounds is None:
            raise ValueError("Raster without extent.")
        xmin, ymin, xmax, ymax = bounds
        rows, cols = data.shape
        res_x = (xmax - xmin) / cols
        res_y = (ymax - ymin) / rows
        xs = np.linspace(xmin + res_x/2, xmax - res_x/2, cols)
        ys = np.linspace(ymax - res_y/2, ymin + res_y/2, rows)
        xx, yy = np.meshgrid(xs, ys)
        points = np.column_stack([xx.ravel(), yy.ravel()])
        path = MplPath(polygon)
        mask = path.contains_points(points).reshape(rows, cols)
    else:
        bounds = raster.bounds
        if bounds is None:
            raise ValueError("Raster without extent.")
        xmin, ymin, xmax, ymax = bounds
        rows, cols = data.shape
        res_x = (xmax - xmin) / cols
        res_y = (ymax - ymin) / rows
        xs = np.linspace(xmin + res_x/2, xmax - res_x/2, cols)
        ys = np.linspace(ymax - res_y/2, ymin + res_y/2, rows)
        xx, yy = np.meshgrid(xs, ys)
        mask = data != raster.nodata

    valid = mask & (data != raster.nodata)
    diff = data[valid] - reference_z

    cut = np.sum(diff[diff > 0]) * cell_area
    fill = np.sum(np.abs(diff[diff < 0])) * cell_area
    net = cut - fill

    # Prepare 2D grid for 3D Volume solid rendering
    zz = data.astype(np.float32).copy()
    zz[~valid] = np.nan

    result = {
        "cut_volume_m3": float(cut),
        "fill_volume_m3": float(fill),
        "net_volume_m3": float(net),
        "area_m2": float(np.sum(valid) * cell_area),
        "grid_x": xx,
        "grid_y": yy,
        "grid_z": zz,
    }

    logger.info(f"Cut: {cut:.1f}m³ | Fill: {fill:.1f}m³ | Net: {net:.1f}m³")
    return result

