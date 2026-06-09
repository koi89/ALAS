"""
ALAS — Contour Lines Analysis Tab
Follows the same BaseAnalysisTab / AnalysisResultsWindow pattern as
Geomorphology, Hydrology, Vegetation, and Multitemporal.
"""

from __future__ import annotations
import os
import shutil
import tempfile

from PyQt6.QtWidgets import (
    QVBoxLayout, QGroupBox, QFormLayout, QDoubleSpinBox,
    QCheckBox, QPushButton, QMessageBox, QFileDialog, QComboBox,
)
from PyQt6.QtCore import Qt

from app.core.raster_layer import RasterLayer
from app.i18n import tr
from app.logger import get_logger

from .analysis_base import BaseAnalysisTab, show_history_dialog
from .results_window import AnalysisResultsWindow

logger = get_logger("ui.contours_tab")


# ---------------------------------------------------------------------------
# Results window
# ---------------------------------------------------------------------------

class ContoursResultsWindow(AnalysisResultsWindow):
    """
    Shows a matplotlib contour-map image + statistics.
    results dict: {"contour_lines": {"contours": [...], "interval": float, "crs_epsg": int|None}}
    """

    TAB_TYPE = "contours"

    def __init__(self, results: dict, parent=None):
        self._results_data = results          # store before super().__init__ calls _setup_ui
        super().__init__(results, parent)

    def _setup_ui(self, results: dict):
        super()._setup_ui(results)
        # Add Export Shapefile to the window's toolbar
        from PyQt6.QtWidgets import QToolBar
        from PyQt6.QtGui import QAction
        tb = QToolBar()
        tb.setMovable(False)
        act = QAction(tr("contour.export_shp"), self)
        act.triggered.connect(self._export_shapefile)
        tb.addAction(act)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, tb)

    def _render_layer(self, layer_type: str, contour_data):
        from app.processing.contours import render_contour_figure
        from PyQt6.QtGui import QPixmap

        contours = contour_data["contours"]
        interval = contour_data["interval"]
        img_path = render_contour_figure(contours, interval)
        # Keep the path so render_for_pdf can reuse it
        contour_data["_img_path"] = img_path

        pixmap = QPixmap(img_path)
        pixmap = pixmap.scaledToWidth(800, Qt.TransformationMode.SmoothTransformation)
        return None, None, pixmap

    def _get_legend_text(self, layer_type: str, contour_data=None) -> str:
        if not contour_data:
            return ""
        interval = contour_data.get("interval", "?")
        elevs = [c["elevation"] for c in contour_data.get("contours", [])]
        if not elevs:
            return ""
        return (
            f"<b>{tr('contour.title')}</b><br>"
            f"• {tr('contour.interval')} {interval} m | "
            f"{tr('contour.min_elev')} {min(elevs):.1f} m – "
            f"{tr('contour.max_elev')} {max(elevs):.1f} m"
        )

    def _collect_layer_stats(self, layer_type: str, contour_data) -> dict:
        if not isinstance(contour_data, dict):
            return {}
        contours = contour_data.get("contours", [])
        if not contours:
            return {}
        elevs = [c["elevation"] for c in contours]
        return {
            "Contour segments":  len(contours),
            "Unique levels":     len(set(elevs)),
            "Interval (m)":      contour_data.get("interval", "—"),
            "Min elevation (m)": f"{min(elevs):.1f}",
            "Max elevation (m)": f"{max(elevs):.1f}",
            "Total vertices":    sum(len(c["xy"]) for c in contours),
        }

    def _export_shapefile(self):
        contour_data = self._results_data.get("contour_lines", {})
        contours = contour_data.get("contours", [])
        if not contours:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("contour.export"), "",
            "Shapefile (*.shp);;GeoJSON (*.geojson);;GeoPackage (*.gpkg)"
        )
        if not path:
            return
        try:
            from app.processing.contours import export_contours
            export_contours(contours, path, crs_epsg=contour_data.get("crs_epsg"))
            QMessageBox.information(
                self, tr("success.exported"),
                tr("contour.exported").format(path)
            )
        except Exception as e:
            logger.error(f"Shapefile export failed: {e}")
            QMessageBox.critical(self, tr("error.export_failed"), str(e))

    @classmethod
    def render_for_pdf(cls, results: dict) -> tuple:
        temp_dir = tempfile.mkdtemp(prefix="alas_pdf_contours_")
        pdf_data = {}

        for layer_type, contour_data in results.items():
            img_path = None
            try:
                # Reuse already-rendered image if available
                src = contour_data.get("_img_path")
                if src and os.path.exists(src):
                    img_path = os.path.join(temp_dir, f"{layer_type}.png")
                    shutil.copy(src, img_path)
                else:
                    from app.processing.contours import render_contour_figure
                    src = render_contour_figure(
                        contour_data["contours"], contour_data["interval"]
                    )
                    img_path = os.path.join(temp_dir, f"{layer_type}.png")
                    shutil.copy(src, img_path)
            except Exception as e:
                logger.warning(f"Cannot render contour image for PDF: {e}")

            contours = contour_data.get("contours", [])
            elevs = [c["elevation"] for c in contours]
            stats = {}
            if elevs:
                stats = {
                    "Contour segments":  len(contours),
                    "Unique levels":     len(set(elevs)),
                    "Interval (m)":      contour_data.get("interval"),
                    "Min elevation (m)": round(min(elevs), 1),
                    "Max elevation (m)": round(max(elevs), 1),
                }

            pdf_data[layer_type] = {
                "image":  img_path,
                "legend": f"{tr('contour.interval')} {contour_data.get('interval')} m",
                "stats":  stats,
            }

        return pdf_data, temp_dir


# ---------------------------------------------------------------------------
# Tab widget
# ---------------------------------------------------------------------------

class ContoursTab(BaseAnalysisTab):
    TAB_TYPE = "contours"

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Source raster
        grp_src = QGroupBox(tr("contour.input"))
        form_src = QFormLayout(grp_src)
        self._raster_combo = self._make_raster_combo()
        form_src.addRow(tr("contour.raster"), self._raster_combo)
        layout.addWidget(grp_src)

        # Parameters
        grp_p = QGroupBox(tr("analysis.parameters"))
        form_p = QFormLayout(grp_p)
        form_p.setSpacing(8)

        self._interval_spin = QDoubleSpinBox()
        self._interval_spin.setRange(0.1, 1000.0)
        self._interval_spin.setValue(1.0)
        self._interval_spin.setSuffix(" m")
        self._interval_spin.setDecimals(1)
        form_p.addRow(tr("contour.interval"), self._interval_spin)

        self._auto_chk = QCheckBox(tr("contour.auto_range"))
        self._auto_chk.setChecked(True)
        self._auto_chk.stateChanged.connect(self._on_auto_changed)
        form_p.addRow("", self._auto_chk)

        self._min_spin = QDoubleSpinBox()
        self._min_spin.setRange(-10000.0, 10000.0)
        self._min_spin.setValue(0.0)
        self._min_spin.setSuffix(" m")
        self._min_spin.setDecimals(1)
        self._min_spin.setEnabled(False)

        self._max_spin = QDoubleSpinBox()
        self._max_spin.setRange(-10000.0, 10000.0)
        self._max_spin.setValue(100.0)
        self._max_spin.setSuffix(" m")
        self._max_spin.setDecimals(1)
        self._max_spin.setEnabled(False)

        form_p.addRow(tr("contour.min_elev"), self._min_spin)
        form_p.addRow(tr("contour.max_elev"), self._max_spin)
        layout.addWidget(grp_p)

        # Buttons — same layout order as other tabs
        self._btn_run = QPushButton(tr("contour.execute"))
        self._btn_run.setObjectName("primary")
        self._btn_run.clicked.connect(self._run)
        layout.addWidget(self._btn_run)

        self._btn_view = QPushButton(tr("analysis.view_results"))
        self._btn_view.setEnabled(False)
        self._btn_view.clicked.connect(self._show_latest_results)
        layout.addWidget(self._btn_view)

        self._btn_history = QPushButton(tr("contour.history"))
        self._btn_history.clicked.connect(self._show_history)
        layout.addWidget(self._btn_history)

        layout.addStretch()

    # --- BaseAnalysisTab interface ---

    def _get_run_btn(self) -> QPushButton:
        return self._btn_run

    def _get_view_btn(self) -> QPushButton:
        return self._btn_view

    # --- Combo helpers ---

    def _make_raster_combo(self):
        combo = QComboBox()
        self._fill_combo(combo)
        return combo

    def _fill_combo(self, combo: QComboBox):
        current = combo.currentData()
        combo.clear()
        new_idx = 0
        for i, entry in enumerate(self.layer_manager.get_all_entries()):
            if entry.is_raster:
                combo.addItem(entry.name, i)
                if i == current:
                    new_idx = combo.count() - 1
        if combo.count() == 0:
            combo.addItem(tr("analysis.no_raster_layers"), -1)
        combo.setCurrentIndex(new_idx)

    def refresh_combos(self):
        self._fill_combo(self._raster_combo)

    # --- UI helpers ---

    def _on_auto_changed(self, _state):
        manual = not self._auto_chk.isChecked()
        self._min_spin.setEnabled(manual)
        self._max_spin.setEnabled(manual)

    # --- Run logic ---

    def _run(self):
        idx = self._raster_combo.currentData()
        if idx is None or idx < 0:
            QMessageBox.warning(self, tr("dialog.confirm"), tr("contour.error_no_raster"))
            return

        raster = self.layer_manager.get_layer(idx)
        if not isinstance(raster, RasterLayer):
            return

        self._pending_layer_name = raster.name
        self._pending_crs_epsg   = raster.crs_epsg
        interval = self._interval_spin.value()
        min_elev = None if self._auto_chk.isChecked() else self._min_spin.value()
        max_elev = None if self._auto_chk.isChecked() else self._max_spin.value()

        def _compute():
            from app.processing.contours import generate_contours
            return generate_contours(raster, interval, min_elev, max_elev)

        self._show_loading()
        self._run_worker(_compute, lambda c: self._on_result(c, interval))

    def _on_result(self, contours: list, interval: float):
        n = len(contours)
        self._latest_results = {
            "contour_lines": {
                "contours":  contours,
                "interval":  interval,
                "crs_epsg":  self._pending_crs_epsg,
            }
        }
        self._append_history(self._pending_layer_name, self._latest_results)
        self._btn_view.setEnabled(True)
        msg = tr("contour.generated").format(n, interval)
        QMessageBox.information(
            self, tr("dialog.confirm"),
            f"{tr('contour.completed')}\n\n{msg}"
        )

    def _show_latest_results(self):
        if hasattr(self, "_latest_results") and self._latest_results:
            self._open_results_window(self._latest_results, ContoursResultsWindow)

    def _show_history(self):
        show_history_dialog(
            self,
            self.main_window,
            history_attr="_contours_history",
            tab_type="contours",
            history_dialog_attr="_contours_history_dialog",
            pdf_title_key="contour.pdf_title",
            source_label_key="contour.history_raster",
            results_window_class=ContoursResultsWindow,
        )
