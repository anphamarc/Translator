"""Cua so chinh."""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QMainWindow, QTabWidget, QVBoxLayout, QWidget

from translator_app import __version__
from translator_app.engine import get_engine

from .common import STYLE
from .tabs import FileTab, ImageTab, LanguageBar, ModelTab, TextTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Translator {__version__} — Dịch Anh · Hàn · Việt (offline)")
        self.resize(1180, 760)

        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        lay = QVBoxLayout(central)
        lay.setContentsMargins(20, 14, 20, 10)

        header = QHBoxLayout()
        title = QLabel("🌏 Translator")
        title.setObjectName("appTitle")
        header.addWidget(title)
        header.addSpacing(24)
        self.langs = LanguageBar()
        header.addWidget(self.langs, 1)
        lay.addLayout(header)

        self.banner = QLabel(
            "⚠ Chưa có đủ mô hình dịch. Vào thẻ <b>⚙ Mô hình</b> và bấm <b>Tải tất cả mô hình</b> "
            "(chỉ cần Internet một lần)."
        )
        self.banner.setObjectName("banner")
        self.banner.setTextFormat(Qt.TextFormat.RichText)
        self.banner.hide()
        lay.addWidget(self.banner)

        status = self.statusBar().showMessage
        self.tabs = QTabWidget()
        self.text_tab = TextTab(self.langs, status)
        self.image_tab = ImageTab(self.langs, status)
        self.file_tab = FileTab(self.langs, status)
        self.model_tab = ModelTab(status)
        self.tabs.addTab(self.text_tab, "📝 Văn bản")
        self.tabs.addTab(self.image_tab, "🖼️ Hình ảnh")
        self.tabs.addTab(self.file_tab, "📄 Tệp tin")
        self.tabs.addTab(self.model_tab, "⚙ Mô hình")
        lay.addWidget(self.tabs, 1)

        self.model_tab.models_changed.connect(lambda ok: self.banner.setVisible(not ok))
        self.banner.linkActivated.connect(lambda _: self.tabs.setCurrentWidget(self.model_tab))
        self.banner.mousePressEvent = lambda _: self.tabs.setCurrentWidget(self.model_tab)
        self.model_tab.refresh()
        status(f"Sẵn sàng · Bộ máy dịch: {get_engine().name}")


def run() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Translator")
    app.setStyleSheet(STYLE)
    win = MainWindow()
    win.show()
    return app.exec()
