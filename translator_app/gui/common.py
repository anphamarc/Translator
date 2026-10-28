"""Thanh phan dung chung cho giao dien: luong nen, keo-tha, kieu dang."""

from __future__ import annotations

import io
import traceback
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, QObject, QRunnable, Qt, QThreadPool, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QImage, QPixmap
from PySide6.QtWidgets import QLabel, QListWidget, QMessageBox, QWidget

from translator_app.engine import Cancelled, MissingModelError


class _Signals(QObject):
    done = Signal(object)
    failed = Signal(str)
    progress = Signal(int, int)
    log = Signal(str)


class Worker(QRunnable):
    """Chay ham nang (dich, OCR, tai mo hinh) o luong nen de giao dien khong bi treo.

    Ham duoc goi dang fn(worker, *args, **kwargs); trong ham co the dung
    worker.progress(done, total), worker.cancelled() va worker.log(text).
    """

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn, self.args, self.kwargs = fn, args, kwargs
        self.signals = _Signals()
        self.progress = self.signals.progress.emit
        self.log = self.signals.log.emit
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def cancelled(self) -> bool:
        return self._cancel

    def run(self) -> None:
        try:
            result = self.fn(self, *self.args, **self.kwargs)
        except Cancelled:
            self.signals.failed.emit("Đã hủy.")
        except Exception as exc:  # noqa: BLE001 - hien thi moi loi cho nguoi dung
            traceback.print_exc()
            self.signals.failed.emit(friendly_error(exc))
        else:
            self.signals.done.emit(result)


_active: set[Worker] = set()


def start(worker: Worker, done=None, failed=None, progress=None, log=None) -> Worker:
    """Noi tin hieu roi moi chay, de khong lo ket qua cua viec chay qua nhanh."""
    sig = worker.signals
    for signal, slot in ((sig.done, done), (sig.failed, failed), (sig.progress, progress), (sig.log, log)):
        if slot:
            signal.connect(slot)
    # Giu tham chieu den khi chay xong
    _active.add(worker)
    sig.done.connect(lambda _: _active.discard(worker))
    sig.failed.connect(lambda _: _active.discard(worker))
    worker.setAutoDelete(False)
    QThreadPool.globalInstance().start(worker)
    return worker


def friendly_error(exc: Exception) -> str:
    if isinstance(exc, MissingModelError):
        return str(exc)
    if isinstance(exc, ModuleNotFoundError):
        return (
            f"Thiếu thư viện '{exc.name}'. Hãy chạy lại install.bat "
            "(hoặc: pip install -r requirements.txt)."
        )
    if isinstance(exc, FileNotFoundError) and "easyocr" in traceback.format_exc():
        return "Chưa có mô hình nhận dạng chữ. Vào thẻ 'Mô hình' để tải."
    return f"Có lỗi xảy ra: {exc}"


def show_error(parent: QWidget, message: str) -> None:
    QMessageBox.warning(parent, "Translator", message)


def open_path(path: str | Path) -> None:
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


def pil_to_pixmap(img) -> QPixmap:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    pix = QPixmap()
    pix.loadFromData(buf.getvalue(), "PNG")
    return pix


def qimage_to_pil(qimg: QImage):
    from PIL import Image

    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    qimg.save(buf, "PNG")
    return Image.open(io.BytesIO(bytes(buf.data())))


def _dropped_paths(event) -> list[Path]:
    return [Path(u.toLocalFile()) for u in event.mimeData().urls() if u.isLocalFile()]


class DropLabel(QLabel):
    """Vung hien thi anh, cho phep keo-tha tep vao."""

    files_dropped = Signal(list)

    def __init__(self, text: str):
        super().__init__(text)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setObjectName("dropArea")
        self.setWordWrap(True)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        self.files_dropped.emit(_dropped_paths(e))


class DropList(QListWidget):
    """Danh sach tep, cho phep keo-tha nhieu tep / thu muc vao."""

    files_dropped = Signal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setObjectName("dropList")
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        e.acceptProposedAction()

    def dropEvent(self, e):
        self.files_dropped.emit(_dropped_paths(e))


STYLE = """
* { font-size: 11pt; }
QMainWindow, QWidget#central { background: #f5f7fb; }
QLabel#appTitle { font-size: 18pt; font-weight: 600; color: #1f2a44; }
QLabel#hint { color: #5b6478; }
QLabel#banner {
    background: #fff4e5; border: 1px solid #f5c27a; border-radius: 8px;
    padding: 8px 12px; color: #7a4b00;
}
QTabWidget::pane { border: none; }
QTabBar::tab {
    background: transparent; padding: 10px 18px; margin-right: 4px;
    border-bottom: 3px solid transparent; color: #5b6478;
}
QTabBar::tab:selected { color: #2457d6; border-bottom-color: #2457d6; font-weight: 600; }
QPlainTextEdit, QListWidget, QTreeWidget, QLineEdit {
    background: white; border: 1px solid #d9deea; border-radius: 10px; padding: 8px;
}
QPlainTextEdit { font-size: 13pt; }
QPlainTextEdit:focus, QLineEdit:focus { border-color: #2457d6; }
QComboBox {
    background: white; border: 1px solid #d9deea; border-radius: 8px;
    padding: 6px 12px; min-width: 170px;
}
QPushButton {
    background: white; border: 1px solid #c9d0e0; border-radius: 8px; padding: 7px 16px;
}
QPushButton:hover { background: #eef2fb; }
QPushButton:disabled { color: #9aa3b5; }
QPushButton#primary { background: #2457d6; color: white; border: none; font-weight: 600; }
QPushButton#primary:hover { background: #1c47b3; }
QPushButton#primary:disabled { background: #9db3ea; }
QPushButton#swap { min-width: 44px; max-width: 44px; font-size: 14pt; }
QLabel#dropArea, QListWidget#dropList {
    border: 2px dashed #b8c3dc; border-radius: 12px; background: white; color: #5b6478;
}
QProgressBar {
    border: 1px solid #d9deea; border-radius: 8px; background: white; text-align: center; height: 20px;
}
QProgressBar::chunk { background: #2457d6; border-radius: 7px; }
"""
