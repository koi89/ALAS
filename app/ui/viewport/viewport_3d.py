"""
ALAS — 3D Viewport
3D viewport based on PyVista QtInteractor for point cloud visualization.
"""

import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import pyqtSignal, Qt
import sys
from typing import Optional

from app.core.point_cloud import PointCloudData
from app.core.raster_layer import RasterLayer
from app.ui.viewport.colorizers import (
    colorize_by_height, colorize_by_intensity, colorize_by_classification,
    colorize_by_return_number, colorize_rgb, colorize_single
)
from app.ui.viewport.annotation_manager import AnnotationManager
from app.ui.viewport.figure_manager import FigureManager
from app.ui.viewport.measurement_tools import MeasurementTools
from app.config import (
    DEFAULT_POINT_SIZE, DEFAULT_BACKGROUND_COLOR,
    COLORIZE_HEIGHT, COLORIZE_INTENSITY, COLORIZE_CLASSIFICATION,
    COLORIZE_RETURN_NUMBER, COLORIZE_RGB, COLORIZE_SINGLE,
    MAX_VIEWPORT_POINTS
)
from app.logger import get_logger

logger = get_logger("ui.viewport")


class Viewport3D(QWidget):
    """
    3D viewport widget wrapping PyVista QtInteractor.
    Displays point clouds and raster surfaces.
    Delegates annotation, figure, and tool management to dedicated classes.
    """

    point_picked = pyqtSignal(float, float, float)   # x, y, z
    cursor_moved = pyqtSignal(float, float, float)    # coordinates under cursor

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._current_actors = {}
        self._point_size = DEFAULT_POINT_SIZE
        self._colorize_mode = COLORIZE_HEIGHT

        self.annotations = AnnotationManager(self.plotter)
        self.figures     = FigureManager(self.plotter, self._current_actors)
        self.tools       = MeasurementTools(self.plotter, self.point_picked.emit)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        pv.global_theme.background = DEFAULT_BACKGROUND_COLOR
        pv.global_theme.font.color = "white"

        # On Windows MSAA can be very slow, we use FXAA or disable it
        if sys.platform == "win32":
            pv.global_theme.anti_aliasing = "fxaa"
        else:
            pv.global_theme.anti_aliasing = "msaa"

        self.plotter = QtInteractor(self)

        # Eye Dome Lighting is excellent but heavy, we enable it with optimized parameters
        self.plotter.enable_eye_dome_lighting()
        layout.addWidget(self.plotter.interactor)

        self.plotter.enable_trackball_style()
        self.plotter.interactor.installEventFilter(self)

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent, Qt
        from PyQt6.QtGui import QMouseEvent
        from PyQt6.QtWidgets import QApplication

        if self.tools.picking_active:
            return super().eventFilter(obj, event)

        if hasattr(self, 'plotter') and obj == self.plotter.interactor:
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.RightButton:
                    new_event = QMouseEvent(
                        QEvent.Type.MouseButtonPress,
                        event.position(),
                        event.globalPosition(),
                        Qt.MouseButton.MiddleButton,
                        (event.buttons() & ~Qt.MouseButton.RightButton) | Qt.MouseButton.MiddleButton,
                        event.modifiers()
                    )
                    QApplication.postEvent(obj, new_event)
                    return True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                if event.button() == Qt.MouseButton.RightButton:
                    new_event = QMouseEvent(
                        QEvent.Type.MouseButtonRelease,
                        event.position(),
                        event.globalPosition(),
                        Qt.MouseButton.MiddleButton,
                        (event.buttons() & ~Qt.MouseButton.RightButton),
                        event.modifiers()
                    )
                    QApplication.postEvent(obj, new_event)
                    return True
            elif event.type() == QEvent.Type.MouseMove:
                if event.buttons() & Qt.MouseButton.RightButton:
                    new_event = QMouseEvent(
                        QEvent.Type.MouseMove,
                        event.position(),
                        event.globalPosition(),
                        Qt.MouseButton.NoButton,
                        (event.buttons() & ~Qt.MouseButton.RightButton) | Qt.MouseButton.MiddleButton,
                        event.modifiers()
                    )
                    QApplication.postEvent(obj, new_event)
                    return True
        return super().eventFilter(obj, event)

    # ------------------------------------------------------------------
    # Point Cloud Display
    # ------------------------------------------------------------------

    @staticmethod
    def prepare_display_data(pc: PointCloudData, colorize_by: str) -> pv.PolyData:
        """Decimate and build a colored PolyData mesh — safe to run off the main thread."""
        display_pc = pc
        if pc.point_count > MAX_VIEWPORT_POINTS:
            display_pc = pc.decimate_for_display(MAX_VIEWPORT_POINTS)
            logger.info(
                f"Automatic decimation: {pc.point_count:,} → "
                f"{display_pc.point_count:,} points for visualization"
            )

        points = display_pc.xyz.astype(np.float32)
        cloud = pv.PolyData(points)

        colors = Viewport3D._generate_colors_static(display_pc, colorize_by)
        if colors is not None:
            cloud["RGB"] = colors

        return cloud

    def render_prepared_cloud(self, cloud: pv.PolyData, name: str):
        """Upload a prepared PolyData mesh to the plotter — must run on the main thread."""
        has_colors = "RGB" in cloud.point_data
        actor = self.plotter.add_mesh(
            cloud,
            scalars="RGB" if has_colors else None,
            rgb=has_colors,
            point_size=self._point_size,
            render_points_as_spheres=False,
            name=name,
            show_scalar_bar=False,
        )
        self._current_actors[name] = actor
        logger.info(f"Rendered {cloud.n_points:,} points | name={name}")

    def display_point_cloud(self, pc: PointCloudData,
                             colorize_by: str = None, name: str = None):
        """Display a point cloud synchronously (used by update_colorization)."""
        if pc.xyz is None or pc.point_count == 0:
            logger.warning("Empty cloud, nothing to display")
            return
        name = name or pc.name
        colorize_by = colorize_by or self._colorize_mode
        cloud = Viewport3D.prepare_display_data(pc, colorize_by)
        self.render_prepared_cloud(cloud, name)

    def update_colorization(self, pc: PointCloudData,
                              colorize_by: str, name: str = None):
        self._colorize_mode = colorize_by
        self.display_point_cloud(pc, colorize_by, name)

    @staticmethod
    def _generate_colors_static(pc: PointCloudData,
                                 mode: str) -> Optional[np.ndarray]:
        try:
            if mode == COLORIZE_HEIGHT:
                return colorize_by_height(pc.xyz[:, 2])
            elif mode == COLORIZE_INTENSITY and pc.intensity is not None:
                return colorize_by_intensity(pc.intensity)
            elif mode == COLORIZE_CLASSIFICATION and pc.classification is not None:
                return colorize_by_classification(pc.classification)
            elif mode == COLORIZE_RETURN_NUMBER and pc.return_number is not None:
                return colorize_by_return_number(pc.return_number)
            elif mode == COLORIZE_RGB and pc.has_rgb:
                return colorize_rgb(pc.rgb)
            elif mode == COLORIZE_SINGLE:
                return colorize_single(pc.point_count)
            else:
                return colorize_by_height(pc.xyz[:, 2])
        except Exception as e:
            logger.error(f"Error in colorization ({mode}): {e}")
            return colorize_by_height(pc.xyz[:, 2])

    # ------------------------------------------------------------------
    # Raster Display
    # ------------------------------------------------------------------

    def display_raster_surface(self, raster: RasterLayer, name: str = None):
        if not raster.is_loaded:
            return

        name = name or raster.name
        data = raster.get_band(0)
        rows, cols = data.shape
        bounds = raster.bounds
        if bounds is None:
            return

        xmin, ymin, xmax, ymax = bounds
        x = np.linspace(xmin, xmax, cols)
        y = np.linspace(ymax, ymin, rows)  # Y inverted in rasters
        xx, yy = np.meshgrid(x, y)

        terrain_arr = getattr(raster, "flood_terrain_arr", None)
        is_flood = terrain_arr is not None

        if is_flood:
            z = np.asarray(terrain_arr, dtype=np.float32).copy()
            z[z == raster.nodata] = np.nan

            depth = data.astype(np.float32).copy()
            depth[depth == raster.nodata] = np.nan
            depth[depth <= 0.0] = np.nan

            if not np.any(np.isfinite(depth)):
                logger.info(f"Flood layer '{name}': no flooded cells at this water level")
                self._remove_actor(name)
                return

            grid = pv.StructuredGrid(xx, yy, z)

            # Build per-point RGBA: semi-transparent blue where flooded,
            # fully transparent elsewhere. Terrain shape comes from z so
            # the surface follows the DTM and can be overlaid for comparison.
            n_pts = rows * cols
            rgba = np.zeros((n_pts, 4), dtype=np.uint8)
            depth_flat = depth.ravel(order="F")
            flooded = np.isfinite(depth_flat)

            valid_depth = depth_flat[flooded]
            vmax = float(np.nanpercentile(valid_depth, 99.0))
            norm = np.clip(valid_depth / max(vmax, 0.01), 0.0, 1.0)
            rgba[flooded, 0] = np.interp(norm, [0, 1], [173,   8]).astype(np.uint8)
            rgba[flooded, 1] = np.interp(norm, [0, 1], [216,  48]).astype(np.uint8)
            rgba[flooded, 2] = np.interp(norm, [0, 1], [230, 107]).astype(np.uint8)
            rgba[flooded, 3] = 200

            grid["FloodColor"] = rgba
            actor = self.plotter.add_mesh(
                grid,
                scalars="FloodColor",
                rgba=True,
                show_scalar_bar=False,
                name=name,
            )
        else:
            z = data.astype(np.float32).copy()
            z[z == raster.nodata] = np.nan

            grid = pv.StructuredGrid(xx, yy, z)
            grid["Elevation"] = z.ravel(order="F")
            # PyVista's name= parameter replaces any existing mesh with this name
            # atomically. Calling _remove_actor first would cause a double-remove
            # that crashes VTK on subsequent runs of the same analysis.
            actor = self.plotter.add_mesh(
                grid,
                scalars="Elevation",
                cmap="terrain",
                nan_opacity=0,
                show_scalar_bar=False,
                name=name,
            )

        self._current_actors[name] = actor

    # ------------------------------------------------------------------
    # Actor management
    # ------------------------------------------------------------------

    def _remove_actor(self, name: str):
        if name in self._current_actors:
            try:
                self.plotter.remove_actor(self._current_actors[name])
            except Exception:
                pass
            del self._current_actors[name]

    def remove_layer(self, name: str):
        self._remove_actor(name)
        self.plotter.render()

    def set_layer_visibility(self, name: str, visible: bool):
        if name in self._current_actors:
            actor = self._current_actors[name]
            actor.SetVisibility(visible)
            self.plotter.render()

    def clear_all(self):
        self.plotter.clear()
        self._current_actors.clear()

    # ------------------------------------------------------------------
    # Camera controls
    # ------------------------------------------------------------------

    def reset_camera(self):
        self.plotter.reset_camera()
        self.plotter.render()

    def set_view_top(self):
        self.plotter.view_xy()
        self.plotter.render()

    def set_view_front(self):
        self.plotter.view_xz()
        self.plotter.render()

    def set_view_side(self):
        self.plotter.view_yz()
        self.plotter.render()

    def zoom_to_bounds(self, bounds):
        if bounds is None:
            return
        if len(bounds) == 6:
            xmin, ymin, zmin, xmax, ymax, zmax = bounds
        else:
            xmin, ymin, xmax, ymax = bounds
            zmin, zmax = 0, 100
        self.plotter.reset_camera_clipping_range()
        self.plotter.render()

    # ------------------------------------------------------------------
    # Point size
    # ------------------------------------------------------------------

    def set_point_size(self, size: float):
        self._point_size = size
        for name, actor in self._current_actors.items():
            try:
                prop = actor.GetProperty()
                prop.SetPointSize(size)
            except Exception:
                pass
        self.plotter.render()

    # ------------------------------------------------------------------
    # Screenshot
    # ------------------------------------------------------------------

    def take_screenshot(self, path: str = None) -> Optional[np.ndarray]:
        if path:
            self.plotter.screenshot(path)
            logger.info(f"Screenshot saved: {path}")
            return None
        return self.plotter.screenshot(return_img=True)

    # ------------------------------------------------------------------
    # Interactive tools — delegated to MeasurementTools
    # ------------------------------------------------------------------

    def enable_point_picking(self, callback=None):
        self.tools.enable_point_picking(callback)

    def add_temporary_line(self, p1, p2, color="#ffff00"):
        return self.tools.add_temporary_line(p1, p2, color)

    def add_measurement_marker(self, p):
        return self.tools.add_measurement_marker(p)

    def add_measurement_line(self, p1, p2):
        return self.tools.add_measurement_line(p1, p2)

    def enable_distance_tool(self):
        self.tools.enable_distance_tool()

    def enable_world_picking(self, callback):
        self.tools.enable_world_picking(callback)

    def enable_area_tool(self, on_vertex_added=None):
        self.tools.enable_area_tool(on_vertex_added)

    def draw_closing_line(self):
        self.tools.draw_closing_line()

    def clear_volume_graphics(self):
        self.tools.clear_volume_graphics()

    def display_volume_region(self, grid_x, grid_y, grid_z, reference_z):
        self.tools.display_volume_region(grid_x, grid_y, grid_z, reference_z)

    def clear_temporary_graphics(self):
        self.tools.clear_temporary_graphics()

    def disable_tools(self):
        self.tools.disable_tools()

    # ------------------------------------------------------------------
    # Geometric figures — delegated to FigureManager
    # ------------------------------------------------------------------

    @staticmethod
    def _build_figure_mesh(figure_type: str, center, params: dict):
        return FigureManager._build_mesh(figure_type, center, params)

    def add_figure(self, figure_type: str, center, params: dict,
                   name: str, color: str = "#a855f7", opacity: float = 0.55):
        return self.figures.add(figure_type, center, params, name, color, opacity)

    def update_figure(self, figure_type: str, center, params: dict,
                      name: str, color: str = "#a855f7", opacity: float = 0.55):
        return self.figures.update(figure_type, center, params, name, color, opacity)

    def register_figure_id(self, name: str, figure_id: int):
        self.figures.register_id(name, figure_id)

    def unregister_figure(self, name: str):
        self.figures.unregister(name)

    def enable_figure_dragging(self, on_figure_moved):
        self.figures.enable_dragging(on_figure_moved)

    def disable_figure_dragging(self):
        self.figures.disable_dragging()

    # ------------------------------------------------------------------
    # Annotations — delegated to AnnotationManager
    # ------------------------------------------------------------------

    def add_annotation(self, ann_id: int, point: tuple, text: str,
                       color: str = "#00e5ff") -> None:
        self.annotations.add(ann_id, point, text, color)

    def remove_annotation(self, ann_id: int) -> None:
        self.annotations.remove(ann_id)

    def clear_annotations(self) -> None:
        self.annotations.clear()

    # ------------------------------------------------------------------
    # Contour Lines
    # ------------------------------------------------------------------

    def display_contours(self, contours: list, name: str = "_contours") -> None:
        """
        Render elevation contour lines.

        Parameters
        ----------
        contours : list of {"elevation": float, "xy": ndarray (N, 2)}
        name     : actor name used for later removal / replacement
        """
        if not contours:
            self._remove_actor(name)
            return

        all_pts: list[np.ndarray] = []
        all_cells: list[np.ndarray] = []
        all_elev: list[np.ndarray] = []
        offset = 0

        for c in contours:
            xy = c["xy"]
            elev = c["elevation"]
            n = len(xy)
            pts_3d = np.column_stack([xy, np.full(n, elev, dtype=np.float64)])
            all_pts.append(pts_3d)
            cell = np.concatenate([[n], np.arange(offset, offset + n)])
            all_cells.append(cell)
            all_elev.append(np.full(n, elev, dtype=np.float64))
            offset += n

        pts_array  = np.vstack(all_pts)
        cells_flat = np.concatenate(all_cells).astype(np.int64)
        elev_array = np.concatenate(all_elev)

        pd = pv.PolyData()
        pd.points    = pts_array
        pd.lines     = cells_flat
        pd["elevation"] = elev_array

        actor = self.plotter.add_mesh(
            pd,
            scalars="elevation",
            cmap="terrain",
            line_width=1.5,
            name=name,
            reset_camera=False,
            show_scalar_bar=False,
        )
        self._current_actors[name] = actor
        self.plotter.render()
        logger.info(f"Displayed {len(contours)} contour segments")

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        self.plotter.close()
        super().closeEvent(event)
