"""
ALAS — Measurement Tools
Interactive measurement tools: point picking, distance, area, volume, world picking.
"""

import numpy as np
import pyvista as pv
from app.logger import get_logger

logger = get_logger("ui.viewport.tools")


class MeasurementTools:
    """
    Owns all temporary actors and VTK observers used by interactive measurement tools.
    ``emit_point_picked(x, y, z)`` is a callable injected from Viewport3D so the
    pyqtSignal can be emitted without coupling this class to Qt.
    """

    def __init__(self, plotter, emit_point_picked):
        self._plotter = plotter
        self._emit_point_picked = emit_point_picked

        self._picked_points = []
        self._measuring_widget = None
        self._picking_callback = None
        self._temp_actors = []
        self.picking_active = False   # read by Viewport3D.eventFilter

    # ------------------------------------------------------------------
    # Point picking
    # ------------------------------------------------------------------

    def enable_point_picking(self, callback=None):
        logger.info("Enabling point picking...")
        self.disable_tools()
        self.picking_active = True
        self._picking_callback = callback

        self._plotter.enable_point_picking(
            callback=self._on_point_picked,
            show_message="",
            color="#ffff00",
            point_size=12,
            use_picker=True,
            left_clicking=True
        )
        logger.info("Point picking ready. Left-click on points.")

    def _on_point_picked(self, point):
        logger.debug(f"Picking event triggered. Point: {point}")
        if point is None:
            logger.warning("Picking triggered but no point found.")
            return

        x, y, z = point
        logger.info(f"Point detected: X={x:.3f}, Y={y:.3f}, Z={z:.3f}")

        sphere = pv.Sphere(radius=0.2, center=point)
        actor = self._plotter.add_mesh(
            sphere, color="#ffff00",
            name=f"_tmp_point_{len(self._temp_actors)}"
        )
        self._temp_actors.append(actor)

        self._emit_point_picked(x, y, z)
        if self._picking_callback:
            logger.debug("Calling tool callback...")
            self._picking_callback(x, y, z)

    # ------------------------------------------------------------------
    # Temporary graphics
    # ------------------------------------------------------------------

    def add_temporary_line(self, p1, p2, color="#ffff00"):
        line = pv.Line(p1, p2)
        actor = self._plotter.add_mesh(
            line,
            color=color,
            line_width=12,
            name=f"_tmp_line_{len(self._temp_actors)}",
            render_lines_as_tubes=True,
            smooth_shading=True,
        )
        try:
            actor.GetProperty().SetLighting(False)
            actor.GetProperty().SetAmbient(1.0)
        except Exception:
            pass
        self._temp_actors.append(actor)
        return actor

    def add_measurement_marker(self, p):
        pts = pv.PolyData([list(p)])
        actor = self._plotter.add_mesh(
            pts,
            color="#000000",
            point_size=14,
            render_points_as_spheres=True,
            name=f"_meas_marker_{len(self._temp_actors)}",
            reset_camera=False,
        )
        self._temp_actors.append(actor)
        return actor

    def add_measurement_line(self, p1, p2):
        line = pv.Line(p1, p2)
        actor = self._plotter.add_mesh(
            line,
            color="#000000",
            line_width=3,
            name=f"_meas_line_{len(self._temp_actors)}",
            reset_camera=False,
        )
        self._temp_actors.append(actor)
        self._plotter.render()
        return actor

    def clear_temporary_graphics(self):
        for actor in self._temp_actors:
            try:
                self._plotter.remove_actor(actor)
            except Exception:
                pass
        self._temp_actors = []
        for attr in ("_area_markers_actor", "_area_lines_actor"):
            actor = getattr(self, attr, None)
            if actor is not None:
                try:
                    self._plotter.remove_actor(actor)
                except Exception:
                    pass
                setattr(self, attr, None)
        self._plotter.render()

    # ------------------------------------------------------------------
    # Distance tool
    # ------------------------------------------------------------------

    def enable_distance_tool(self):
        self.disable_tools()
        self.picking_active = True
        self._measuring_widget = self._plotter.add_measurement_widget(color="#000000")
        logger.info("Distance tool enabled")

    # ------------------------------------------------------------------
    # World picking (profile, annotations, etc.)
    # ------------------------------------------------------------------

    def enable_world_picking(self, callback):
        import vtk as _vtk
        self.disable_tools()
        self.picking_active = True

        wp_picker = _vtk.vtkWorldPointPicker()
        self._wp_picker_ref = wp_picker

        iren = self._plotter.iren.interactor
        press_pos_ref = [None]

        def _on_press(obj, event):
            press_pos_ref[0] = iren.GetEventPosition()
            obj.OnLeftButtonDown()

        def _on_release(obj, event):
            release_pos = iren.GetEventPosition()
            press_pos   = press_pos_ref[0]
            obj.OnLeftButtonUp()
            if press_pos is None:
                return
            dx = release_pos[0] - press_pos[0]
            dy = release_pos[1] - press_pos[1]
            if (dx * dx + dy * dy) > 25:
                return
            wp_picker.Pick(press_pos[0], press_pos[1], 0, self._plotter.renderer)
            p = wp_picker.GetPickPosition()
            x, y, z = float(p[0]), float(p[1]), float(p[2])
            logger.debug(f"World pick: ({x:.3f}, {y:.3f}, {z:.3f})")
            callback(x, y, z)

        style = iren.GetInteractorStyle()
        self._wp_obs_press   = style.AddObserver("LeftButtonPressEvent",   _on_press)
        self._wp_obs_release = style.AddObserver("LeftButtonReleaseEvent", _on_release)
        self._wp_style_ref   = style

    # ------------------------------------------------------------------
    # Area tool
    # ------------------------------------------------------------------

    def enable_area_tool(self, on_vertex_added=None):
        """
        Performance:
        - vtkWorldPointPicker: O(1) — reads the Z-buffer, does NOT traverse geometry.
        - Single PolyData actor for all vertices (large points).
        - Single PolyData actor for all lines, updated on each click.
        - Click vs drag: if mouse moves < 5 px between press and release = click.
        """
        import vtk as _vtk
        logger.info("Enabling area tool...")
        self.disable_tools()
        self.picking_active = True
        self._area_vertices: list = []
        self._area_press_pos = None
        self._area_markers_actor = None
        self._area_lines_actor   = None

        wp_picker = _vtk.vtkWorldPointPicker()
        self._area_picker = wp_picker

        iren = self._plotter.iren.interactor

        def _on_press(obj, event):
            self._area_press_pos = iren.GetEventPosition()
            obj.OnLeftButtonDown()

        def _on_release(obj, event):
            release_pos = iren.GetEventPosition()
            press_pos   = self._area_press_pos
            obj.OnLeftButtonUp()
            if press_pos is None:
                return
            dx = release_pos[0] - press_pos[0]
            dy = release_pos[1] - press_pos[1]
            if (dx * dx + dy * dy) > 25:
                return

            wp_picker.Pick(press_pos[0], press_pos[1], 0, self._plotter.renderer)
            p = wp_picker.GetPickPosition()
            x, y, z = float(p[0]), float(p[1]), float(p[2])
            self._area_vertices.append((x, y, z))
            pts = np.array(self._area_vertices, dtype=np.float32)

            markers = pv.PolyData(pts)
            if self._area_markers_actor is not None:
                self._plotter.remove_actor(self._area_markers_actor)
            self._area_markers_actor = self._plotter.add_mesh(
                markers,
                color="#000000",
                point_size=14,
                render_points_as_spheres=True,
                name="_area_markers",
                reset_camera=False,
            )

            if len(self._area_vertices) >= 2:
                n = len(pts)
                cells = np.empty((n - 1) * 3, dtype=np.int_)
                cells[0::3] = 2
                cells[1::3] = np.arange(n - 1)
                cells[2::3] = np.arange(1, n)
                lines_pd = pv.PolyData()
                lines_pd.points = pts
                lines_pd.lines  = cells
                if self._area_lines_actor is not None:
                    self._plotter.remove_actor(self._area_lines_actor)
                self._area_lines_actor = self._plotter.add_mesh(
                    lines_pd,
                    color="#000000",
                    line_width=3,
                    name="_area_lines",
                    reset_camera=False,
                )

            self._plotter.render()
            logger.debug(f"Area — vertex {len(self._area_vertices)}: ({x:.2f}, {y:.2f}, {z:.2f})")
            if on_vertex_added:
                on_vertex_added(x, y, z)

        style = iren.GetInteractorStyle()
        self._area_obs_press   = style.AddObserver("LeftButtonPressEvent",   _on_press)
        self._area_obs_release = style.AddObserver("LeftButtonReleaseEvent", _on_release)
        self._area_style_ref   = style
        logger.info("Area tool ready. Click to add vertices.")

    def draw_closing_line(self):
        if not hasattr(self, "_area_vertices") or len(self._area_vertices) < 3:
            return
        pts = np.array(self._area_vertices, dtype=np.float32)
        n = len(pts)
        cells = np.empty(n * 3, dtype=np.int_)
        cells[0::3] = 2
        cells[1::3] = np.arange(n)
        cells[2::3] = np.arange(1, n + 1) % n
        lines_pd = pv.PolyData()
        lines_pd.points = pts
        lines_pd.lines  = cells
        if hasattr(self, "_area_lines_actor") and self._area_lines_actor is not None:
            self._plotter.remove_actor(self._area_lines_actor)
        self._area_lines_actor = self._plotter.add_mesh(
            lines_pd, color="#000000", line_width=3, name="_area_lines",
            reset_camera=False,
        )

    # ------------------------------------------------------------------
    # Volume graphics
    # ------------------------------------------------------------------

    def clear_volume_graphics(self):
        if hasattr(self, "_volume_solid_actor") and self._volume_solid_actor is not None:
            try:
                self._plotter.remove_actor(self._volume_solid_actor)
                if self._volume_solid_actor in self._temp_actors:
                    self._temp_actors.remove(self._volume_solid_actor)
            except Exception:
                pass
            self._volume_solid_actor = None
        self._plotter.render()

    def display_volume_region(self, grid_x: np.ndarray, grid_y: np.ndarray,
                               grid_z: np.ndarray, reference_z: float):
        self.clear_volume_graphics()
        try:
            z_terrain = grid_z.copy()
            valid_mask = ~np.isnan(z_terrain)
            if not np.any(valid_mask):
                return
            z_terrain[~valid_mask] = reference_z
            z_ref_layer = np.full_like(z_terrain, reference_z)

            x3d = np.dstack((grid_x, grid_x))
            y3d = np.dstack((grid_y, grid_y))
            z3d = np.dstack((z_terrain, z_ref_layer))
            grid = pv.StructuredGrid(x3d, y3d, z3d)

            diff_2d  = z_terrain - reference_z
            diff_3d  = np.dstack((diff_2d, diff_2d))
            category_3d = np.where(diff_3d > 0, 1, -1)
            valid_3d = np.dstack((valid_mask, valid_mask)).astype(float)

            grid["Category"] = category_3d.flatten(order="F")
            grid["Valid"]    = valid_3d.flatten(order="F")

            solid_volume = grid.threshold(0.5, scalars="Valid")
            if solid_volume.n_points == 0:
                return

            from matplotlib.colors import ListedColormap
            cmap = ListedColormap(["#3b82f6", "#ef4444"])

            actor = self._plotter.add_mesh(
                solid_volume,
                scalars="Category",
                cmap=cmap,
                show_scalar_bar=False,
                name=f"_tmp_vol_solid_{len(self._temp_actors)}",
                opacity=0.9,
                reset_camera=False
            )
            self._temp_actors.append(actor)
            self._volume_solid_actor = actor
        except Exception as e:
            logger.error(f"Error generating 3D volume solid: {e}")
        self._plotter.render()

    # ------------------------------------------------------------------
    # Teardown
    # ------------------------------------------------------------------

    def disable_tools(self):
        self.picking_active = False

        style_ref = getattr(self, "_area_style_ref", None)
        if style_ref is not None:
            for obs_attr in ("_area_obs_press", "_area_obs_release"):
                obs_id = getattr(self, obs_attr, None)
                if obs_id is not None:
                    try:
                        style_ref.RemoveObserver(obs_id)
                    except Exception:
                        pass
                    setattr(self, obs_attr, None)
            self._area_style_ref = None

        wp_style = getattr(self, "_wp_style_ref", None)
        if wp_style is not None:
            for obs_attr in ("_wp_obs_press", "_wp_obs_release"):
                obs_id = getattr(self, obs_attr, None)
                if obs_id is not None:
                    try:
                        wp_style.RemoveObserver(obs_id)
                    except Exception:
                        pass
                    setattr(self, obs_attr, None)
            self._wp_style_ref = None

        self._plotter.disable_picking()
        self.clear_temporary_graphics()

        if self._measuring_widget:
            try:
                self._plotter.clear_measurements()
            except Exception:
                pass
            self._measuring_widget = None

        self._picking_callback = None
        logger.info("Interactive tools disabled")
