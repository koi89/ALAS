"""
ALAS — Figure Controller
Handles geometric figure placement, editing, dragging, and removal.
"""

from app.i18n import tr
from app.logger import get_logger

logger = get_logger("ui.figure_controller")


class FigureController:
    """
    Owns all figure dialog instances and the state maps that link
    figure ids to viewport actor names.
    """

    def __init__(self, window):
        self._w = window
        self._figures_dialog = None
        self._figures_history_dialog = None
        self._figure_actor_names: dict[int, str] = {}
        self._figure_entries: dict = {}
        self._pending_figure = None

    # ------------------------------------------------------------------
    # Dialogs
    # ------------------------------------------------------------------

    def show_figures_tool(self):
        from app.ui.viewport.figures_tool import FiguresToolDialog
        if self._figures_dialog is None:
            self._figures_dialog = FiguresToolDialog(self._w)
            self._figures_dialog.place_requested.connect(self._on_place_requested)
            self._figures_dialog.update_requested.connect(self._on_update_requested)
        self._figures_dialog.show()
        self._figures_dialog.raise_()
        self._figures_dialog.activateWindow()

    def _get_history_dialog(self):
        if self._figures_history_dialog is None:
            from app.ui.dialogs.figures_history_dialog import FiguresHistoryDialog
            self._figures_history_dialog = FiguresHistoryDialog(self._w)
            self._figures_history_dialog.remove_requested.connect(self._on_remove_requested)
            self._figures_history_dialog.clear_all_requested.connect(self._on_clear_all)
        return self._figures_history_dialog

    def show_figures_history(self):
        self._get_history_dialog().show_and_raise()

    # ------------------------------------------------------------------
    # Placement
    # ------------------------------------------------------------------

    def _on_place_requested(self, ftype: str, params: dict):
        self._pending_figure = (ftype, dict(params))
        self._w.viewport.enable_world_picking(self._on_world_pick)
        self._w._update_status(tr("fig.status_pick"))

    def _on_world_pick(self, x: float, y: float, z: float):
        if self._pending_figure is None:
            return
        ftype, params = self._pending_figure
        self._pending_figure = None
        self._w.viewport.disable_tools()

        from app.ui.viewport.figures_tool import params_summary
        dlg = self._get_history_dialog()
        entry = dlg.add_figure(ftype, (x, y, z), params)
        self._figure_actor_names[entry.id] = entry.actor_name
        self._figure_entries[entry.id] = {
            "ftype": ftype, "center": (x, y, z), "params": dict(params)
        }
        try:
            self._w.viewport.add_figure(ftype, (x, y, z), params, entry.actor_name)
        except Exception as e:
            logger.error(f"Failed to place figure: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self._w, tr("fig.title"), str(e))
            return
        self._w.viewport.register_figure_id(entry.actor_name, entry.id)
        self._w.layer_panel.add_figure_item(entry.id, ftype, params_summary(ftype, params))
        self._w.viewport.enable_figure_dragging(self._on_dragged)
        self._w._update_status(tr("fig.status_placed").format(x, y, z))
        logger.info(f"Figure #{entry.id} ({ftype}) placed at ({x:.3f}, {y:.3f}, {z:.3f})")

    # ------------------------------------------------------------------
    # Update / edit
    # ------------------------------------------------------------------

    def _on_update_requested(self, figure_id: int, ftype: str,
                              new_center: tuple, new_params: dict):
        from app.ui.viewport.figures_tool import params_summary
        info = self._figure_entries.get(figure_id)
        name = self._figure_actor_names.get(figure_id)
        if info is None or name is None:
            return
        info["params"] = dict(new_params)
        info["center"] = tuple(new_center)
        try:
            self._w.viewport.update_figure(ftype, new_center, new_params, name)
            if name in self._w.viewport.figures._figure_meta:
                ft, _, p = self._w.viewport.figures._figure_meta[name]
                self._w.viewport.figures._figure_meta[name] = (ft, list(new_center), p)
        except Exception as e:
            logger.error(f"Failed to update figure: {e}")
            return
        self._w.layer_panel.update_figure_item(figure_id, ftype,
                                               params_summary(ftype, new_params))
        if self._figures_history_dialog is not None:
            self._figures_history_dialog.update_entry(figure_id, new_params)
            self._figures_history_dialog.update_entry_center(figure_id, new_center)
        logger.info(f"Figure #{figure_id} updated: center={new_center} params={new_params}")

    def on_edit_from_layer(self, figure_id: int):
        info = self._figure_entries.get(figure_id)
        if info is None:
            return
        self.show_figures_tool()
        self._figures_dialog.load_figure(
            figure_id, info["ftype"], info["center"], info["params"]
        )

    # ------------------------------------------------------------------
    # Drag
    # ------------------------------------------------------------------

    def _on_dragged(self, figure_id: int, x: float, y: float, z: float):
        from app.ui.viewport.figures_tool import params_summary
        info = self._figure_entries.get(figure_id)
        if info is None:
            return
        info["center"] = (x, y, z)
        if self._figures_history_dialog is not None:
            self._figures_history_dialog.update_entry_center(figure_id, (x, y, z))
        self._w.layer_panel.update_figure_item(
            figure_id, info["ftype"], params_summary(info["ftype"], info["params"])
        )
        if (self._figures_dialog is not None
                and getattr(self._figures_dialog, "_edit_id", None) == figure_id):
            self._figures_dialog.update_center_display((x, y, z))
        logger.info(f"Figure #{figure_id} dragged to ({x:.3f}, {y:.3f}, {z:.3f})")

    # ------------------------------------------------------------------
    # Removal
    # ------------------------------------------------------------------

    def _on_remove_requested(self, figure_id: int):
        self._remove(figure_id)

    def on_remove_from_layer(self, figure_id: int):
        self._remove(figure_id)
        if self._figures_history_dialog is not None:
            self._figures_history_dialog.remove_entry(figure_id)

    def _remove(self, figure_id: int):
        name = self._figure_actor_names.pop(figure_id, None)
        self._figure_entries.pop(figure_id, None)
        if name:
            self._w.viewport.unregister_figure(name)
            self._w.viewport.remove_layer(name)
        self._w.layer_panel.remove_figure_item(figure_id)
        if (self._figures_dialog is not None
                and getattr(self._figures_dialog, "_edit_id", None) == figure_id):
            self._figures_dialog._exit_edit_mode()
        if not self._figure_actor_names:
            self._w.viewport.disable_figure_dragging()

    def _on_clear_all(self):
        for name in list(self._figure_actor_names.values()):
            self._w.viewport.unregister_figure(name)
            self._w.viewport.remove_layer(name)
        self._figure_actor_names.clear()
        self._figure_entries.clear()
        self._w.layer_panel.clear_figure_items()
        self._w.viewport.disable_figure_dragging()
