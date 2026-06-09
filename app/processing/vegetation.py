"""
ALAS — Vegetation Analysis
CHM, tree detection, crown segmentation, canopy statistics.
"""

import numpy as np
from typing import Optional, Tuple, List, Dict
from scipy import ndimage

from app.core.raster_layer import RasterLayer
from app.config import (
    DEFAULT_NODATA, DEFAULT_MIN_TREE_HEIGHT,
    DEFAULT_CROWN_WINDOW, DEFAULT_CANOPY_CELL_SIZE
)
from app.logger import get_logger

logger = get_logger("processing.vegetation")


def detect_tree_tops(chm: RasterLayer, min_height: float = None,
                      window_size: int = None) -> np.ndarray:
    """
    Detects tree tops as local maxima in the CHM.
    Returns array (N, 3) with coordinates [x, y, height].
    """
    min_height = min_height or DEFAULT_MIN_TREE_HEIGHT
    window_size = window_size or DEFAULT_CROWN_WINDOW

    logger.info(f"Detecting trees (min_h={min_height}m, window={window_size}px)")

    data = chm.get_band(0).copy()
    data[data == chm.nodata] = 0

    # Local maxima
    local_max = ndimage.maximum_filter(data, size=window_size)
    is_peak = (data == local_max) & (data >= min_height)

    # Peak coordinates
    rows, cols = np.where(is_peak)
    heights = data[rows, cols]

    # Convert pixel coords to geo coords
    if chm.transform:
        xs = chm.transform.c + cols * chm.transform.a + chm.transform.a / 2
        ys = chm.transform.f + rows * chm.transform.e + chm.transform.e / 2
    elif chm.bounds:
        xmin, ymin, xmax, ymax = chm.bounds
        xs = xmin + cols * (xmax - xmin) / data.shape[1]
        ys = ymax - rows * (ymax - ymin) / data.shape[0]
    else:
        xs = cols.astype(float)
        ys = rows.astype(float)

    tree_tops = np.column_stack([xs, ys, heights])

    logger.info(f"Detected {len(tree_tops)} trees (h: {heights.min():.1f} - {heights.max():.1f} m)")
    return tree_tops


def segment_crowns(chm: RasterLayer, tree_tops: np.ndarray,
                    method: str = "watershed") -> np.ndarray:
    """
    Segments individual crowns using watershed.
    Returns a label raster (each tree = one ID).
    """
    logger.info(f"Segmenting crowns ({method})...")
    from skimage.segmentation import watershed
    from skimage.feature import peak_local_max

    data = chm.get_band(0).copy()
    data[data == chm.nodata] = 0

    # Create markers from tree_tops
    markers = np.zeros_like(data, dtype=np.int32)

    if chm.transform:
        for i, (x, y, h) in enumerate(tree_tops):
            col = int((x - chm.transform.c) / chm.transform.a - 0.5)
            row = int((y - chm.transform.f) / chm.transform.e - 0.5)
            if 0 <= row < data.shape[0] and 0 <= col < data.shape[1]:
                markers[row, col] = i + 1
    elif chm.bounds:
        xmin, ymin, xmax, ymax = chm.bounds
        for i, (x, y, h) in enumerate(tree_tops):
            col = int((x - xmin) / (xmax - xmin) * data.shape[1])
            row = int((ymax - y) / (ymax - ymin) * data.shape[0])
            if 0 <= row < data.shape[0] and 0 <= col < data.shape[1]:
                markers[row, col] = i + 1

    # Watershed (invert CHM so crowns become basins)
    mask = data > 0.5  # Only vegetation zones
    labels = watershed(-data, markers=markers, mask=mask)

    n_trees = len(np.unique(labels)) - 1  # Exclude 0 (background)
    logger.info(f"Segmented {n_trees} individual crowns")

    return labels, data


def build_crown_raster(chm: RasterLayer,
                       height_map: np.ndarray,
                       labels: np.ndarray) -> RasterLayer:
    """
    Builds a segmented crown raster.
    Each crown pixel takes the maximum height of its segment.
    """
    logger.info("Building segmented crown raster...")

    crown_data = np.full(labels.shape, chm.nodata, dtype=np.float32)
    unique_ids = np.unique(labels)
    unique_ids = unique_ids[unique_ids > 0]

    for tree_id in unique_ids:
        mask = labels == tree_id
        if not mask.any():
            continue
        crown_data[mask] = float(np.max(height_map[mask]))

    bounds = chm.bounds
    if bounds is None:
        raise ValueError("Cannot build crown raster without valid bounds.")

    result = RasterLayer.from_array(
        crown_data,
        bounds,
        epsg=chm.crs_epsg,
        nodata=chm.nodata,
        name="Vegetation_crowns"
    )
    result.crs = chm.crs
    return result


def compute_canopy_stats(chm: RasterLayer,
                          labels: np.ndarray) -> List[Dict]:
    """
    Calculates statistics per segmented crown.
    Returns list of dicts with: id, x, y, max_height, mean_height, area_m2.
    """
    logger.info("Calculating crown statistics...")

    data = chm.get_band(0).copy()
    data[data == chm.nodata] = 0

    res_x = chm.resolution[0] if chm.resolution else 1.0
    res_y = chm.resolution[1] if chm.resolution else 1.0
    cell_area = res_x * res_y

    unique_ids = np.unique(labels)
    unique_ids = unique_ids[unique_ids > 0]  # Exclude background

    stats = []
    for tree_id in unique_ids:
        mask = labels == tree_id
        heights = data[mask]

        if len(heights) == 0:
            continue

        # Centroid
        rows, cols = np.where(mask)
        mean_row = rows.mean()
        mean_col = cols.mean()

        if chm.transform:
            cx = chm.transform.c + (mean_col + 0.5) * chm.transform.a
            cy = chm.transform.f + (mean_row + 0.5) * chm.transform.e
        else:
            cx, cy = mean_col, mean_row

        stats.append({
            "id": int(tree_id),
            "x": float(cx),
            "y": float(cy),
            "max_height": float(heights.max()),
            "mean_height": float(heights.mean()),
            "area_m2": float(len(heights) * cell_area),
            "n_pixels": int(len(heights)),
        })

    logger.info(f"Statistics calculated for {len(stats)} trees")
    return stats


def density_map(chm: RasterLayer, cell_size: float = None) -> RasterLayer:
    """
    Generates vegetation density map.
    Percentage of canopy coverage per cell of configurable size.
    """
    cell_size = cell_size or DEFAULT_CANOPY_CELL_SIZE
    logger.info(f"Calculating density map (cell={cell_size}m)")

    data = chm.get_band(0).copy()
    data[data == chm.nodata] = 0

    res = chm.resolution[0] if chm.resolution else 1.0
    block_size = max(1, int(cell_size / res))

    rows, cols = data.shape
    out_rows = rows // block_size
    out_cols = cols // block_size

    density = np.zeros((out_rows, out_cols), dtype=np.float32)

    for r in range(out_rows):
        for c in range(out_cols):
            block = data[
                r * block_size: (r + 1) * block_size,
                c * block_size: (c + 1) * block_size
            ]
            total = block.size
            canopy = np.sum(block > DEFAULT_MIN_TREE_HEIGHT)
            density[r, c] = (canopy / total * 100) if total > 0 else 0

    bounds = chm.bounds
    if bounds:
        xmin, ymin, xmax, ymax = bounds
        new_xmax = xmin + out_cols * cell_size
        new_ymin = ymax - out_rows * cell_size
        bounds = (xmin, new_ymin, new_xmax, ymax)

    result = RasterLayer.from_array(
        density, bounds, epsg=chm.crs_epsg,
        nodata=DEFAULT_NODATA, name="Vegetation_density"
    )
    result.crs = chm.crs

    logger.info(f"Mean density: {np.mean(density):.1f}%")
    return result
