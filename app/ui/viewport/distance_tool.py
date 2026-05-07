"""
ALAS — Distance Tool
Floating modal for the distance measurement tool.
Shows points A and B in real time and inline results.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFormLayout, QGroupBox, QListWidget, QListWidgetItem,
    QSizePolicy, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from app.i18n import tr
from app.logger import get_logger

logger = get_logger("ui.distance_tool")


class DistanceToolDialog(QDialog):
    """
    Floating modal for the distance tool.
    - Stays visible while the user clicks in the viewport.
    - Shows points A and B in real time.
    - When point B is selected, shows inline results.
    - Emits calculate_requested when two points are available.
    - Emits clear_requested when the user cancels/clears.
    """

    calculate_requested = pyqtSignal()   # The main_window executes the calculation
    clear_requested     = pyqtSignal()   # The main_window clears the viewport

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Tool)  # Tool = floating, non-blocking
        self.setWindowTitle(tr("action.distance"))
        self.setMinimumWidth(320)
        self.setMaximumWidth(400)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        self._points: list[tuple] = []
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # --- Instructions ---
        lbl_hint = QLabel(tr("dist.instructions"))
        lbl_hint.setWordWrap(True)
        lbl_hint.setObjectName("muted")
        lbl_hint.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(lbl_hint)

        # --- Point list ---
        grp_points = QGroupBox(tr("dist.points"))
        points_layout = QVBoxLayout(grp_points)
        points_layout.setContentsMargins(6, 6, 6, 6)

        self._point_list = QListWidget()
        self._point_list.setMaximumHeight(80)
        self._point_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self._point_list.setStyleSheet(
            "QListWidget { background: #12121f; border: none; font-size: 11px; }"
            "QListWidget::item { padding: 2px 4px; color: #c0c0d0; }"
        )
        points_layout.addWidget(self._point_list)

        layout.addWidget(grp_points)

        # --- Separator ---
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2a2a3d;")
        layout.addWidget(sep)

        # --- Results panel (hidden until calculation) ---
        self._results_group = QGroupBox(tr("dist.results"))
        results_form = QFormLayout(self._results_group)
        results_form.setSpacing(6)

        font_val = QFont()
        font_val.setBold(True)

        self._lbl_dist_3d = QLabel("—")
        self._lbl_dist_3d.setFont(font_val)
        self._lbl_dist_2d = QLabel("—")
        self._lbl_dist_2d.setFont(font_val)
        self._lbl_dz = QLabel("—")
        self._lbl_dz.setFont(font_val)
        self._lbl_slope = QLabel("—")
        self._lbl_slope.setFont(font_val)

        results_form.addRow(tr("dist.3d_distance"), self._lbl_dist_3d)
        results_form.addRow(tr("dist.2d_distance"), self._lbl_dist_2d)
        results_form.addRow(tr("dist.z_diff"), self._lbl_dz)
        results_form.addRow(tr("dist.slope"), self._lbl_slope)

        self._results_group.setVisible(False)
        layout.addWidget(self._results_group)

        # --- Action buttons ---
        btn_row = QHBoxLayout()

        btn_clear = QPushButton(tr("dist.clear"))
        btn_clear.clicked.connect(self._on_clear)
        btn_row.addWidget(btn_clear)

        layout.addLayout(btn_row)

        # --- Close button ---
        btn_close = QPushButton(tr("dialog.close"))
        btn_close.clicked.connect(self._on_close)
        layout.addWidget(btn_close)

        layout.addStretch()
        self.adjustSize()

    # ------------------------------------------------------------------
    # Public API — called from main_window
    # ------------------------------------------------------------------

    def add_point(self, x: float, y: float, z: float, label: str):
        """Add a point (A or B) and update the UI."""
        if len(self._points) >= 2:
            return  # Only two points
        self._points.append((x, y, z))

        item = QListWidgetItem(f"{label}: X={x:.2f}   Y={y:.2f}   Z={z:.2f}")
        item.setForeground(QColor("#a855f7"))
        self._point_list.addItem(item)

        if len(self._points) == 2:
            self.calculate_requested.emit()

        logger.debug(f"Point {label} added: ({x:.2f}, {y:.2f}, {z:.2f})")

    def show_results(self, dist_3d: float, dist_2d: float, dz: float, slope_deg: float):
        """Show the results in the inline panel."""
        self._lbl_dist_3d.setText(f"{dist_3d:.3f} {tr('dist.unit_m')}")
        self._lbl_dist_2d.setText(f"{dist_2d:.3f} {tr('dist.unit_m')}")
        self._lbl_dz.setText(f"{dz:.3f} {tr('dist.unit_m')}")
        self._lbl_slope.setText(f"{slope_deg:.1f} {tr('dist.unit_deg')}")

        self._results_group.setVisible(True)
        self.adjustSize()

    def get_points(self) -> list[tuple]:
        """Return the point list [(x, y, z), ...]."""
        return list(self._points)

    def reset(self):
        """Clear points and results."""
        self._points.clear()
        self._point_list.clear()
        self._results_group.setVisible(False)
        self.adjustSize()

    # ------------------------------------------------------------------
    # Internal slots
    # ------------------------------------------------------------------

    def _on_clear(self):
        self.reset()
        self.clear_requested.emit()

    def _on_close(self):
        self.hide()
        self.reset()
        self.clear_requested.emit()

    # Prevent closing the window from destroying the dialog
    def closeEvent(self, event):
        self._on_close()
        event.ignore()   # Do not destroy, only hide
        self.hide()

    # Enter or Escape
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._on_close()
        else:
            super().keyPressEvent(event)