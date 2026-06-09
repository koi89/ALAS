"""
ALAS — 3D Annotations Tool
Floating dialog to pin text labels at 3D coordinates in the viewport.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QListWidget, QListWidgetItem, QSizePolicy,
    QInputDialog, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal

from app.i18n import tr
from app.logger import get_logger

logger = get_logger("ui.annotations_tool")


@dataclass
class AnnotationEntry:
    id: int
    text: str
    x: float
    y: float
    z: float
    time: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))


class AnnotationsToolDialog(QDialog):
    """
    Floating tool for placing and managing 3D text annotations.

    Signals
    -------
    add_requested()          — user wants to pick a point for a new annotation
    remove_requested(int)    — user wants to remove annotation with given id
    clear_all_requested()    — remove all annotations
    """

    add_requested     = pyqtSignal()
    remove_requested  = pyqtSignal(int)
    clear_all_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Tool)
        self.setWindowTitle(tr("ann.title"))
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setMinimumWidth(340)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self._entries: dict[int, AnnotationEntry] = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        hint = QLabel(tr("ann.instructions"))
        hint.setWordWrap(True)
        hint.setObjectName("muted")
        hint.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(hint)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2a2a3d;")
        layout.addWidget(sep)

        grp = QGroupBox(tr("ann.annotations"))
        grp_layout = QVBoxLayout(grp)

        self._list = QListWidget()
        self._list.setMinimumHeight(140)
        self._list.currentRowChanged.connect(self._on_selection_changed)
        grp_layout.addWidget(self._list)

        self._empty_lbl = QLabel(tr("ann.empty"))
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setObjectName("muted")
        self._empty_lbl.setWordWrap(True)
        grp_layout.addWidget(self._empty_lbl)

        layout.addWidget(grp)

        btn_row = QHBoxLayout()

        self._btn_add = QPushButton(tr("ann.add"))
        self._btn_add.clicked.connect(self.add_requested)
        btn_row.addWidget(self._btn_add)

        self._btn_remove = QPushButton(tr("ann.remove"))
        self._btn_remove.setEnabled(False)
        self._btn_remove.clicked.connect(self._on_remove)
        btn_row.addWidget(self._btn_remove)

        self._btn_clear = QPushButton(tr("ann.clear_all"))
        self._btn_clear.setEnabled(False)
        self._btn_clear.clicked.connect(self.clear_all_requested)
        btn_row.addWidget(self._btn_clear)

        layout.addLayout(btn_row)

        btn_close = QPushButton(tr("dialog.close"))
        btn_close.clicked.connect(self.hide)
        layout.addWidget(btn_close)

        self._refresh_state()
        self.adjustSize()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_selection_changed(self, row: int):
        self._btn_remove.setEnabled(row >= 0)

    def _on_remove(self):
        item = self._list.currentItem()
        if item is None:
            return
        ann_id = item.data(Qt.ItemDataRole.UserRole)
        self.remove_requested.emit(ann_id)

    def _refresh_state(self):
        has = bool(self._entries)
        self._list.setVisible(has)
        self._empty_lbl.setVisible(not has)
        self._btn_clear.setEnabled(has)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_annotation(self, entry: AnnotationEntry):
        self._entries[entry.id] = entry
        item = QListWidgetItem(
            f"[{entry.id}] {entry.text}  "
            f"({entry.x:.1f}, {entry.y:.1f}, {entry.z:.1f})"
        )
        item.setData(Qt.ItemDataRole.UserRole, entry.id)
        self._list.addItem(item)
        self._refresh_state()

    def remove_annotation(self, ann_id: int):
        self._entries.pop(ann_id, None)
        for i in range(self._list.count()):
            if self._list.item(i).data(Qt.ItemDataRole.UserRole) == ann_id:
                self._list.takeItem(i)
                break
        self._refresh_state()

    def clear_all(self):
        self._entries.clear()
        self._list.clear()
        self._refresh_state()

    def ask_text(self) -> Optional[str]:
        """Prompt the user for the annotation label. Returns None if cancelled."""
        text, ok = QInputDialog.getText(
            self, tr("ann.title"), tr("ann.label")
        )
        return text.strip() if ok and text.strip() else None

    def closeEvent(self, event):
        event.ignore()
        self.hide()
