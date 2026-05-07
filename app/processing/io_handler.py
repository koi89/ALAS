"""
ALAS — I/O Handler
Reading and writing LAS/LAZ files with laspy and PDAL.
"""

import json
import numpy as np
from pathlib import Path
from typing import Optional, List

from app.core.point_cloud import PointCloudData
from app.logger import get_logger

logger = get_logger("processing.io")


def read_las(path: str) -> PointCloudData:
    """Reads a LAS/LAZ file using laspy."""
    return PointCloudData.from_file(path)


def write_las(pc: PointCloudData, path: str, compress: bool = True):
    """Writes a LAS/LAZ file."""
    pc.to_file(path, compress=compress)


def read_with_pdal(path: str, extra_stages: list = None) -> np.ndarray:
    """
    Reads a file using a PDAL pipeline.
    Returns a structured NumPy array.
    """
    import pdal

    pipeline_stages = [{"type": "readers.las", "filename": str(path)}]
    if extra_stages:
        pipeline_stages.extend(extra_stages)

    pipeline_json = json.dumps(pipeline_stages)
    pipeline = pdal.Pipeline(pipeline_json)
    count = pipeline.execute()
    logger.info(f"PDAL processed {count:,} points from {Path(path).name}")

    arrays = pipeline.arrays
    if arrays:
        return arrays[0]
    return np.array([])


def pdal_pipeline_execute(stages: list) -> np.ndarray:
    """
    Executes an arbitrary PDAL pipeline.
    stages: list of PDAL stage dictionaries.
    """
    import pdal

    pipeline_json = json.dumps(stages)
    pipeline = pdal.Pipeline(pipeline_json)
    count = pipeline.execute()
    logger.info(f"PDAL pipeline executed: {count:,} points")

    arrays = pipeline.arrays
    if arrays:
        return arrays[0]
    return np.array([])


def get_file_info(path: str) -> dict:
    """Gets basic information from a LAS/LAZ file without reading all points."""
    import laspy

    with laspy.open(str(path)) as reader:
        header = reader.header
        # system_identifier can be bytes or str depending on laspy version
        sys_id = header.system_identifier
        if isinstance(sys_id, bytes):
            system_id = sys_id.decode('utf-8', errors='ignore').strip()
        else:
            system_id = str(sys_id).strip() if sys_id else None
        info = {
            "file": str(path),
            "version": f"{header.version.major}.{header.version.minor}",
            "point_format": header.point_format.id,
            "point_count": header.point_count,
            "system_identifier": system_id,
            "scale": list(header.scales),
            "offset": list(header.offsets),
            "mins": list(header.mins),
            "maxs": list(header.maxs),
        }
    return info


def merge_files(paths: List[str]) -> PointCloudData:
    """Merges multiple LAS/LAZ files."""
    clouds = [PointCloudData.from_file(p) for p in paths]
    return PointCloudData.merge(clouds, "merged")
