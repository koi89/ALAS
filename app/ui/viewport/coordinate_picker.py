"""
ALAS — Coordinate Picker Tool
Floating dialog showing X/Y/Z of the last viewport click.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QGroupBox, QLabel,
    QPushButton, QSizePolicy
)
from PyQt6.QtCore import Qt

from app.i18n import tr
from app.logger import get_logger

logger = get_logger("ui.coordinate_picker")


class CoordinatePickerDialog(QDialog):
    """
    Small floating readout that shows the 3D coordinates of the last clicked
    point in the viewport.  The main window drives picking; this dialog only
    displays results.
    """

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Tool)
        self.setWindowTitle(tr("coord.title"))
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setMinimumWidth(260)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        hint = QLabel(tr("coord.instructions"))
        hint.setWordWrap(True)
        hint.setObjectName("muted")
        layout.addWidget(hint)

        grp = QGroupBox(tr("coord.coordinates"))
        form = QFormLayout(grp)
        form.setSpacing(6)

        self._lbl_x = QLabel("—")
        self._lbl_y = QLabel("—")
        self._lbl_z = QLabel("—")
        layout.addWidget(grp)

        form.addRow("X:", self._lbl_x)
        form.addRow("Y:", self._lbl_y)
        form.addRow("Z:", self._lbl_z)

        btn_close = QPushButton(tr("dialog.close"))
        btn_close.clicked.connect(self.hide)
        layout.addWidget(btn_close)

        self.adjustSize()

    def update_coords(self, x: float, y: float, z: float):
        self._lbl_x.setText(f"{x:,.3f}")
        self._lbl_y.setText(f"{y:,.3f}")
        self._lbl_z.setText(f"{z:,.3f}")
        logger.debug(f"Coordinate pick: X={x:.3f} Y={y:.3f} Z={z:.3f}")

    def closeEvent(self, event):
        event.ignore()
        self.hide()
