"""
ALAS — Area Tool
Floating modal for the area measurement tool.
Shows vertices in real time and inline results.
"""

import numpy as np
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFormLayout, QGroupBox, QListWidget, QListWidgetItem,
    QSizePolicy, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from app.i18n import tr
from app.logger import get_logger

logger = get_logger("ui.area_tool")


class AreaToolDialog(QDialog):
    """
    Floating modal for the area tool.
    - Stays visible while the user clicks in the viewport.
    - Shows the vertex list in real time.
    - When 'Calculate' or Enter is pressed with ≥3 vertices, shows inline results.
    - Emits calculate_requested when the user wants to calculate.
    - Emits clear_requested when the user cancels/clears.
    """

    calculate_requested = pyqtSignal()   # The main_window executes the calculation
    clear_requested     = pyqtSignal()   # The main_window clears the viewport
    undo_requested      = pyqtSignal(list)  # The main_window redraws with remaining vertices

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Tool)  # Tool = floating, non-blocking
        self.setWindowTitle(tr("action.area"))
        self.setMinimumWidth(320)
        self.setMaximumWidth(400)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        self._vertices: list[tuple] = []
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # --- Instructions ---
        lbl_hint = QLabel(tr("area.instructions"))
        lbl_hint.setWordWrap(True)
        lbl_hint.setObjectName("muted")
        lbl_hint.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(lbl_hint)

        # --- Vertex list ---
        grp_verts = QGroupBox(tr("area.vertices"))
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

        # Counter
        self._count_label = QLabel(tr("area.zero_vertices"))
        self._count_label.setObjectName("muted")
        self._count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        verts_layout.addWidget(self._count_label)

        layout.addWidget(grp_verts)

        # --- Action buttons ---
        btn_row = QHBoxLayout()

        self._btn_calc = QPushButton(tr("area.calculate"))
        self._btn_calc.setObjectName("primary")
        self._btn_calc.setEnabled(False)
        self._btn_calc.clicked.connect(self._on_calculate_clicked)
        btn_row.addWidget(self._btn_calc)

        btn_undo = QPushButton(tr("area.undo"))
        btn_undo.clicked.connect(self._on_undo)
        btn_row.addWidget(btn_undo)

        btn_clear = QPushButton(tr("area.clear"))
        btn_clear.clicked.connect(self._on_clear)
        btn_row.addWidget(btn_clear)

        layout.addLayout(btn_row)

        # --- Separator ---
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2a2a3d;")
        layout.addWidget(sep)

        # --- Results panel (hidden until calculation) ---
        self._results_group = QGroupBox(tr("area.results"))
        results_form = QFormLayout(self._results_group)
        results_form.setSpacing(6)

        font_val = QFont()
        font_val.setBold(True)

        self._lbl_plan   = QLabel("—")
        self._lbl_plan.setFont(font_val)
        self._lbl_plan_ha = QLabel("—")
        self._lbl_plan_ha.setFont(font_val)
        self._lbl_surf   = QLabel("—")
        self._lbl_surf.setFont(font_val)
        self._lbl_perim  = QLabel("—")
        self._lbl_perim.setFont(font_val)
        self._lbl_verts  = QLabel("—")

        results_form.addRow(tr("area.planimetric"),  self._lbl_plan)
        results_form.addRow("",                    self._lbl_plan_ha)
        results_form.addRow(tr("area.surface"),   self._lbl_surf)
        results_form.addRow(tr("area.perimeter"),       self._lbl_perim)
        results_form.addRow(tr("area.vertex_count"),           self._lbl_verts)

        self._results_group.setVisible(False)
        layout.addWidget(self._results_group)

        # --- Data source notice ---
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
    # Public API — called from main_window
    # ------------------------------------------------------------------

    def add_vertex(self, x: float, y: float, z: float):
        """Add a vertex and update the UI."""
        self._vertices.append((x, y, z))
        n = len(self._vertices)

        item = QListWidgetItem(f"  {n:>2}.  X={x:.2f}   Y={y:.2f}   Z={z:.2f}")
        item.setForeground(QColor("#a855f7"))
        self._vertex_list.addItem(item)
        self._vertex_list.scrollToBottom()

        self._count_label.setText(f"{n} {tr('area.vertex_count').lower()}{'es' if n != 1 else ''}")
        self._btn_calc.setEnabled(n >= 3)

        # Reset results if more vertices are added after calculation
        if self._results_group.isVisible():
            self._results_group.setVisible(False)
            self._lbl_source.setText("")

        logger.debug(f"Vertex {n} added: ({x:.2f}, {y:.2f}, {z:.2f})")

    def get_vertices(self) -> list[tuple]:
        """Return the vertex list [(x, y, z), ...]."""
        return list(self._vertices)

    def show_results(self, plan_m2: float, surf_m2: float,
                     perimeter_m: float, used_raster: bool):
        """Show the results in the inline panel."""
        self._lbl_plan.setText(f"{plan_m2:,.2f} {tr('area.unit_m2')}")
        self._lbl_plan_ha.setText(f"({plan_m2 / 10000:,.4f} {tr('area.unit_ha')})")
        self._lbl_surf.setText(
            f"{surf_m2:,.2f} {tr('area.unit_m2')}" if used_raster else tr("area.without_dem")
        )
        self._lbl_perim.setText(f"{perimeter_m:,.2f} {tr('dist.unit_m')}")
        self._lbl_verts.setText(str(len(self._vertices)))

        if used_raster:
            self._lbl_source.setText(tr("area.source_dem"))
        else:
            self._lbl_source.setText(tr("area.source_no_dem"))

        self._results_group.setVisible(True)
        self.adjustSize()

    def reset(self):
        """Clear vertices and results."""
        self._vertices.clear()
        self._vertex_list.clear()
        self._count_label.setText(tr("area.zero_vertices"))
        self._btn_calc.setEnabled(False)
        self._results_group.setVisible(False)
        self._lbl_source.setText("")
        self._lbl_plan.setText("—")
        self._lbl_plan_ha.setText("—")
        self._lbl_surf.setText("—")
        self._lbl_perim.setText("—")
        self._lbl_verts.setText("—")
        self.adjustSize()

    # ------------------------------------------------------------------
    # Internal slots
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
        self.undo_requested.emit(list(self._vertices))

    def _on_clear(self):
        self.reset()
        self.clear_requested.emit()

    def _on_close(self):
        self.hide()
        self.reset()
        self.clear_requested.emit()

    # Prevent closing the window from destroying the dialog
    def closeEvent(self, event):
        event.ignore()   # Do not destroy, only hide
        self._on_close()

    # Enter when the focus is on the dialog
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self._btn_calc.isEnabled():
                self._on_calculate_clicked()
        elif event.key() == Qt.Key.Key_Escape:
            self._on_close()
        else:
            super().keyPressEvent(event)
