"""
ALAS — Multitemporal Analysis
Comparison of DEMs and point clouds from different dates, change detection.
"""

import numpy as np
from typing import Optional, Dict

from app.core.raster_layer import RasterLayer
from app.config import DEFAULT_NODATA, DEFAULT_DOD_THRESHOLD
from app.logger import get_logger

logger = get_logger("processing.multitemporal")


def compute_dod(dem_before: RasterLayer,
                dem_after: RasterLayer,
                name: str = "DoD") -> RasterLayer:
    """
    Calculates DEM Difference (DoD) = DEM_after - DEM_before.
    Positive values = deposition/growth.
    Negative values = erosion/loss.
    """
    logger.info("Calculating DoD (DEM Difference)...")

    d_before = dem_before.get_band(0).copy()
    d_after = dem_after.get_band(0).copy()

    # Align dimensions
    min_r = min(d_before.shape[0], d_after.shape[0])
    min_c = min(d_before.shape[1], d_after.shape[1])
    d_before = d_before[:min_r, :min_c]
    d_after = d_after[:min_r, :min_c]

    # Valid data mask
    valid = (d_before != dem_before.nodata) & (d_after != dem_after.nodata)

    dod = np.full_like(d_before, DEFAULT_NODATA, dtype=np.float32)
    dod[valid] = d_after[valid] - d_before[valid]

    result = RasterLayer.from_array(
        dod, dem_before.bounds, epsg=dem_before.crs_epsg,
        nodata=DEFAULT_NODATA, name=name
    )
    result.transform = dem_before.transform
    result.crs = dem_before.crs

    stats = change_statistics(result)
    logger.info(
        f"DoD: gain={stats['volume_gain_m3']:.1f}m³, "
        f"loss={stats['volume_loss_m3']:.1f}m³, "
        f"net={stats['net_change_m3']:.1f}m³"
    )
    return result


def classify_changes(dod: RasterLayer,
                      threshold: float = None) -> RasterLayer:
    """
    Classifies changes in the DoD:
    1 = significant erosion (negative < -threshold)
    2 = significant deposition (positive > threshold)
    3 = stable (within ±threshold)
    """
    threshold = threshold or DEFAULT_DOD_THRESHOLD
    logger.info(f"Classifying changes (threshold=±{threshold}m)...")

    data = dod.get_band(0).copy()
    result = np.full_like(data, DEFAULT_NODATA, dtype=np.float32)

    valid = data != dod.nodata

    result[valid & (data < -threshold)] = 1  # Erosion
    result[valid & (data > threshold)] = 2   # Deposition
    result[valid & (data >= -threshold) & (data <= threshold)] = 3  # Stable

    rl = RasterLayer.from_array(
        result, dod.bounds, epsg=dod.crs_epsg,
        nodata=DEFAULT_NODATA, name="Classified_changes"
    )
    rl.transform = dod.transform
    rl.crs = dod.crs

    # Stats
    erosion_pct = np.sum(result == 1) / np.sum(valid) * 100 if np.sum(valid) > 0 else 0
    deposition_pct = np.sum(result == 2) / np.sum(valid) * 100 if np.sum(valid) > 0 else 0
    stable_pct = np.sum(result == 3) / np.sum(valid) * 100 if np.sum(valid) > 0 else 0
    logger.info(
        f"Erosion: {erosion_pct:.1f}% | "
        f"Deposition: {deposition_pct:.1f}% | "
        f"Stable: {stable_pct:.1f}%"
    )
    return rl


def change_statistics(dod: RasterLayer,
                       mask: np.ndarray = None) -> Dict[str, float]:
    """
    Change statistics from the DoD.
    """
    data = dod.get_band(0).copy()
    valid = data != dod.nodata

    if mask is not None:
        valid = valid & mask

    if not valid.any():
        return {
            "volume_gain_m3": 0, "volume_loss_m3": 0,
            "net_change_m3": 0, "mean_change_m": 0,
            "max_gain_m": 0, "max_loss_m": 0,
            "area_changed_m2": 0,
        }

    values = data[valid]
    res = dod.resolution
    cell_area = res[0] * res[1] if res else 1.0

    positive = values[values > 0]
    negative = values[values < 0]

    volume_gain = float(np.sum(positive) * cell_area)
    volume_loss = float(np.sum(np.abs(negative)) * cell_area)
    net = volume_gain - volume_loss

    threshold = DEFAULT_DOD_THRESHOLD
    changed = np.abs(values) > threshold
    area_changed = float(np.sum(changed) * cell_area)

    return {
        "volume_gain_m3": volume_gain,
        "volume_loss_m3": volume_loss,
        "net_change_m3": net,
        "mean_change_m": float(np.mean(values)),
        "max_gain_m": float(np.max(values)) if len(values) > 0 else 0,
        "max_loss_m": float(np.min(values)) if len(values) > 0 else 0,
        "std_change_m": float(np.std(values)),
        "area_changed_m2": area_changed,
        "area_changed_ha": area_changed / 10000,
    }


def detect_deforestation(chm_before: RasterLayer,
                          chm_after: RasterLayer,
                          height_threshold: float = 2.0) -> RasterLayer:
    """
    Detects deforested areas: where the CHM decreased significantly.
    """
    logger.info("Detecting deforestation...")

    d_before = chm_before.get_band(0).copy()
    d_after = chm_after.get_band(0).copy()

    min_r = min(d_before.shape[0], d_after.shape[0])
    min_c = min(d_before.shape[1], d_after.shape[1])
    d_before = d_before[:min_r, :min_c]
    d_after = d_after[:min_r, :min_c]

    valid = (d_before != chm_before.nodata) & (d_after != chm_after.nodata)

    result = np.full_like(d_before, DEFAULT_NODATA, dtype=np.float32)

    # Zones where there was tall vegetation and no longer is
    had_trees = d_before > height_threshold
    lost_trees = d_after < height_threshold
    deforested = valid & had_trees & lost_trees

    result[deforested] = 1       # Deforested
    result[valid & ~deforested] = 0  # No significant change

    rl = RasterLayer.from_array(
        result, chm_before.bounds, epsg=chm_before.crs_epsg,
        nodata=DEFAULT_NODATA, name="Deforestation"
    )
    rl.transform = chm_before.transform
    rl.crs = chm_before.crs

    deforested_area = np.sum(deforested)
    if chm_before.resolution:
        area_m2 = deforested_area * chm_before.resolution[0] * chm_before.resolution[1]
        logger.info(f"Deforested area: {area_m2:.0f} m² ({area_m2/10000:.2f} ha)")

    return rl
