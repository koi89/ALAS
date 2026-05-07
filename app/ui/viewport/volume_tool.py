"""
ALAS — Volume Tool
Floating modal for the volume calculation tool.
Shows vertices in real time, allows defining reference Z and shows inline results.
"""

import numpy as np
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFormLayout, QGroupBox, QListWidget, QListWidgetItem,
    QSizePolicy, QFrame, QDoubleSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from app.i18n import tr
from app.logger import get_logger

logger = get_logger("ui.volume_tool")


class VolumeToolDialog(QDialog):
    """
    Floating modal for the volume tool.
    - Stays visible while the user clicks in the viewport.
    - Allows configuring the reference Z level.
    - Shows the vertex list in real time.
    - When 'Calculate' or Enter is pressed with >= 3 vertices, shows inline results.
    """

    calculate_requested = pyqtSignal()
    clear_requested     = pyqtSignal()
    clear_volume_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Tool)
        self.setWindowTitle(tr("vol.title"))
        self.setMinimumWidth(320)
        self.setMaximumWidth(400)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        self._vertices: list[tuple] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # --- Instructions ---
        lbl_hint = QLabel(tr("vol.instructions"))
        lbl_hint.setWordWrap(True)
        lbl_hint.setObjectName("muted")
        lbl_hint.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(lbl_hint)

        # --- Configuration ---
        grp_config = QGroupBox(tr("vol.config"))
        config_form = QFormLayout(grp_config)
        self._z_ref_spin = QDoubleSpinBox()
        self._z_ref_spin.setRange(-10000, 10000)
        self._z_ref_spin.setDecimals(2)
        self._z_ref_spin.setValue(0.0)
        self._z_ref_spin.setSuffix(" m")
        config_form.addRow(tr("vol.ref_level"), self._z_ref_spin)
        layout.addWidget(grp_config)

        # --- Vertex list ---
        grp_verts = QGroupBox(tr("vol.polygon_verts"))
        verts_layout = QVBoxLayout(grp_verts)
        verts_layout.setContentsMargins(6, 6, 6, 6)

        self._vertex_list = QListWidget()
        self._vertex_list.setMaximumHeight(160)
        self._vertex_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self._vertex_list.setStyleSheet(
            "QListWidget { background: #12121f; border: none; font-size: 11px; }"
            "QListWidget::item { padding: 2px 4px; color: #c0c0d0; }"
        )
        verts_layout.addWidget(self._vertex_list)

        self._count_label = QLabel(tr("area.zero_vertices"))
        self._count_label.setObjectName("muted")
        self._count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        verts_layout.addWidget(self._count_label)

        layout.addWidget(grp_verts)

        # --- Action buttons ---
        btn_row_1 = QHBoxLayout()

        self._btn_calc = QPushButton(tr("vol.calculate"))
        self._btn_calc.setObjectName("primary")
        self._btn_calc.setEnabled(False)
        self._btn_calc.clicked.connect(self._on_calculate_clicked)
        btn_row_1.addWidget(self._btn_calc)

        btn_undo = QPushButton(tr("vol.undo"))
        btn_undo.clicked.connect(self._on_undo)
        btn_row_1.addWidget(btn_undo)
        
        layout.addLayout(btn_row_1)

        btn_row_2 = QHBoxLayout()

        btn_clear_vol = QPushButton(tr("vol.clear_volume"))
        btn_clear_vol.setToolTip(tr("vol.clear_volume_tooltip"))
        btn_clear_vol.clicked.connect(self._on_clear_volume)
        btn_row_2.addWidget(btn_clear_vol)

        btn_clear = QPushButton(tr("vol.clear_all"))
        btn_clear.clicked.connect(self._on_clear)
        btn_row_2.addWidget(btn_clear)

        layout.addLayout(btn_row_2)

        # --- Separator ---
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2a2a3d;")
        layout.addWidget(sep)

        # --- Results panel ---
        self._results_group = QGroupBox(tr("vol.results"))
        results_form = QFormLayout(self._results_group)
        results_form.setSpacing(6)

        font_val = QFont()
        font_val.setBold(True)

        self._lbl_cut = QLabel("—")
        self._lbl_cut.setFont(font_val)
        self._lbl_fill = QLabel("—")
        self._lbl_fill.setFont(font_val)
        self._lbl_net = QLabel("—")
        self._lbl_net.setFont(font_val)
        self._lbl_area = QLabel("—")

        results_form.addRow(tr("vol.cut"), self._lbl_cut)
        results_form.addRow(tr("vol.fill"), self._lbl_fill)
        results_form.addRow(tr("vol.net"), self._lbl_net)
        results_form.addRow(tr("vol.base_area"), self._lbl_area)

        self._results_group.setVisible(False)
        layout.addWidget(self._results_group)

        self._lbl_source = QLabel("")
        self._lbl_source.setObjectName("muted")
        self._lbl_source.setWordWrap(True)
        self._lbl_source.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._lbl_source)

        # --- Close button ---
        btn_close = QPushButton(tr("dialog.close"))
        btn_close.clicked.connect(self._on_close)
        layout.addWidget(btn_close)

        layout.addStretch()
        self.adjustSize()

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------

    def add_vertex(self, x: float, y: float, z: float):
        self._vertices.append((x, y, z))
        n = len(self._vertices)

        item = QListWidgetItem(f"  {n:>2}.  X={x:.2f}   Y={y:.2f}   Z={z:.2f}")
        item.setForeground(QColor("#a855f7"))
        self._vertex_list.addItem(item)
        self._vertex_list.scrollToBottom()

        self._count_label.setText(f"{n} {tr('area.vertex_count').lower()}{'es' if n != 1 else ''}")
        self._btn_calc.setEnabled(n >= 3)

        if self._results_group.isVisible():
            self._results_group.setVisible(False)
            self._lbl_source.setText("")

    def get_vertices(self) -> list[tuple]:
        return list(self._vertices)
        
    def get_reference_z(self) -> float:
        return self._z_ref_spin.value()

    def show_results(self, cut_m3: float, fill_m3: float, net_m3: float, area_m2: float):
        self._lbl_cut.setText(f"{cut_m3:,.2f} {tr('vol.unit_m3')}")
        self._lbl_fill.setText(f"{fill_m3:,.2f} {tr('vol.unit_m3')}")
        self._lbl_net.setText(f"{net_m3:,.2f} {tr('vol.unit_m3')}")
        self._lbl_area.setText(f"{area_m2:,.2f} {tr('dist.unit_m')}")

        self._lbl_source.setText(tr("vol.source"))
        self._results_group.setVisible(True)
        self.adjustSize()
        
    def show_error(self, message: str):
        self._results_group.setVisible(False)
        self._lbl_source.setText(message)
        self._lbl_source.setStyleSheet("color: #ef4444;")
        self.adjustSize()

    def reset(self):
        self._vertices.clear()
        self._vertex_list.clear()
        self._count_label.setText(tr("area.zero_vertices"))
        self._btn_calc.setEnabled(False)
        self._results_group.setVisible(False)
        self._lbl_source.setText("")
        self._lbl_source.setStyleSheet("")
        self.adjustSize()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_calculate_clicked(self):
        if len(self._vertices) >= 3:
            self.calculate_requested.emit()

    def _on_undo(self):
        if not self._vertices:
            return
        self._vertices.pop()
        self._vertex_list.takeItem(self._vertex_list.count() - 1)
        n = len(self._vertices)
        self._count_label.setText(f"{n} {tr('area.vertex_count').lower()}{'es' if n != 1 else ''}")
        self._btn_calc.setEnabled(n >= 3)
        self.clear_requested.emit()

    def _on_clear_volume(self):
        self.clear_volume_requested.emit()

    def _on_clear(self):
        self.reset()
        self.clear_requested.emit()

    def _on_close(self):
        self.hide()
        self.reset()
        self.clear_requested.emit()

    def closeEvent(self, event):
        self._on_close()
        event.ignore()
        self.hide()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self._btn_calc.isEnabled():
                self._on_calculate_clicked()
        elif event.key() == Qt.Key.Key_Escape:
            self._on_close()
        else:
            super().keyPressEvent(event)
