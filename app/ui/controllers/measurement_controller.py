"""
ALAS — Measurement Controller
Handles profile, distance, area, volume tools and their history dialogs.
"""

import numpy as np
from app.i18n import tr
from app.logger import get_logger

logger = get_logger("ui.measurement_controller")


class MeasurementController:
    """
    Owns all measurement-tool dialog instances and the callbacks that wire
    them to the viewport.  Constructed with a reference to MainWindow so it
    can reach viewport, layer_manager, layer_panel, and _update_status.
    """

    def __init__(self, window):
        self._w = window
        self._area_dialog = None
        self._distance_dialog = None
        self._measurements_dialog = None
        self._classification_history_dialog = None
        self._volume_dialog = None
        self._profile_dialog = None
        self._profile_points = []

    # ------------------------------------------------------------------
    # Profile tool
    # ------------------------------------------------------------------

    def start_profile_tool(self):
        logger.info("Profile tool activated")
        from app.ui.viewport.profile_tool import ProfileDialog

        if self._profile_dialog is None:
            self._profile_dialog = ProfileDialog(self._w.layer_manager, self._w)

        entry = self._w.layer_manager.active_layer
        if entry and entry.layer.bounds:
            b = entry.layer.bounds
            if len(b) == 6:
                self._profile_dialog.set_coordinates(b[0], b[1], b[3], b[4])
            elif len(b) == 4:
                self._profile_dialog.set_coordinates(b[0], b[1], b[2], b[3])

        self._profile_dialog.show()
        self._profile_dialog.raise_()
        self._profile_dialog.activateWindow()

        self._profile_points = []

        def on_pick(x, y, z):
            self._profile_points.append((x, y, z))
            if len(self._profile_points) == 1:
                self._w._update_status(tr("msg.profile_end"))
            elif len(self._profile_points) == 2:
                p1, p2 = self._profile_points
                self._w.viewport.add_temporary_line(p1, p2, color="#ffff00")
                self._profile_dialog.set_coordinates(p1[0], p1[1], p2[0], p2[1])
                self._profile_dialog._on_calculate()
                self._profile_points = []
                self._w._update_status(tr("msg.profile_calculated"))

        self._w.viewport.enable_point_picking(on_pick)
        self._w._update_status(tr("msg.profile_start"))

    # ------------------------------------------------------------------
    # Distance tool
    # ------------------------------------------------------------------

    def start_distance_tool(self):
        logger.info("Distance tool activated")
        from app.ui.viewport.distance_tool import DistanceToolDialog

        if self._distance_dialog is None:
            self._distance_dialog = DistanceToolDialog(self._w)
            self._distance_dialog.calculate_requested.connect(self._calculate_distance)
            self._distance_dialog.clear_requested.connect(self._on_distance_clear)

        self._distance_dialog.reset()
        self._distance_dialog.show()
        self._distance_dialog.raise_()
        self._distance_dialog.activateWindow()

        self._w.viewport.enable_world_picking(self._on_distance_pick)
        self._w._update_status(tr("msg.distance_point_a"))

    def _on_distance_pick(self, x, y, z):
        if self._distance_dialog is None:
            return
        num = len(self._distance_dialog.get_points())
        if num == 0:
            self._distance_dialog.add_point(x, y, z, "A")
            self._w.viewport.add_measurement_marker((x, y, z))
            self._w._update_status(tr("msg.distance_point_b"))
        elif num == 1:
            self._distance_dialog.add_point(x, y, z, "B")
            self._w.viewport.add_measurement_marker((x, y, z))
            points = self._distance_dialog.get_points()
            self._w.viewport.add_measurement_line(points[0], points[1])

    def _on_distance_clear(self):
        self._w.viewport.disable_tools()
        if self._distance_dialog is not None and self._distance_dialog.isVisible():
            self._distance_dialog.reset()
            self._w.viewport.enable_world_picking(self._on_distance_pick)
        self._w._update_status(tr("status.ready"))

    def _calculate_distance(self):
        if self._distance_dialog is None:
            return
        points = self._distance_dialog.get_points()
        if len(points) != 2:
            return
        p1, p2 = points
        from app.processing.measurements import measure_3d_distance
        res = measure_3d_distance(p1, p2)
        self._distance_dialog.show_results(
            res['distance_3d'], res['distance_2d'], res['dz'], res['slope_degrees']
        )
        self._w._update_status(
            tr("status.distance").format(
                res['distance_3d'], res['distance_2d'], res['dz'], res['slope_degrees']
            )
        )
        self.record_measurement("distance", {
            **res,
            "ax": p1[0], "ay": p1[1], "az": p1[2],
            "bx": p2[0], "by": p2[1], "bz": p2[2],
        })
        logger.info(
            f"Distance: 3D={res['distance_3d']:.3f}m  "
            f"2D={res['distance_2d']:.3f}m  dZ={res['dz']:.3f}m"
        )

    # ------------------------------------------------------------------
    # Area tool
    # ------------------------------------------------------------------

    def start_area_tool(self):
        logger.info("Area tool activated")
        from app.ui.viewport.area_tool import AreaToolDialog

        if self._area_dialog is None:
            self._area_dialog = AreaToolDialog(self._w)
            self._area_dialog.calculate_requested.connect(self._calculate_area)
            self._area_dialog.clear_requested.connect(self._on_area_clear)
            self._area_dialog.undo_requested.connect(self._on_area_undo)

        self._area_dialog.reset()
        self._area_dialog.show()
        self._area_dialog.raise_()
        self._area_dialog.activateWindow()

        self._w.viewport.enable_area_tool(on_vertex_added=self._on_area_vertex_added)
        self._w._update_status(tr("msg.area_tool"))

    def _on_area_vertex_added(self, x, y, z):
        if self._area_dialog is not None:
            self._area_dialog.add_vertex(x, y, z)
            n = len(self._area_dialog.get_vertices())
            self._w._update_status(
                tr("msg.area_vertices").format(n, "es" if n != 1 else "")
            )

    def _on_area_clear(self):
        self._w.viewport.disable_tools()
        if self._area_dialog is not None and self._area_dialog.isVisible():
            self._w.viewport.enable_area_tool(on_vertex_added=self._on_area_vertex_added)
        self._w._update_status(tr("status.ready"))

    def _on_area_undo(self, vertices):
        self._w.viewport.disable_tools()
        if self._area_dialog is not None and self._area_dialog.isVisible():
            self._w.viewport.enable_area_tool(on_vertex_added=self._on_area_vertex_added)
            for v in vertices:
                self._w.viewport.add_measurement_marker(v)
            for i in range(len(vertices) - 1):
                self._w.viewport.add_measurement_line(vertices[i], vertices[i + 1])
        n = len(vertices)
        self._w._update_status(
            tr("msg.area_vertices").format(n, "es" if n != 1 else "")
        )

    def _calculate_area(self):
        if self._area_dialog is None:
            return
        vertices = self._area_dialog.get_vertices()
        if len(vertices) < 3:
            return

        self._w.viewport.draw_closing_line()

        pts = np.array(vertices)
        diffs = np.diff(pts[:, :2], axis=0)
        seg_lengths = np.sqrt((diffs ** 2).sum(axis=1))
        closing = np.sqrt(
            (pts[-1, 0] - pts[0, 0]) ** 2 + (pts[-1, 1] - pts[0, 1]) ** 2
        )
        perimeter = float(seg_lengths.sum() + closing)

        rasters = [e for e in self._w.layer_manager.get_all_entries() if e.is_raster]

        if rasters:
            from app.processing.measurements import measure_area
            polygon_xy = pts[:, :2]
            raster_layer = rasters[0].layer

            def _on_result(res):
                self._finish_area_calculation(
                    vertices, res["planimetric_area_m2"], res["surface_area_m2"],
                    perimeter, True
                )

            def _on_error(e):
                logger.error(f"Error calculating area with DEM: {e}")
                fallback = self._shoelace_area(pts[:, :2])
                self._finish_area_calculation(vertices, fallback, fallback, perimeter, False)

            self._w._run_processing(
                measure_area, raster_layer, polygon_xy,
                on_result=_on_result, on_error=_on_error,
            )
        else:
            plan_m2 = self._shoelace_area(pts[:, :2])
            self._finish_area_calculation(vertices, plan_m2, plan_m2, perimeter, False)

    def _finish_area_calculation(self, vertices, plan_m2, surf_m2, perimeter, used_raster):
        if self._area_dialog is None:
            return
        self._area_dialog.show_results(
            plan_m2=plan_m2, surf_m2=surf_m2,
            perimeter_m=perimeter, used_raster=used_raster,
        )
        self._w._update_status(tr("msg.area_calculated").format(plan_m2, perimeter))
        logger.info(
            f"Area: plan={plan_m2:.2f}m² surf={surf_m2:.2f}m² "
            f"per={perimeter:.2f}m verts={len(vertices)}"
        )
        verts_as_dicts = [{"x": v[0], "y": v[1], "z": v[2]} for v in vertices]
        self.record_measurement("area", {
            "planimetric_area_m2": plan_m2,
            "surface_area_m2":     surf_m2,
            "perimeter_m":         perimeter,
            "used_raster":         used_raster,
            "num_vertices":        len(vertices),
            "vertices":            verts_as_dicts,
        })

    @staticmethod
    def _shoelace_area(pts: np.ndarray) -> float:
        x, y = pts[:, 0], pts[:, 1]
        return float(abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2.0)

    # ------------------------------------------------------------------
    # Volume tool
    # ------------------------------------------------------------------

    def start_volume_tool(self):
        logger.info("Volume tool activated")
        from app.ui.viewport.volume_tool import VolumeToolDialog

        if self._volume_dialog is None:
            self._volume_dialog = VolumeToolDialog(self._w)
            self._volume_dialog.calculate_requested.connect(self._calculate_volume)
            self._volume_dialog.clear_requested.connect(self._on_volume_clear)
            self._volume_dialog.clear_volume_requested.connect(self._on_volume_clear_only_solid)

        self._volume_dialog.reset()
        self._volume_dialog.show()
        self._volume_dialog.raise_()
        self._volume_dialog.activateWindow()

        self._w.viewport.enable_area_tool(on_vertex_added=self._on_volume_vertex_added)
        self._w._update_status(tr("msg.volume_tool_active"))

    def _on_volume_vertex_added(self, x, y, z):
        if self._volume_dialog is not None:
            self._volume_dialog.add_vertex(x, y, z)
            n = len(self._volume_dialog.get_vertices())
            self._w._update_status(
                tr("msg.volume_vertices").format(n, "es" if n != 1 else "")
            )

    def _on_volume_clear_only_solid(self):
        self._w.viewport.clear_volume_graphics()
        self._w._update_status(tr("msg.volume_cleared"))

    def _on_volume_clear(self):
        self._w.viewport.disable_tools()
        if self._volume_dialog is not None and self._volume_dialog.isVisible():
            self._w.viewport.enable_area_tool(on_vertex_added=self._on_volume_vertex_added)
        self._w._update_status(tr("status.ready"))

    def _calculate_volume(self):
        if self._volume_dialog is None:
            return
        vertices = self._volume_dialog.get_vertices()
        if len(vertices) < 3:
            return

        z_ref = self._volume_dialog.get_reference_z()
        self._w.viewport.draw_closing_line()

        rasters = [e for e in self._w.layer_manager.get_all_entries() if e.is_raster]
        if not rasters:
            self._volume_dialog.show_error(tr("msg.volume_no_dem"))
            return

        from app.processing.measurements import calculate_volume
        raster_layer = rasters[0].layer
        polygon_xy = np.array(vertices)[:, :2]

        def _do_volume():
            return calculate_volume(raster_layer, z_ref, polygon_xy)

        def _on_result(res):
            if self._volume_dialog is None:
                return
            self._volume_dialog.show_results(
                res['cut_volume_m3'], res['fill_volume_m3'],
                res['net_volume_m3'], res['area_m2']
            )
            self._w._update_status(tr("msg.volume_calculated").format(res['net_volume_m3'], z_ref))
            if 'grid_x' in res:
                self._w.viewport.display_volume_region(
                    res['grid_x'], res['grid_y'], res['grid_z'], z_ref
                )
            hist_data = {k: v for k, v in res.items() if k not in ('grid_x', 'grid_y', 'grid_z')}
            verts_as_dicts = [{"x": v[0], "y": v[1], "z": v[2]} for v in vertices]
            self.record_measurement("volume", {
                **hist_data,
                "reference_z":  z_ref,
                "num_vertices": len(vertices),
                "vertices":     verts_as_dicts,
            })

        def _on_error(e):
            logger.error(f"Error calculating volume: {e}")
            if self._volume_dialog is not None:
                self._volume_dialog.show_error(f"Error: {e}")

        self._w._run_processing(_do_volume, on_result=_on_result, on_error=_on_error)

    # ------------------------------------------------------------------
    # Measurement history
    # ------------------------------------------------------------------

    def _get_measurements_dialog(self):
        if self._measurements_dialog is None:
            from app.ui.dialogs.measurements_history_dialog import MeasurementsHistoryDialog
            self._measurements_dialog = MeasurementsHistoryDialog(self._w)
        return self._measurements_dialog

    def show_measurements_history(self):
        self._get_measurements_dialog().show_and_raise()

    def record_measurement(self, mtype: str, data: dict):
        self._get_measurements_dialog().add_measurement(mtype, data)
        logger.info(f"Measurement '{mtype}' registered in history.")

    # ------------------------------------------------------------------
    # Classification history
    # ------------------------------------------------------------------

    def _get_classification_history_dialog(self):
        if self._classification_history_dialog is None:
            from app.ui.dialogs.classification_history_dialog import ClassificationHistoryDialog
            self._classification_history_dialog = ClassificationHistoryDialog(self._w)
        return self._classification_history_dialog

    def show_classification_history(self):
        self._get_classification_history_dialog().show_and_raise()

    def record_classification(self, algo: str, data: dict):
        self._get_classification_history_dialog().add_classification(algo, data)
        logger.info(f"Classification '{algo}' registered in history.")
