"""
ALAS — License Activation Dialog
Modal gate: shown when the logged-in user has no active license activation
for this machine. The user must enter a valid license key to continue.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QHBoxLayout, QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.i18n import tr
from app.logger import get_logger
from app.auth.license_service import (
    LicenseStatus, activate_license, get_machine_id,
)

logger = get_logger("ui.license_dialog")


class LicenseDialog(QDialog):
    """Modal license gate. self.license is set on accept()."""

    def __init__(self, token: str, parent=None):
        super().__init__(parent)
        self.token = token
        self.machine_id = get_machine_id()
        self.license: LicenseStatus | None = None

        self.setWindowTitle("ALAS — License")
        self.setFixedSize(440, 360)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)

        title = QLabel(tr("license.title"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setObjectName("heading")
        root.addWidget(title)

        root.addSpacing(8)
        sub = QLabel(tr("license.subtitle"))
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setObjectName("muted")
        sub.setWordWrap(True)
        root.addWidget(sub)

        root.addSpacing(28)

        self._key_field = QLineEdit()
        self._key_field.setPlaceholderText("ALAS-XXXX-XXXX-XXXX-XXXX")
        self._key_field.setFixedHeight(44)
        self._key_field.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f = QFont("Menlo")
        f.setStyleHint(QFont.StyleHint.Monospace)
        self._key_field.setFont(f)
        root.addWidget(self._key_field)

        root.addSpacing(16)
        self._error = QLabel("")
        self._error.setObjectName("errorLabel")
        self._error.setWordWrap(True)
        self._error.setVisible(False)
        root.addWidget(self._error)

        root.addStretch()

        row = QHBoxLayout()
        self._quit_btn = QPushButton(tr("license.quit"))
        self._quit_btn.setFixedHeight(44)
        self._quit_btn.clicked.connect(self._on_quit)
        row.addWidget(self._quit_btn)

        self._activate_btn = QPushButton(tr("license.activate"))
        self._activate_btn.setFixedHeight(44)
        self._activate_btn.setObjectName("primary")
        self._activate_btn.setDefault(True)
        self._activate_btn.clicked.connect(self._do_activate)
        row.addWidget(self._activate_btn)
        root.addLayout(row)

    def _show_error(self, text: str):
        self._error.setText(text)
        self._error.setVisible(True)

    def _set_enabled(self, enabled: bool):
        self._key_field.setEnabled(enabled)
        self._activate_btn.setEnabled(enabled)
        self._quit_btn.setEnabled(enabled)

    def _do_activate(self):
        self._error.setVisible(False)
        key = self._key_field.text().strip()
        if not key:
            self._show_error(tr("license.error_empty_key"))
            return

        self._set_enabled(False)
        QApplication.processEvents()

        result = activate_license(self.token, key, self.machine_id)
        self._set_enabled(True)

        if isinstance(result, str):
            self._show_error(tr(result))
            return

        self.license = result
        self.accept()

    def _on_quit(self):
        self.reject()

    def closeEvent(self, event):
        if self.license is None:
            self.reject()
        super().closeEvent(event)
