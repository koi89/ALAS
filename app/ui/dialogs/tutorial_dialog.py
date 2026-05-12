"""
ALAS — Tutorial Dialog
Interactive help viewer that renders TUTORIAL.md with a navigable
section sidebar and full-text search.
"""

import re

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QListWidget, QListWidgetItem, QLineEdit,
    QTextBrowser, QLabel, QFrame, QWidget
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut, QTextCursor, QTextCharFormat, QColor, QTextDocument

from app.config import ROOT_DIR
from app.i18n import tr


def _read_tutorial() -> str:
    path = ROOT_DIR / "TUTORIAL.md"
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return "# Tutorial\n\nNo se encontró el archivo TUTORIAL.md."


def _extract_sections(md: str) -> list[tuple[str, str]]:
    """Return list of (display_label, anchor_text) for every heading."""
    sections = []
    for line in md.splitlines():
        m = re.match(r"^(#{1,3})\s+(.+)", line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            # strip markdown link syntax if present
            title = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", title)
            indent = "  " * (level - 1)
            sections.append((f"{indent}{title}", title))
    return sections


class TutorialDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("dialog.tutorial_title"))
        self.setMinimumSize(900, 640)
        self.resize(1020, 720)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint
        )
        self._md = _read_tutorial()
        self._sections = _extract_sections(self._md)
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._do_search)
        self._build_ui()
        self._populate_sections()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top bar ─────────────────────────────────────────────────────
        top_bar = QWidget()
        top_bar.setObjectName("tutorialTopBar")
        top_bar.setFixedHeight(48)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(16, 8, 16, 8)
        top_layout.setSpacing(12)

        lbl = QLabel(tr("dialog.tutorial_title"))
        lbl.setObjectName("tutorialHeadingLabel")
        top_layout.addWidget(lbl)
        top_layout.addStretch()

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText(tr("dialog.tutorial_search"))
        self._search_box.setFixedWidth(240)
        self._search_box.setObjectName("tutorialSearchBox")
        self._search_box.textChanged.connect(self._on_search_changed)
        self._search_box.returnPressed.connect(self._jump_next_match)
        top_layout.addWidget(self._search_box)

        self._match_label = QLabel("")
        self._match_label.setObjectName("tutorialMatchLabel")
        self._match_label.setFixedWidth(90)
        top_layout.addWidget(self._match_label)

        prev_btn = QPushButton("▲")
        prev_btn.setToolTip(tr("dialog.tutorial_prev"))
        prev_btn.setFixedSize(28, 28)
        prev_btn.setObjectName("tutorialNavBtn")
        prev_btn.clicked.connect(self._jump_prev_match)
        top_layout.addWidget(prev_btn)

        next_btn = QPushButton("▼")
        next_btn.setToolTip(tr("dialog.tutorial_next"))
        next_btn.setFixedSize(28, 28)
        next_btn.setObjectName("tutorialNavBtn")
        next_btn.clicked.connect(self._jump_next_match)
        top_layout.addWidget(next_btn)

        root.addWidget(top_bar)

        # ── Divider ─────────────────────────────────────────────────────
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("tutorialDivider")
        root.addWidget(line)

        # ── Splitter (sidebar + content) ────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setObjectName("tutorialSplitter")

        # Sidebar
        self._section_list = QListWidget()
        self._section_list.setObjectName("tutorialSidebar")
        self._section_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._section_list.currentRowChanged.connect(self._on_section_selected)
        splitter.addWidget(self._section_list)

        # Content browser
        self._browser = QTextBrowser()
        self._browser.setObjectName("tutorialBrowser")
        self._browser.setOpenExternalLinks(True)
        self._browser.setMarkdown(self._md)
        splitter.addWidget(self._browser)

        splitter.setSizes([220, 780])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, 1)

        # ── Bottom bar ──────────────────────────────────────────────────
        bottom_bar = QWidget()
        bottom_bar.setObjectName("tutorialBottomBar")
        bottom_bar.setFixedHeight(48)
        bot_layout = QHBoxLayout(bottom_bar)
        bot_layout.setContentsMargins(16, 8, 16, 8)
        bot_layout.addStretch()

        close_btn = QPushButton(tr("dialog.close"))
        close_btn.setFixedWidth(100)
        close_btn.setDefault(True)
        close_btn.clicked.connect(self.accept)
        bot_layout.addWidget(close_btn)

        root.addWidget(bottom_bar)

        # Esc closes
        QShortcut(QKeySequence("Escape"), self, self.accept)
        # F3 jumps to next match
        QShortcut(QKeySequence("F3"), self, self._jump_next_match)
        QShortcut(QKeySequence("Shift+F3"), self, self._jump_prev_match)

        self._apply_styles()

    def _apply_styles(self):
        self.setStyleSheet("""
            #tutorialTopBar {
                background-color: #050505;
                border-bottom: 1px solid #222222;
            }
            #tutorialHeadingLabel {
                font-size: 15px;
                font-weight: 700;
                color: #ffffff;
            }
            #tutorialSearchBox {
                background-color: #050505;
                border: 1px solid #333333;
                border-radius: 6px;
                color: #e0e0e8;
                padding: 4px 10px;
                font-size: 13px;
            }
            #tutorialSearchBox:focus {
                border-color: #555555;
                background-color: #080808;
            }
            #tutorialMatchLabel {
                color: #888898;
                font-size: 12px;
            }
            #tutorialNavBtn {
                background-color: #222222;
                border: 1px solid #333333;
                border-radius: 6px;
                color: #e0e0e8;
                font-size: 11px;
                padding: 2px 6px;
                min-height: 0;
            }
            #tutorialNavBtn:hover {
                background-color: #2a2a2a;
                border-color: #555555;
            }
            #tutorialNavBtn:pressed {
                background-color: #555555;
                color: #ffffff;
            }
            #tutorialDivider {
                color: #222222;
                max-height: 1px;
            }
            #tutorialSidebar {
                background-color: #050505;
                border: none;
                border-right: 1px solid #222222;
                color: #e0e0e8;
                font-size: 13px;
                padding: 4px 0;
            }
            #tutorialSidebar::item {
                padding: 5px 12px;
                border-radius: 0;
            }
            #tutorialSidebar::item:selected {
                background-color: #333333;
                color: #ffffff;
            }
            #tutorialSidebar::item:hover:!selected {
                background-color: #1a1a1a;
            }
            #tutorialBrowser {
                background-color: #000000;
                color: #c0c0d0;
                border: none;
                padding: 24px 32px;
                font-size: 14px;
            }
            #tutorialBottomBar {
                background-color: #050505;
                border-top: 1px solid #222222;
            }
        """)

    # ------------------------------------------------------------------
    # Sections
    # ------------------------------------------------------------------

    def _populate_sections(self):
        for label, _ in self._sections:
            item = QListWidgetItem(label)
            # top-level headings get a slightly different style via font weight
            stripped = label.lstrip()
            depth = len(label) - len(stripped)
            if depth == 0:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            self._section_list.addItem(item)

    def _on_section_selected(self, row: int):
        if row < 0 or row >= len(self._sections):
            return
        _, heading_text = self._sections[row]
        # Find the heading in the document and scroll to it
        doc = self._browser.document()
        cursor = doc.find(heading_text)
        if not cursor.isNull():
            self._browser.setTextCursor(cursor)
            self._browser.ensureCursorVisible()

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _on_search_changed(self, text: str):
        self._search_timer.start(250)

    def _do_search(self):
        query = self._search_box.text().strip()
        self._clear_highlights()
        if not query:
            self._match_label.setText("")
            return

        self._matches: list[QTextCursor] = []
        self._match_index = -1

        doc = self._browser.document()
        cursor = QTextCursor(doc)
        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#7a6a00"))
        fmt.setForeground(QColor("#ffffff"))

        while True:
            cursor = doc.find(query, cursor, QTextDocument.FindFlag(0))
            if cursor.isNull():
                break
            cursor.mergeCharFormat(fmt)
            self._matches.append(QTextCursor(cursor))

        count = len(self._matches)
        if count:
            self._match_index = 0
            self._scroll_to_match(0)
            self._match_label.setText(f"1 / {count}")
        else:
            self._match_label.setText(tr("dialog.tutorial_no_match"))

    def _clear_highlights(self):
        cursor = QTextCursor(self._browser.document())
        cursor.select(QTextCursor.SelectionType.Document)
        fmt = QTextCharFormat()
        fmt.setBackground(QColor("transparent"))
        fmt.setForeground(QColor("#c0c0d0"))
        cursor.mergeCharFormat(fmt)
        self._matches = []
        self._match_index = -1

    def _scroll_to_match(self, index: int):
        if not self._matches:
            return
        cursor = self._matches[index]
        # highlight current match differently
        active_fmt = QTextCharFormat()
        active_fmt.setBackground(QColor("#888800"))
        active_fmt.setForeground(QColor("#ffffff"))
        prev_fmt = QTextCharFormat()
        prev_fmt.setBackground(QColor("#7a6a00"))
        prev_fmt.setForeground(QColor("#ffffff"))

        for i, c in enumerate(self._matches):
            c.mergeCharFormat(active_fmt if i == index else prev_fmt)

        self._browser.setTextCursor(cursor)
        self._browser.ensureCursorVisible()

    def _jump_next_match(self):
        if not getattr(self, "_matches", []):
            return
        self._match_index = (self._match_index + 1) % len(self._matches)
        self._scroll_to_match(self._match_index)
        self._match_label.setText(f"{self._match_index + 1} / {len(self._matches)}")

    def _jump_prev_match(self):
        if not getattr(self, "_matches", []):
            return
        self._match_index = (self._match_index - 1) % len(self._matches)
        self._scroll_to_match(self._match_index)
        self._match_label.setText(f"{self._match_index + 1} / {len(self._matches)}")
