"""
ALAS — Figure Manager
Manages geometric figure actors and drag interaction in the viewport.
"""

import pyvista as pv
from app.logger import get_logger

logger = get_logger("ui.viewport.figures")


class FigureManager:
    """
    Owns figure metadata and drag observers.
    Takes a reference to the viewport's _current_actors dict so figure actors
    participate in the same layer-management lifecycle as point clouds.
    """

    def __init__(self, plotter, current_actors: dict):
        self._plotter = plotter
        self._current_actors = current_actors   # shared reference
        self._figure_meta: dict = {}            # name → (ftype, center, params)
        self._figure_id_map: dict = {}          # name → figure_id
        self._drag_observers_active = False

    # ------------------------------------------------------------------
    # Mesh building
    # ------------------------------------------------------------------

    @staticmethod
    def _build_mesh(figure_type: str, center, params: dict):
        cx, cy, cz = float(center[0]), float(center[1]), float(center[2])
        if figure_type == "cube":
            s = float(params.get("size", 1.0))
            h = s / 2.0
            return pv.Box(bounds=(cx - h, cx + h, cy - h, cy + h, cz - h, cz + h))
        if figure_type == "sphere":
            r = float(params.get("radius", 1.0))
            return pv.Sphere(radius=r, center=(cx, cy, cz))
        if figure_type == "cylinder":
            r = float(params.get("radius", 1.0))
            h = float(params.get("height", 2.0))
            return pv.Cylinder(center=(cx, cy, cz + h / 2.0),
                               direction=(0, 0, 1), radius=r, height=h, resolution=48)
        if figure_type == "cone":
            r = float(params.get("radius", 1.0))
            h = float(params.get("height", 2.0))
            return pv.Cone(center=(cx, cy, cz + h / 2.0),
                           direction=(0, 0, 1), radius=r, height=h, resolution=48)
        if figure_type == "plane":
            w = float(params.get("size_x", 2.0))
            d = float(params.get("size_y", 2.0))
            return pv.Plane(center=(cx, cy, cz), direction=(0, 0, 1),
                            i_size=w, j_size=d)
        raise ValueError(f"Unknown figure type: {figure_type}")

    # ------------------------------------------------------------------
    # Actor lifecycle
    # ------------------------------------------------------------------

    def add(self, figure_type: str, center, params: dict,
            name: str, color: str = "#a855f7", opacity: float = 0.55):
        mesh = self._build_mesh(figure_type, center, params)
        actor = self._plotter.add_mesh(
            mesh, color=color, opacity=opacity, name=name,
            show_edges=True, edge_color="#ffffff", line_width=1,
            reset_camera=False,
        )
        self._current_actors[name] = actor
        self._figure_meta[name] = (figure_type, list(center), dict(params))
        self._plotter.render()
        return actor

    def update(self, figure_type: str, center, params: dict,
               name: str, color: str = "#a855f7", opacity: float = 0.55):
        return self.add(figure_type, center, params, name, color, opacity)

    def register_id(self, name: str, figure_id: int):
        self._figure_id_map[name] = figure_id

    def unregister(self, name: str):
        self._figure_meta.pop(name, None)
        self._figure_id_map.pop(name, None)

    # ------------------------------------------------------------------
    # Drag interaction
    # ------------------------------------------------------------------

    def enable_dragging(self, on_figure_moved):
        import vtk as _vtk
        if self._drag_observers_active:
            return

        prop_picker = _vtk.vtkPropPicker()
        wp_picker   = _vtk.vtkWorldPointPicker()
        self._drag_prop_picker = prop_picker
        self._drag_wp_picker   = wp_picker
        self._drag_on_moved    = on_figure_moved
        self._drag_active      = False
        self._drag_name        = None
        self._drag_figure_id   = None
        self._drag_center      = None
        self._drag_press_screen = None

        iren  = self._plotter.iren.interactor
        style = iren.GetInteractorStyle()
        self._drag_style_ref = style

        def _on_press(obj, event):
            pos = iren.GetEventPosition()
            self._drag_press_screen = pos

            prop_picker.Pick(pos[0], pos[1], 0, self._plotter.renderer)
            hit_actor = prop_picker.GetActor()

            name = None
            if hit_actor is not None:
                for n, a in self._current_actors.items():
                    if a is hit_actor and n in self._figure_meta:
                        name = n
                        break

            if name is not None:
                self._drag_active    = True
                self._drag_name      = name
                self._drag_figure_id = self._figure_id_map.get(name)
                _, center, _ = self._figure_meta[name]
                self._drag_center    = list(center)
                wp_picker.Pick(pos[0], pos[1], 0, self._plotter.renderer)
                p = wp_picker.GetPickPosition()
                self._drag_pick_offset = (
                    self._drag_center[0] - p[0],
                    self._drag_center[1] - p[1],
                )
            else:
                self._drag_active = False
                obj.OnLeftButtonDown()

        def _on_move(obj, event):
            if not self._drag_active:
                obj.OnMouseMove()
                return
            pos = iren.GetEventPosition()
            wp_picker.Pick(pos[0], pos[1], 0, self._plotter.renderer)
            p = wp_picker.GetPickPosition()
            nx = p[0] + self._drag_pick_offset[0]
            ny = p[1] + self._drag_pick_offset[1]
            nz = self._drag_center[2]
            self._drag_center = [nx, ny, nz]
            ftype, _, params = self._figure_meta[self._drag_name]
            self._figure_meta[self._drag_name] = (ftype, [nx, ny, nz], params)
            mesh = self._build_mesh(ftype, (nx, ny, nz), params)
            actor = self._plotter.add_mesh(
                mesh, color="#a855f7", opacity=0.55, name=self._drag_name,
                show_edges=True, edge_color="#ffffff", line_width=1,
                reset_camera=False,
            )
            self._current_actors[self._drag_name] = actor
            self._plotter.render()

        def _on_release(obj, event):
            if not self._drag_active:
                obj.OnLeftButtonUp()
                return
            self._drag_active = False
            cx, cy, cz = self._drag_center
            if self._drag_figure_id is not None:
                self._drag_on_moved(self._drag_figure_id, cx, cy, cz)
            obj.OnLeftButtonUp()

        self._drag_obs_press   = style.AddObserver("LeftButtonPressEvent",   _on_press)
        self._drag_obs_move    = style.AddObserver("MouseMoveEvent",          _on_move)
        self._drag_obs_release = style.AddObserver("LeftButtonReleaseEvent",  _on_release)
        self._drag_observers_active = True
        logger.info("Figure dragging enabled")

    def disable_dragging(self):
        style = getattr(self, "_drag_style_ref", None)
        if style is None:
            return
        for attr in ("_drag_obs_press", "_drag_obs_move", "_drag_obs_release"):
            obs = getattr(self, attr, None)
            if obs is not None:
                try:
                    style.RemoveObserver(obs)
                except Exception:
                    pass
                setattr(self, attr, None)
        self._drag_style_ref = None
        self._drag_observers_active = False
