"""
ALAS — Main Window
Main window: central 3D viewport, dock panels, menu and toolbar.
"""

import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QDockWidget, QFileDialog, QMessageBox,
    QLabel, QWidget, QVBoxLayout, QApplication,
    QTabWidget, QToolBar, QStatusBar, QPushButton, QDialog
)
from PyQt6.QtCore import Qt, QSize, QThreadPool, QTimer
from PyQt6.QtGui import QAction, QKeySequence, QIcon, QPixmap, QPainter, QFont, QColor, QPainterPath
import numpy as np

from app.core.project import Project, UserPreferences
from app.core.layer_manager import LayerManager
from app.core.point_cloud import PointCloudData
from app.core.raster_layer import RasterLayer
from app.ui.viewport.viewport_3d import Viewport3D
from app.ui.panels.layer_panel import LayerPanel
from app.ui.panels.properties_panel import PropertiesPanel
from app.ui.panels.tools_panel import ToolsPanel
from app.ui.panels.statistics_panel import StatisticsPanel
from app.ui.panels.log_panel import LogPanel
from app.processing.workers import FileLoadWorker, ProcessingWorker, ProcessingWorkerSignals
from app.ui.widgets import LoadingOverlay
from app.config import (
    APP_NAME, APP_FULL_NAME, APP_VERSION,
    POINT_CLOUD_FILTER, RASTER_FILTER, POINT_CLOUD_EXTENSIONS,
    RASTER_EXTENSIONS
)
from app.i18n import tr, set_language, get_language
from app.ui.menu_bar import build_menu_bar
from app.ui.controllers.measurement_controller import MeasurementController
from app.ui.controllers.figure_controller import FigureController
from app.ui.controllers.annotation_controller import AnnotationController
from app.logger import get_logger

logger = get_logger("ui.main_window")


class MainWindow(QMainWindow):
    """ALAS main window."""

    def __init__(self, user=None, session_token: str = None):
        super().__init__()

        self._current_user = user
        self._session_token = session_token
        self._login_shown = False

        # Core objects
        self.project = Project()
        self.preferences = UserPreferences()
        self.layer_manager = LayerManager(self)
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(4)

        # Apply saved language
        saved_lang = self.preferences.get("language", "es")
        set_language(saved_lang)

        # Coordinate picker (small enough to live here)
        self._coord_picker_dialog = None

        # Setup UI
        self._setup_window()
        self._setup_viewport()
        self._setup_panels()
        self._setup_menu_bar()
        self._setup_status_bar()
        self._connect_signals()
        self._setup_shortcuts()

        # Controllers (depend on viewport + panels being ready)
        self._measurements = MeasurementController(self)
        self._figures      = FigureController(self)
        self._annotations  = AnnotationController(self)

        self._restore_state()
        logger.info(f"{APP_NAME} v{APP_VERSION} started")

    # ==================================================================
    # Window setup
    # ==================================================================

    def _setup_window(self):
        self.setWindowTitle(f"{APP_NAME} — {APP_FULL_NAME}")
        self.setMinimumSize(1200, 800)
        self.resize(1600, 1000)
        self.setDockOptions(
            QMainWindow.DockOption.AllowTabbedDocks |
            QMainWindow.DockOption.AllowNestedDocks |
            QMainWindow.DockOption.AnimatedDocks
        )

    def _setup_viewport(self):
        self.viewport = Viewport3D(self)
        self.setCentralWidget(self.viewport)
        self._loading_overlay = LoadingOverlay(self)
        self._loading_overlay.hide()

    def _setup_panels(self):
        self.layer_panel = LayerPanel(self.layer_manager, self)
        dock_layers = QDockWidget(tr("panel.layers"), self)
        dock_layers.setWidget(self.layer_panel)
        dock_layers.setMinimumWidth(220)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock_layers)

        right_tabs = QTabWidget()
        self.properties_panel = PropertiesPanel(self.layer_manager, self)
        right_tabs.addTab(self.properties_panel, tr("panel.properties"))
        self.tools_panel = ToolsPanel(self)
        right_tabs.addTab(self.tools_panel, tr("panel.tools"))
        self.statistics_panel = StatisticsPanel(self.layer_manager, self)
        right_tabs.addTab(self.statistics_panel, tr("panel.statistics"))

        dock_right = QDockWidget(tr("panel.properties"), self)
        dock_right.setWidget(right_tabs)
        dock_right.setMinimumWidth(280)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock_right)

        self.log_panel = LogPanel(self)
        dock_log = QDockWidget(tr("panel.log"), self)
        dock_log.setWidget(self.log_panel)
        dock_log.setMaximumHeight(200)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock_log)

    def _setup_menu_bar(self):
        build_menu_bar(self)

    def _setup_status_bar(self):
        self.statusBar().setStyleSheet("QStatusBar { font-size: 12px; }")
        self._status_label = QLabel(tr("status.ready"))
        self.statusBar().addWidget(self._status_label, 1)
        self._crs_label = QLabel(tr("status.no_crs"))
        self._crs_label.setStyleSheet("color: #a855f7; font-weight: 600;")
        self.statusBar().addPermanentWidget(self._crs_label)
        self._points_label = QLabel("0 " + tr("status.points"))
        self.statusBar().addPermanentWidget(self._points_label)

    def _setup_shortcuts(self):
        self._act_clear = QAction(tr("action.reset_view"), self)
        self._act_clear.setShortcut(QKeySequence("Esc"))
        self._act_clear.triggered.connect(self._clear_active_tools)
        self.addAction(self._act_clear)

    def _clear_active_tools(self):
        self.viewport.disable_tools()
        self._update_status(tr("status.ready"))
        logger.info("Tools cleared by user")

    # ==================================================================
    # Signal connections
    # ==================================================================

    def _connect_signals(self):
        self.tools_panel.point_size_changed.connect(self.viewport.set_point_size)
        self.tools_panel.colorize_mode_changed.connect(self._on_colorize_mode_changed)
        self.tools_panel.view_reset_requested.connect(self.viewport.reset_camera)
        self.tools_panel.view_top_requested.connect(self.viewport.set_view_top)
        self.tools_panel.view_front_requested.connect(self.viewport.set_view_front)
        self.tools_panel.view_side_requested.connect(self.viewport.set_view_side)

        self.layer_panel.zoom_to_layer_requested.connect(self._zoom_to_layer)
        self.layer_panel.export_layer_requested.connect(self._export_layer)
        self.layer_panel.figure_edit_requested.connect(
            lambda fid: self._figures.on_edit_from_layer(fid)
        )
        self.layer_panel.figure_remove_requested.connect(
            lambda fid: self._figures.on_remove_from_layer(fid)
        )

        self.layer_manager.layer_added.connect(self._on_layer_added)
        self.layer_manager.layer_removed.connect(lambda _: self._update_points_display())
        self.layer_manager.layer_visibility_changed.connect(self._on_visibility_changed)
        self.layer_manager.active_layer_changed.connect(self._on_active_layer_changed)

    def _on_layer_added(self, index: int):
        self._update_points_display()
        entry = self.layer_manager.get_entry(index)
        if not entry:
            return
        if entry.is_point_cloud:
            colorize_by = self.viewport._colorize_mode
            name = entry.name
            layer = entry.layer
            self._run_processing(
                Viewport3D.prepare_display_data,
                layer, colorize_by,
                on_result=lambda cloud: self.viewport.render_prepared_cloud(cloud, name),
            )
        elif entry.is_raster:
            self.viewport.display_raster_surface(entry.layer, name=entry.name)

    # ==================================================================
    # Status bar helpers
    # ==================================================================

    def _make_avatar_pixmap(self, full_name: str, size: int = 28) -> QPixmap:
        parts = full_name.strip().split()
        initials = (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()
        px = QPixmap(size, size)
        px.fill(Qt.GlobalColor.transparent)
        painter = QPainter(px)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        painter.fillPath(path, QColor("#333348"))
        painter.setPen(QColor("#c0c0e0"))
        font = QFont("Segoe UI", size // 3, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(0, 0, size, size, Qt.AlignmentFlag.AlignCenter, initials)
        painter.end()
        return px

    def _update_status(self, message: str):
        self._status_label.setText(message)

    def _update_crs_display(self, epsg: int = None):
        if epsg:
            self._crs_label.setText(f"{tr('crs.epsg_prefix')}{epsg}")
        else:
            self._crs_label.setText(tr("status.no_crs"))

    def _update_points_display(self):
        total = sum(
            e.layer.point_count for e in self.layer_manager.get_all_entries()
            if e.is_point_cloud
        )
        self._points_label.setText(f"{total:,} {tr('status.points')}")

    # ==================================================================
    # File operations
    # ==================================================================

    def _open_file(self):
        last_dir = self.preferences.get("last_import_dir", "")
        file_path, _ = QFileDialog.getOpenFileName(
            self, tr("action.open"), last_dir,
            f"{POINT_CLOUD_FILTER};;{RASTER_FILTER}"
        )
        if file_path:
            self._load_file(file_path)

    def _open_multiple_files(self):
        last_dir = self.preferences.get("last_import_dir", "")
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, tr("action.open_multiple"), last_dir, POINT_CLOUD_FILTER
        )
        for fp in file_paths:
            self._load_file(fp)

    def _load_file(self, file_path: str):
        self.preferences.set("last_import_dir", str(Path(file_path).parent))
        self.preferences.add_recent_file(file_path)
        ext = Path(file_path).suffix.lower()
        self._update_status(tr("status.loading"))

        kwargs = {}
        if ext in POINT_CLOUD_EXTENSIONS:
            loader_func = PointCloudData.from_file
            try:
                import laspy
                from PyQt6.QtWidgets import QInputDialog
                with laspy.open(file_path) as f:
                    total_points = f.header.point_count
                if total_points > 1000000:
                    reply = QMessageBox.question(
                        self, tr("action.open"),
                        tr("msg.decimate_question").format(total_points),
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        target, ok = QInputDialog.getInt(
                            self, tr("msg.decimate_title"), tr("msg.target_points"),
                            min(5000000, total_points), 10000, total_points, 100000
                        )
                        if ok:
                            kwargs['max_points'] = target
            except Exception as e:
                logger.warning(f"Could not read quick header of {file_path}: {e}")
        elif ext in RASTER_EXTENSIONS:
            loader_func = RasterLayer.from_file
        else:
            self._update_status(tr("status.ready"))
            return

        worker = FileLoadWorker(file_path, loader_func, **kwargs)
        worker.signals.started.connect(lambda: self._loading_overlay.show_loading())
        worker.signals.result.connect(lambda res: self._on_file_loaded(res, ext, file_path))
        worker.signals.error.connect(lambda err: self._on_file_load_error(err, file_path))
        worker.signals.finished.connect(lambda: self._loading_overlay.hide_loading())
        self.thread_pool.start(worker)

    def _on_file_loaded(self, result, ext, file_path):
        if ext in POINT_CLOUD_EXTENSIONS:
            self.layer_manager.add_layer(result)
            self.viewport.reset_camera()
            if result.crs_epsg:
                self._update_crs_display(result.crs_epsg)
                self.preferences.last_crs = result.crs_epsg
            else:
                self._update_crs_display(None)
                self._prompt_crs_assignment(result)
        elif ext in RASTER_EXTENSIONS:
            self.layer_manager.add_layer(result)
            self.viewport.reset_camera()
            if result.crs_epsg:
                self._update_crs_display(result.crs_epsg)
        self._update_status(tr("success.loaded"))
        self.project.loaded_files.append(file_path)

    def _on_file_load_error(self, error_msg, file_path):
        logger.error(f"Error loading {file_path}: {error_msg}")
        QMessageBox.critical(self, tr("error.processing_failed"), str(error_msg))
        self._update_status(tr("status.ready"))

    def _run_processing(self, func, *args, on_result, on_error=None, **kwargs):
        self._update_status(tr("status.processing"))
        worker = ProcessingWorker(func, *args, **kwargs)
        worker.signals.started.connect(self._loading_overlay.show_loading)
        worker.signals.result.connect(on_result)
        worker.signals.error.connect(on_error if on_error is not None else self._on_processing_error)
        worker.signals.finished.connect(self._on_processing_finished)
        self.thread_pool.start(worker)

    def _on_processing_error(self, error_msg: str):
        QMessageBox.critical(self, tr("crs.error"), error_msg)

    def _on_processing_finished(self):
        self._loading_overlay.hide_loading()
        self._update_status(tr("status.ready"))

    def _prompt_crs_assignment(self, pc: PointCloudData):
        from PyQt6.QtWidgets import QInputDialog
        last_crs = self.preferences.last_crs
        default_text = str(last_crs) if last_crs else "25830"
        epsg_str, ok = QInputDialog.getText(
            self, tr("prop.crs"),
            f"{tr('error.no_crs')}\n\n{tr('msg.enter_epsg')}",
            text=default_text,
        )
        if ok and epsg_str.strip().isdigit():
            epsg = int(epsg_str.strip())
            pc.crs_epsg = epsg
            try:
                from pyproj import CRS
                pc.crs_wkt = CRS.from_epsg(epsg).to_wkt()
            except Exception:
                pass
            self._update_crs_display(epsg)
            self.preferences.last_crs = epsg

    # ==================================================================
    # Project operations
    # ==================================================================

    def _save_project(self):
        last_dir = self.preferences.get("last_export_dir", "")
        path, _ = QFileDialog.getSaveFileName(
            self, tr("action.save_project"), last_dir, "ALAS Project (*.alas)"
        )
        if path:
            self.project.save(path)
            self._update_status(tr("status.ready"))

    def _load_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr("action.load_project"), "", "ALAS Project (*.alas)"
        )
        if path:
            try:
                self.project = Project.load(path)
                self._update_status(tr("status.ready"))
            except Exception as e:
                QMessageBox.critical(self, tr("crs.error"), str(e))

    # ==================================================================
    # Viewport interactions
    # ==================================================================

    def _on_colorize_mode_changed(self, mode: str):
        entry = self.layer_manager.active_layer
        if entry and entry.is_point_cloud:
            self.viewport.update_colorization(entry.layer, mode)

    def _on_visibility_changed(self, index: int, visible: bool):
        entry = self.layer_manager.get_entry(index)
        if entry:
            self.viewport.set_layer_visibility(entry.name, visible)

    def _on_active_layer_changed(self, index: int):
        entry = self.layer_manager.get_entry(index)
        if entry and (entry.is_point_cloud or entry.is_raster):
            self._update_crs_display(entry.layer.crs_epsg)

    def _zoom_to_layer(self, index: int):
        entry = self.layer_manager.get_entry(index)
        if entry:
            self.viewport.zoom_to_bounds(entry.layer.bounds)
            self.viewport.reset_camera()

    # ==================================================================
    # Processing actions
    # ==================================================================

    def _show_batch_dialog(self):
        from app.ui.dialogs.batch_dialog import BatchProcessingDialog
        BatchProcessingDialog(self).exec()

    def _show_classification_dialog(self):
        from app.ui.dialogs.classification_dialog import ClassificationDialog
        entry = self.layer_manager.active_layer
        if not entry or not entry.is_point_cloud:
            QMessageBox.information(self, tr("dialog.info"), tr("msg.select_point_cloud"))
            return
        dlg = ClassificationDialog(entry.layer, self)
        if dlg.exec():
            result = dlg.get_result()
            if result is not None:
                entry.layer.classification = result
                entry.layer._hag_cache = None
                self.viewport.update_colorization(entry.layer, "classification")
                self._update_status(tr("success.classification_done"))
                classification_data = dlg.get_classification_data()
                if classification_data is not None:
                    algo = classification_data.get("algorithm", "unknown")
                    self._measurements.record_classification(algo, classification_data)
                    ground_points = classification_data.get("ground_points", 0)
                    total_points  = classification_data.get("total_points", 0)
                    reply = QMessageBox.question(
                        self, tr("class_hist.results_title"),
                        tr("class_hist.results_message").format(
                            f"{ground_points:,}", f"{total_points:,}"
                        ),
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        self._measurements.show_classification_history()

    def _show_dem_dialog(self):
        from app.ui.dialogs.dem_dialog import DEMDialog
        entry = self.layer_manager.active_layer
        if not entry or not entry.is_point_cloud:
            QMessageBox.information(self, tr("dialog.info"), tr("msg.select_point_cloud"))
            return
        dlg = DEMDialog(entry.layer, self)
        if dlg.exec():
            rasters = dlg.get_results()
            if rasters:
                for raster in rasters:
                    self.layer_manager.add_layer(raster)
                self._update_status(tr("success.dem_generated"))

    def _show_analysis_dialog(self, tab_name: str):
        if not hasattr(self, "_analysis_dialog") or self._analysis_dialog is None:
            from app.ui.dialogs.analysis.analysis_dialog import AnalysisDialog
            self._analysis_dialog = AnalysisDialog(tab_name, self.layer_manager, self)
            self._analysis_dialog.setWindowFlags(Qt.WindowType.Window)
        else:
            self._analysis_dialog.set_tab(tab_name)
        self._analysis_dialog.show()
        self._analysis_dialog.raise_()
        self._analysis_dialog.activateWindow()

    def _show_geomorphology_dialog(self):
        self._show_analysis_dialog("geomorphology")

    def _show_hydrology_dialog(self):
        self._show_analysis_dialog("hydrology")

    def _show_vegetation_dialog(self):
        self._show_analysis_dialog("vegetation")

    def _show_multitemporal_dialog(self):
        self._show_analysis_dialog("multitemporal")

    def _show_reports_dialog(self):
        if not self._current_user:
            QMessageBox.information(self, tr("dialog.info"), tr("reports.no_user"))
            return
        if not hasattr(self, "_reports_dialog") or self._reports_dialog is None:
            from app.ui.dialogs.reports_dialog import ReportsDialog
            self._reports_dialog = ReportsDialog(self._current_user, self._session_token, self)
        self._reports_dialog.show_and_raise()

    def _show_reproject_dialog(self):
        from app.ui.dialogs.crs_dialog import CRSDialog
        entry = self.layer_manager.active_layer
        if not entry or not entry.is_point_cloud:
            QMessageBox.information(self, tr("dialog.info"), tr("msg.select_point_cloud"))
            return
        CRSDialog(entry.layer, self).exec()

    def _merge_tiles(self):
        clouds = self.layer_manager.get_point_clouds()
        if len(clouds) < 2:
            QMessageBox.information(self, tr("dialog.info"), tr("msg.at_least_2_clouds"))
            return
        def _on_result(merged):
            self.layer_manager.add_layer(merged)
            self.viewport.reset_camera()
        self._run_processing(PointCloudData.merge, clouds, "merged", on_result=_on_result)

    def _filter_noise(self):
        entry = self.layer_manager.active_layer
        if not entry or not entry.is_point_cloud:
            return
        from app.processing.preprocessing import filter_noise
        self._run_processing(filter_noise, entry.layer,
                             on_result=lambda r: self.layer_manager.add_layer(r))

    def _decimate_cloud(self):
        entry = self.layer_manager.active_layer
        if not entry or not entry.is_point_cloud:
            return
        from PyQt6.QtWidgets import QInputDialog
        voxel, ok = QInputDialog.getDouble(
            self, tr("msg.decimate_title"), tr("msg.voxel_size"), 0.5, 0.01, 100.0, 2
        )
        if not ok:
            return
        from app.processing.preprocessing import decimate
        self._run_processing(decimate, entry.layer,
                             on_result=lambda r: self.layer_manager.add_layer(r),
                             voxel_size=voxel)

    def _remove_overlap(self):
        entry = self.layer_manager.active_layer
        if not entry or not entry.is_point_cloud:
            return
        from app.processing.preprocessing import handle_overlap
        self._run_processing(handle_overlap, entry.layer,
                             on_result=lambda r: self.layer_manager.add_layer(r),
                             strategy="remove")

    # ==================================================================
    # Tools — delegated to controllers
    # ==================================================================

    def _start_profile_tool(self):
        self._measurements.start_profile_tool()

    def _start_distance_tool(self):
        self._measurements.start_distance_tool()

    def _start_area_tool(self):
        self._measurements.start_area_tool()

    def _start_volume_tool(self):
        self._measurements.start_volume_tool()

    def _show_measurements_history(self):
        self._measurements.show_measurements_history()

    def _show_classification_history(self):
        self._measurements.show_classification_history()

    def _record_classification(self, algo: str, data: dict):
        self._measurements.record_classification(algo, data)

    def _show_figures_tool(self):
        self._figures.show_figures_tool()

    def _show_figures_history(self):
        self._figures.show_figures_history()

    def _start_annotations_tool(self):
        self._annotations.start_tool()

    # ==================================================================
    # Coordinate Picker
    # ==================================================================

    def _start_coordinate_picker(self):
        logger.info("Coordinate picker activated")
        from app.ui.viewport.coordinate_picker import CoordinatePickerDialog
        if self._coord_picker_dialog is None:
            self._coord_picker_dialog = CoordinatePickerDialog(self)
        self._coord_picker_dialog.show()
        self._coord_picker_dialog.raise_()
        self._coord_picker_dialog.activateWindow()

        def _on_pick(x, y, z):
            self._coord_picker_dialog.update_coords(x, y, z)
            self._update_status(tr("coord.status").format(x, y, z))

        self.viewport.enable_world_picking(_on_pick)
        self._update_status(tr("coord.instructions"))

    # ==================================================================
    # Help / info dialogs
    # ==================================================================

    def _show_flythrough_dialog(self):
        from app.ui.dialogs.flythrough_dialog import FlythroughDialog
        FlythroughDialog(self.layer_manager, self.viewport, self).exec()

    def _show_export_dialog(self):
        from app.ui.dialogs.export_dialog import ExportDialog
        ExportDialog(self.layer_manager, self).exec()

    def _export_layer(self, index: int):
        entry = self.layer_manager.get_entry(index)
        if not entry:
            return
        from app.ui.dialogs.export_dialog import ExportDialog
        ExportDialog(self.layer_manager, self, preset_layer=index).exec()

    def _show_tutorial(self):
        from app.ui.dialogs.tutorial_dialog import TutorialDialog
        TutorialDialog(self).exec()

    def _show_shortcuts(self):
        from app.ui.dialogs.tutorial_dialog import ShortcutsDialog
        ShortcutsDialog(self).exec()

    def _show_glossary(self):
        from app.ui.dialogs.tutorial_dialog import GlossaryDialog
        GlossaryDialog(self).exec()

    def _show_about(self):
        from app.ui.dialogs.about_dialog import AboutDialog
        AboutDialog(self).exec()

    # ==================================================================
    # Auth / profile / settings
    # ==================================================================

    def _show_profile(self):
        if not self._current_user:
            QMessageBox.information(self, tr("dialog.info"), tr("auth.my_account"))
            return
        self._show_user_panel()

    def _show_settings(self):
        from app.ui.dialogs.settings_dialog import SettingsDialog
        dlg = SettingsDialog(self.preferences, self)
        dlg.settings_changed.connect(self._on_settings_changed)
        dlg.exec()

    def _on_settings_changed(self, values: dict):
        bg = values.get("background_color")
        if bg and hasattr(self.viewport, "set_background_color"):
            self.viewport.set_background_color(bg)
        pt = values.get("default_point_size")
        if pt:
            self.viewport.set_point_size(pt)
        self.preferences.set("language", values.get("language", "es"))

    def showEvent(self, event):
        super().showEvent(event)
        if not self._login_shown:
            self._login_shown = True
            QTimer.singleShot(0, self._ensure_gated)

    def _ensure_gated(self):
        if not self._current_user:
            self._ensure_logged_in()
        if self._current_user:
            self._ensure_licensed()

    def _ensure_logged_in(self):
        from app.ui.dialogs.login_dialog import LoginDialog
        dlg = LoginDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            QApplication.quit()
            return
        self._current_user = dlg.user
        self._session_token = dlg.session_token
        if self._session_token and getattr(dlg, "persist_token", False):
            self.preferences.set("session_token", self._session_token)
        self._user_btn.setIcon(QIcon(self._make_avatar_pixmap(self._current_user.full_name)))
        self._user_btn.setIconSize(QSize(26, 26))
        self._user_btn.setVisible(True)

    def _ensure_licensed(self):
        from app.auth.license_service import verify_license, get_machine_id
        from app.ui.dialogs.license_dialog import LicenseDialog

        if not self._session_token:
            QMessageBox.critical(self, "ALAS", tr("license.error_processing_failed"))
            QApplication.quit()
            return

        machine_id = get_machine_id()
        if verify_license(self._session_token, machine_id):
            return

        dlg = LicenseDialog(self._session_token, self)
        if dlg.exec() != QDialog.DialogCode.Accepted or dlg.license is None:
            QApplication.quit()

    def _show_user_panel(self):
        if not self._current_user:
            return
        from app.ui.dialogs.user_panel import UserPanelDialog
        panel = UserPanelDialog(self._current_user, self._session_token, self)
        panel.logout_requested.connect(self._on_logout)
        panel.exec()

    def _on_logout(self):
        from app.auth.service import logout as auth_logout
        if self._session_token:
            auth_logout(self._session_token)
        self.preferences.set("session_token", None)
        import sys
        self.close()
        os.execv(sys.executable, [sys.executable] + sys.argv)

    def _change_language(self, lang: str):
        set_language(lang)
        self.preferences.set("language", lang)
        QMessageBox.information(
            self, tr("menu.language"),
            f"{tr('msg.language_change')}\n{tr('msg.language_change_restart')}"
        )

    # ==================================================================
    # State persistence
    # ==================================================================

    def _restore_state(self):
        geom = self.preferences.get("window_geometry")
        if geom:
            try:
                from PyQt6.QtCore import QByteArray
                self.restoreGeometry(QByteArray.fromHex(geom.encode()))
            except Exception:
                pass

    def closeEvent(self, event):
        self.preferences.set("window_geometry",
                              bytes(self.saveGeometry().toHex()).decode())
        self.preferences.save()
        self.viewport.closeEvent(event)
        super().closeEvent(event)
