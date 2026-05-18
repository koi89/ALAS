"""
ALAS — Annotation Manager
Manages 3D text annotations pinned to world-space points in the viewport.
"""

import pyvista as pv
from app.logger import get_logger

logger = get_logger("ui.viewport.annotations")


class AnnotationManager:
    """Owns _annotation_actors and all annotation lifecycle methods."""

    def __init__(self, plotter):
        self._plotter = plotter
        self._annotation_actors: dict = {}   # ann_id → (sphere_actor, label_actor)

    def add(self, ann_id: int, point: tuple, text: str,
            color: str = "#00e5ff") -> None:
        ann_key = f"_ann_{ann_id}"

        pts = pv.PolyData([list(point)])
        sphere_actor = self._plotter.add_mesh(
            pts, color=color,
            point_size=16,
            render_points_as_spheres=True,
            name=f"{ann_key}_sphere",
            reset_camera=False,
        )

        label_actor = self._plotter.add_point_labels(
            [list(point)], [text],
            name=f"{ann_key}_label",
            always_visible=True,
            reset_camera=False,
            font_size=11,
            text_color="white",
            bold=True,
            shape_opacity=0.55,
            shape_color="#1a1a2e",
            margin=3,
        )

        self._annotation_actors[ann_id] = (sphere_actor, label_actor)
        self._plotter.render()
        logger.debug(f"Annotation {ann_id} added at {point}")

    def remove(self, ann_id: int) -> None:
        actors = self._annotation_actors.pop(ann_id, None)
        if actors:
            for a in actors:
                try:
                    self._plotter.remove_actor(a)
                except Exception:
                    pass
        self._plotter.render()

    def clear(self) -> None:
        for ann_id in list(self._annotation_actors.keys()):
            self.remove(ann_id)
