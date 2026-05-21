"""
ALAS — Menu bar builder.
Extracted from MainWindow to keep _setup_menu_bar isolated.
"""

from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence, QIcon
from PyQt6.QtCore import QSize

from app.i18n import tr


def build_menu_bar(window) -> None:
    """Populate *window*'s menu bar and attach the avatar corner widget."""
    menubar = window.menuBar()

    # --- File ---
    menu_file = menubar.addMenu(tr("menu.file"))

    act_open = QAction(tr("action.open"), window)
    act_open.setShortcut(QKeySequence("Ctrl+O"))
    act_open.triggered.connect(window._open_file)
    menu_file.addAction(act_open)

    act_open_multi = QAction(tr("action.open_multiple"), window)
    act_open_multi.setShortcut(QKeySequence("Ctrl+Shift+O"))
    act_open_multi.triggered.connect(window._open_multiple_files)
    menu_file.addAction(act_open_multi)

    menu_file.addSeparator()

    act_save = QAction(tr("action.save_project"), window)
    act_save.setShortcut(QKeySequence("Ctrl+S"))
    act_save.triggered.connect(window._save_project)
    menu_file.addAction(act_save)

    act_load = QAction(tr("action.load_project"), window)
    act_load.setShortcut(QKeySequence("Ctrl+Shift+S"))
    act_load.triggered.connect(window._load_project)
    menu_file.addAction(act_load)

    menu_file.addSeparator()

    act_export = QAction(tr("action.export"), window)
    act_export.setShortcut(QKeySequence("Ctrl+E"))
    act_export.triggered.connect(window._show_export_dialog)
    menu_file.addAction(act_export)

    act_flythrough = QAction(tr("action.flythrough"), window)
    act_flythrough.setShortcut(QKeySequence("Ctrl+Shift+F"))
    act_flythrough.triggered.connect(window._show_flythrough_dialog)
    menu_file.addAction(act_flythrough)

    menu_file.addSeparator()

    act_exit = QAction(tr("action.exit"), window)
    act_exit.setShortcut(QKeySequence("Ctrl+Q"))
    act_exit.triggered.connect(window.close)
    menu_file.addAction(act_exit)

    # --- View ---
    menu_view = menubar.addMenu(tr("menu.view"))

    act_reset = QAction(tr("action.reset_view"), window)
    act_reset.setShortcut(QKeySequence("R"))
    act_reset.triggered.connect(window.viewport.reset_camera)
    menu_view.addAction(act_reset)

    act_top = QAction(tr("action.top_view"), window)
    act_top.setShortcut(QKeySequence("T"))
    act_top.triggered.connect(window.viewport.set_view_top)
    menu_view.addAction(act_top)

    act_front = QAction(tr("action.front_view"), window)
    act_front.setShortcut(QKeySequence("F"))
    act_front.triggered.connect(window.viewport.set_view_front)
    menu_view.addAction(act_front)

    act_side = QAction(tr("action.side_view"), window)
    act_side.setShortcut(QKeySequence("S"))
    act_side.triggered.connect(window.viewport.set_view_side)
    menu_view.addAction(act_side)

    menu_view.addSeparator()

    menu_lang = menu_view.addMenu(tr("menu.language"))
    act_es = QAction(tr("lang.spanish"), window)
    act_es.triggered.connect(lambda: window._change_language("es"))
    menu_lang.addAction(act_es)
    act_en = QAction(tr("lang.english"), window)
    act_en.triggered.connect(lambda: window._change_language("en"))
    menu_lang.addAction(act_en)

    # --- Process ---
    menu_proc = menubar.addMenu(tr("menu.process"))

    act_classify = QAction(tr("action.classify"), window)
    act_classify.triggered.connect(window._show_classification_dialog)
    menu_proc.addAction(act_classify)

    act_class_history = QAction(tr("action.classification_history"), window)
    act_class_history.setShortcut(QKeySequence("Ctrl+Shift+H"))
    act_class_history.triggered.connect(window._show_classification_history)
    menu_proc.addAction(act_class_history)

    menu_proc.addSeparator()

    act_dem = QAction(tr("action.generate_dem"), window)
    act_dem.triggered.connect(window._show_dem_dialog)
    menu_proc.addAction(act_dem)

    menu_proc.addSeparator()

    act_merge = QAction(tr("action.merge_tiles"), window)
    act_merge.triggered.connect(window._merge_tiles)
    menu_proc.addAction(act_merge)

    act_noise = QAction(tr("action.filter_noise"), window)
    act_noise.triggered.connect(window._filter_noise)
    menu_proc.addAction(act_noise)

    act_reproj = QAction(tr("action.reproject"), window)
    act_reproj.triggered.connect(window._show_reproject_dialog)
    menu_proc.addAction(act_reproj)

    act_decimate = QAction(tr("action.decimate"), window)
    act_decimate.triggered.connect(window._decimate_cloud)
    menu_proc.addAction(act_decimate)

    act_overlap = QAction(tr("action.remove_overlap"), window)
    act_overlap.triggered.connect(window._remove_overlap)
    menu_proc.addAction(act_overlap)

    menu_proc.addSeparator()

    act_batch = QAction(tr("action.batch"), window)
    act_batch.setShortcut(QKeySequence("Ctrl+B"))
    act_batch.triggered.connect(window._show_batch_dialog)
    menu_proc.addAction(act_batch)

    # --- Analysis ---
    menu_analysis = menubar.addMenu(tr("menu.analysis"))

    act_geomorph = QAction(tr("action.geomorphology"), window)
    act_geomorph.triggered.connect(window._show_geomorphology_dialog)
    menu_analysis.addAction(act_geomorph)

    act_hydro = QAction(tr("action.hydrology"), window)
    act_hydro.triggered.connect(window._show_hydrology_dialog)
    menu_analysis.addAction(act_hydro)

    act_veg = QAction(tr("action.vegetation"), window)
    act_veg.triggered.connect(window._show_vegetation_dialog)
    menu_analysis.addAction(act_veg)

    act_multi = QAction(tr("action.multitemporal"), window)
    act_multi.triggered.connect(window._show_multitemporal_dialog)
    menu_analysis.addAction(act_multi)

    act_contours = QAction(tr("action.contours"), window)
    act_contours.triggered.connect(lambda: window._show_analysis_dialog("contours"))
    menu_analysis.addAction(act_contours)

    menu_analysis.addSeparator()

    act_reports = QAction(tr("action.my_reports"), window)
    act_reports.setShortcut(QKeySequence("Ctrl+Shift+R"))
    act_reports.triggered.connect(window._show_reports_dialog)
    menu_analysis.addAction(act_reports)

    # --- Tools ---
    menu_tools = menubar.addMenu(tr("menu.tools"))

    act_profile = QAction(tr("action.profile"), window)
    act_profile.triggered.connect(window._start_profile_tool)
    menu_tools.addAction(act_profile)

    act_dist = QAction(tr("action.distance"), window)
    act_dist.triggered.connect(window._start_distance_tool)
    menu_tools.addAction(act_dist)

    act_area = QAction(tr("action.area"), window)
    act_area.triggered.connect(window._start_area_tool)
    menu_tools.addAction(act_area)

    act_vol = QAction(tr("action.volume"), window)
    act_vol.triggered.connect(window._start_volume_tool)
    menu_tools.addAction(act_vol)

    act_figures = QAction(tr("action.figures"), window)
    act_figures.triggered.connect(window._show_figures_tool)
    menu_tools.addAction(act_figures)

    menu_tools.addSeparator()

    act_history = QAction(tr("action.measurements"), window)
    act_history.setShortcut(QKeySequence("Ctrl+H"))
    act_history.triggered.connect(window._show_measurements_history)
    menu_tools.addAction(act_history)

    act_fig_history = QAction(tr("action.figures_history"), window)
    act_fig_history.triggered.connect(window._show_figures_history)
    menu_tools.addAction(act_fig_history)

    menu_tools.addSeparator()

    act_coord = QAction(tr("action.coordinate_picker"), window)
    act_coord.triggered.connect(window._start_coordinate_picker)
    menu_tools.addAction(act_coord)

    act_ann = QAction(tr("action.annotations"), window)
    act_ann.triggered.connect(window._start_annotations_tool)
    menu_tools.addAction(act_ann)

    # --- Help ---
    menu_help = menubar.addMenu(tr("menu.help"))

    act_tutorial = QAction(tr("action.tutorial"), window)
    act_tutorial.setMenuRole(QAction.MenuRole.NoRole)
    act_tutorial.setShortcut(QKeySequence("F1"))
    act_tutorial.triggered.connect(window._show_tutorial)
    menu_help.addAction(act_tutorial)

    act_shortcuts = QAction(tr("action.shortcuts"), window)
    act_shortcuts.setMenuRole(QAction.MenuRole.NoRole)
    act_shortcuts.triggered.connect(window._show_shortcuts)
    menu_help.addAction(act_shortcuts)

    act_glossary = QAction(tr("action.glossary"), window)
    act_glossary.setMenuRole(QAction.MenuRole.NoRole)
    act_glossary.triggered.connect(window._show_glossary)
    menu_help.addAction(act_glossary)

    menu_help.addSeparator()

    act_about_help = QAction(tr("dialog.about_title"), window)
    act_about_help.setMenuRole(QAction.MenuRole.NoRole)
    act_about_help.triggered.connect(window._show_about)
    menu_help.addAction(act_about_help)

    # --- More ---
    menu_more = menubar.addMenu(tr("menu.more"))

    act_my_profile = QAction(tr("action.my_profile"), window)
    act_my_profile.setMenuRole(QAction.MenuRole.NoRole)
    act_my_profile.triggered.connect(window._show_profile)
    menu_more.addAction(act_my_profile)

    menu_more.addSeparator()

    act_settings = QAction(tr("action.settings"), window)
    act_settings.setMenuRole(QAction.MenuRole.NoRole)
    act_settings.setShortcut(QKeySequence("Ctrl+,"))
    act_settings.triggered.connect(window._show_settings)
    menu_more.addAction(act_settings)

    # Avatar button — far right of the menu bar
    window._user_btn = QPushButton()
    window._user_btn.setFixedSize(30, 30)
    window._user_btn.setObjectName("avatarBtn")
    window._user_btn.setToolTip(tr("auth.my_account"))
    window._user_btn.clicked.connect(window._show_user_panel)
    if window._current_user:
        window._user_btn.setIcon(QIcon(window._make_avatar_pixmap(window._current_user.full_name)))
        window._user_btn.setIconSize(QSize(26, 26))
    else:
        window._user_btn.setVisible(False)
    window.menuBar().setCornerWidget(window._user_btn, Qt.Corner.TopRightCorner)
