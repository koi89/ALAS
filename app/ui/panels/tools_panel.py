"""
ALAS — Tools Panel
Active tools panel: point size, colorization, view configuration.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QFormLayout, QSlider, QComboBox,
    QPushButton, QLabel, QHBoxLayout
)
from PyQt6.QtCore import Qt, pyqtSignal

from app.config import (
    COLORIZE_MODES, COLORIZE_HEIGHT, COLORIZE_INTENSITY,
    COLORIZE_CLASSIFICATION, COLORIZE_RETURN_NUMBER,
    COLORIZE_RGB, COLORIZE_SINGLE, DEFAULT_POINT_SIZE
)
from app.i18n import tr


class ToolsPanel(QWidget):
    """Visualization tools panel."""

    point_size_changed = pyqtSignal(float)
    colorize_mode_changed = pyqtSignal(str)
    view_reset_requested = pyqtSignal()
    view_top_requested = pyqtSignal()
    view_front_requested = pyqtSignal()
    view_side_requested = pyqtSignal()

    COLORIZE_LABELS = {
        COLORIZE_HEIGHT: tr("colorize.height_label"),
        COLORIZE_INTENSITY: tr("colorize.intensity_label"),
        COLORIZE_CLASSIFICATION: tr("colorize.classification_label"),
        COLORIZE_RETURN_NUMBER: tr("colorize.return_label"),
        COLORIZE_RGB: tr("colorize.rgb_label"),
        COLORIZE_SINGLE: tr("colorize.solid_label"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- Visualization ---
        grp_vis = QGroupBox(tr("tool.visualization"))
        form_vis = QFormLayout(grp_vis)

        # Point size slider
        self._point_size_label = QLabel(f"{DEFAULT_POINT_SIZE:.0f}")
        self._point_size_slider = QSlider(Qt.Orientation.Horizontal)
        self._point_size_slider.setRange(1, 20)
        self._point_size_slider.setValue(int(DEFAULT_POINT_SIZE))
        self._point_size_slider.valueChanged.connect(self._on_point_size)

        ps_row = QHBoxLayout()
        ps_row.addWidget(self._point_size_slider)
        ps_row.addWidget(self._point_size_label)
        form_vis.addRow(tr("tool.point_size"), ps_row)

        # Colorize mode
        self._colorize_combo = QComboBox()
        for mode in COLORIZE_MODES:
            self._colorize_combo.addItem(self.COLORIZE_LABELS.get(mode, mode), mode)
        self._colorize_combo.currentIndexChanged.connect(self._on_colorize_changed)
        form_vis.addRow(tr("tool.colorize_by"), self._colorize_combo)

        layout.addWidget(grp_vis)

        # --- Camera ---
        grp_cam = QGroupBox(tr("tool.camera"))
        cam_layout = QVBoxLayout(grp_cam)

        btn_row1 = QHBoxLayout()
        btn_reset = QPushButton(tr("tool.reset"))
        btn_reset.clicked.connect(self.view_reset_requested.emit)
        btn_top = QPushButton(tr("tool.top"))
        btn_top.clicked.connect(self.view_top_requested.emit)
        btn_row1.addWidget(btn_reset)
        btn_row1.addWidget(btn_top)
        cam_layout.addLayout(btn_row1)

        btn_row2 = QHBoxLayout()
        btn_front = QPushButton(tr("tool.front"))
        btn_front.clicked.connect(self.view_front_requested.emit)
        btn_side = QPushButton(tr("tool.side"))
        btn_side.clicked.connect(self.view_side_requested.emit)
        btn_row2.addWidget(btn_front)
        btn_row2.addWidget(btn_side)
        cam_layout.addLayout(btn_row2)

        layout.addWidget(grp_cam)
        layout.addStretch()

    def _on_point_size(self, value: int):
        self._point_size_label.setText(str(value))
        self.point_size_changed.emit(float(value))

    def _on_colorize_changed(self, index: int):
        mode = self._colorize_combo.itemData(index)
        if mode:
            self.colorize_mode_changed.emit(mode)
