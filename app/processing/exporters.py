"""
ALAS — Exporters
Export to GeoTIFF, OBJ, Shapefile, GeoJSON, and PDF.
"""

import numpy as np
from pathlib import Path
from typing import Optional, List, Dict

from app.core.point_cloud import PointCloudData
from app.core.raster_layer import RasterLayer
from app.config import DEFAULT_GEOTIFF_COMPRESS, DEFAULT_NODATA
from app.logger import get_logger

logger = get_logger("processing.exporters")


def export_point_cloud(pc: PointCloudData, path: str,
                        compress: bool = True):
    """Exports point cloud to LAS/LAZ."""
    pc.to_file(path, compress=compress)


def export_geotiff(raster: RasterLayer, path: str,
                    compress: str = None):
    """Exports raster to GeoTIFF."""
    raster.to_geotiff(path, compress=compress or DEFAULT_GEOTIFF_COMPRESS)


def export_mesh_obj(vertices: np.ndarray, faces: np.ndarray,
                     path: str):
    """
    Exports a 3D mesh to OBJ format.
    vertices: (N, 3) array of vertices.
    faces: (M, 3) array of triangle indices.
    """
    logger.info(f"Exporting OBJ: {Path(path).name}")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w') as f:
        f.write(f"# ALAS OBJ Export\n")
        f.write(f"# Vertices: {len(vertices)}\n")
        f.write(f"# Faces: {len(faces)}\n\n")

        for v in vertices:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")

        f.write("\n")

        for face in faces:
            # OBJ uses 1-based indices
            f.write(f"f {face[0]+1} {face[1]+1} {face[2]+1}\n")

    logger.info(f"OBJ saved: {path}")


def raster_to_mesh(raster: RasterLayer) -> tuple:
    """
    Converts a raster to triangulated mesh for OBJ export.
    Returns (vertices, faces).
    """
    data = raster.get_band(0)
    rows, cols = data.shape
    bounds = raster.bounds

    if bounds is None:
        raise ValueError("Raster without defined extent.")

    xmin, ymin, xmax, ymax = bounds
    xs = np.linspace(xmin, xmax, cols)
    ys = np.linspace(ymax, ymin, rows)

    vertices = []
    vertex_map = {}

    for r in range(rows):
        for c in range(cols):
            z = data[r, c]
            if z != raster.nodata and not np.isnan(z):
                idx = len(vertices)
                vertices.append([xs[c], ys[r], z])
                vertex_map[(r, c)] = idx

    vertices = np.array(vertices, dtype=np.float64)

    # Triangles
    faces = []
    for r in range(rows - 1):
        for c in range(cols - 1):
            tl = vertex_map.get((r, c))
            tr = vertex_map.get((r, c+1))
            bl = vertex_map.get((r+1, c))
            br = vertex_map.get((r+1, c+1))

            if tl is not None and tr is not None and bl is not None:
                faces.append([tl, bl, tr])
            if tr is not None and bl is not None and br is not None:
                faces.append([tr, bl, br])

    faces = np.array(faces, dtype=np.int64) if faces else np.zeros((0, 3), dtype=np.int64)

    logger.info(f"Mesh: {len(vertices)} vertices, {len(faces)} triangles")
    return vertices, faces


def export_vector(geometries: list, attributes: list,
                   path: str, crs_epsg: int = None):
    """
    Exports geometries to Shapefile or GeoJSON.
    geometries: list of shapely geometries.
    attributes: list of dicts with properties.
    """
    import geopandas as gpd
    from shapely.geometry import mapping

    logger.info(f"Exporting vector: {Path(path).name}")

    gdf = gpd.GeoDataFrame(attributes, geometry=geometries)
    if crs_epsg:
        gdf.set_crs(epsg=crs_epsg, inplace=True)

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.suffix.lower() == '.shp':
        gdf.to_file(str(path), driver="ESRI Shapefile")
    elif path.suffix.lower() == '.geojson':
        gdf.to_file(str(path), driver="GeoJSON")
    elif path.suffix.lower() == '.gpkg':
        gdf.to_file(str(path), driver="GPKG")
    else:
        gdf.to_file(str(path))

    logger.info(f"Vector saved: {path} ({len(geometries)} features)")


def export_pdf_report(title: str, metadata: dict,
                       statistics: dict, screenshots: list,
                       path: str):
    """
    Generates a PDF report with statistics and screenshots.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER

    logger.info(f"Generating PDF report: {Path(path).name}")

    doc = SimpleDocTemplate(str(path), pagesize=A4,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    elements = []

    # Title style
    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Title'],
        fontSize=24, textColor=colors.HexColor("#7c3aed"),
        spaceAfter=20
    )

    # Title
    elements.append(Paragraph(title, title_style))
    elements.append(Paragraph("ALAS — Aerial LiDAR Analysis Software", styles['Normal']))
    elements.append(Spacer(1, 20))

    # Metadata
    if metadata:
        elements.append(Paragraph("Project information", styles['Heading2']))
        meta_data = [[k, str(v)] for k, v in metadata.items()]
        meta_table = Table(meta_data, colWidths=[6*cm, 10*cm])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#f3f4f6")),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 20))

    # Statistics
    if statistics:
        elements.append(Paragraph("Statistics", styles['Heading2']))
        stats_data = [[k, f"{v:.4f}" if isinstance(v, float) else str(v)]
                       for k, v in statistics.items()]
        stats_table = Table(stats_data, colWidths=[8*cm, 8*cm])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#f3f4f6")),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(stats_table)
        elements.append(Spacer(1, 20))

    # Screenshots
    for img_path in screenshots:
        if Path(img_path).exists():
            elements.append(Paragraph("Visualization", styles['Heading2']))
            img = Image(img_path, width=16*cm, height=12*cm)
            elements.append(img)
            elements.append(Spacer(1, 10))

    doc.build(elements)
    logger.info(f"PDF report saved: {path}")
