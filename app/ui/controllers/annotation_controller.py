"""
ALAS — Annotation Controller
Handles 3D annotation placement, removal, and the annotation dialog.
"""

from app.i18n import tr
from app.logger import get_logger

logger = get_logger("ui.annotation_controller")


class AnnotationController:
    """
    Owns the annotations dialog and all annotation lifecycle callbacks.
    """

    def __init__(self, window):
        self._w = window
        self._dialog = None
        self._next_id: int = 0
        self._entries: dict = {}
        self._pending_text: str = ""

    def start_tool(self):
        logger.info("Annotations tool activated")
        from app.ui.viewport.annotations_tool import AnnotationsToolDialog

        if self._dialog is None:
            self._dialog = AnnotationsToolDialog(self._w)
            self._dialog.add_requested.connect(self._on_add_requested)
            self._dialog.remove_requested.connect(self._on_remove)
            self._dialog.clear_all_requested.connect(self._on_clear_all)

        self._dialog.show()
        self._dialog.raise_()
        self._dialog.activateWindow()

    def _on_add_requested(self):
        if self._dialog is None:
            return
        text = self._dialog.ask_text()
        if not text:
            return
        self._pending_text = text
        self._w.viewport.enable_world_picking(self._on_world_pick)
        self._w._update_status(tr("ann.picking"))

    def _on_world_pick(self, x: float, y: float, z: float):
        text = self._pending_text
        self._pending_text = ""
        self._w.viewport.disable_tools()

        from app.ui.viewport.annotations_tool import AnnotationEntry
        ann_id = self._next_id
        self._next_id += 1

        entry = AnnotationEntry(id=ann_id, text=text, x=x, y=y, z=z)
        self._entries[ann_id] = entry

        self._w.viewport.add_annotation(ann_id, (x, y, z), text)
        if self._dialog is not None:
            self._dialog.add_annotation(entry)

        self._w._update_status(tr("ann.placed").format(text, x, y, z))
        logger.info(f"Annotation {ann_id} '{text}' placed at ({x:.2f}, {y:.2f}, {z:.2f})")

    def _on_remove(self, ann_id: int):
        self._entries.pop(ann_id, None)
        self._w.viewport.remove_annotation(ann_id)
        if self._dialog is not None:
            self._dialog.remove_annotation(ann_id)
        logger.info(f"Annotation {ann_id} removed")

    def _on_clear_all(self):
        self._entries.clear()
        self._w.viewport.clear_annotations()
        if self._dialog is not None:
            self._dialog.clear_all()
        logger.info("All annotations cleared")
