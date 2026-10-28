"""Cac the chuc nang: Van ban, Hinh anh, Tep tin, Mo hinh."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidgetItem,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from translator_app import config
from translator_app.languages import AUTO, LANGUAGES, detect_language

from .common import DropLabel, DropList, Worker, open_path, pil_to_pixmap, qimage_to_pil, show_error, start


def _button(text: str, primary: bool = False, tip: str = "") -> QPushButton:
    b = QPushButton(text)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if primary:
        b.setObjectName("primary")
    if tip:
        b.setToolTip(tip)
    return b


class LanguageBar(QWidget):
    """Chon ngon ngu nguon / dich, dung chung cho moi the."""

    changed = Signal()
    swapped = Signal()

    def __init__(self):
        super().__init__()
        self.src = QComboBox()
        self.src.addItem("🔍 Tự động nhận diện", AUTO)
        self.dst = QComboBox()
        for code, name in LANGUAGES.items():
            self.src.addItem(name, code)
            self.dst.addItem(name, code)
        self.dst.setCurrentIndex(self.dst.findData("vi"))
        swap = _button("⇄", tip="Đảo chiều dịch")
        swap.setObjectName("swap")
        swap.clicked.connect(self.swap)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(QLabel("Dịch từ"))
        lay.addWidget(self.src)
        lay.addWidget(swap)
        lay.addWidget(QLabel("sang"))
        lay.addWidget(self.dst)
        lay.addStretch()
        self.src.currentIndexChanged.connect(self.changed)
        self.dst.currentIndexChanged.connect(self.changed)

    def source(self) -> str:
        return self.src.currentData()

    def target(self) -> str:
        return self.dst.currentData()

    def set_source(self, code: str) -> None:
        self.src.setCurrentIndex(self.src.findData(code))

    def swap(self, detected: str | None = None) -> None:
        src = self.source()
        if src == AUTO:
            src = detected if isinstance(detected, str) else ("en" if self.target() != "en" else "vi")
        dst = self.target()
        self.src.blockSignals(True)
        self.set_source(dst)
        self.src.blockSignals(False)
        self.dst.setCurrentIndex(self.dst.findData(src))
        self.swapped.emit()


# ---- Van ban ----------------------------------------------------------------

class TextTab(QWidget):
    def __init__(self, langs: LanguageBar, status):
        super().__init__()
        self.langs, self.status = langs, status
        self.worker: Worker | None = None
        self.pending = False
        self.detected: str | None = None

        self.input = QPlainTextEdit()
        self.input.setPlaceholderText("Nhập hoặc dán văn bản cần dịch…")
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Bản dịch sẽ hiện ở đây")
        self.info = QLabel("")
        self.info.setObjectName("hint")
        self.auto = QCheckBox("Tự dịch khi gõ")
        self.auto.setChecked(True)

        self.translate_btn = _button("Dịch  (Ctrl+Enter)", primary=True)
        clear_btn = _button("Xóa")
        copy_btn = _button("📋 Sao chép bản dịch")
        open_btn = _button("📂 Mở tệp .txt…")

        left = QVBoxLayout()
        left.addWidget(self.input)
        row = QHBoxLayout()
        row.addWidget(self.info)
        row.addStretch()
        row.addWidget(open_btn)
        row.addWidget(clear_btn)
        left.addLayout(row)
        right = QVBoxLayout()
        right.addWidget(self.output)
        row = QHBoxLayout()
        row.addWidget(self.auto)
        row.addStretch()
        row.addWidget(copy_btn)
        row.addWidget(self.translate_btn)
        right.addLayout(row)

        split = QSplitter()
        for lay in (left, right):
            w = QWidget()
            w.setLayout(lay)
            lay.setContentsMargins(0, 0, 0, 0)
            split.addWidget(w)
        QVBoxLayout(self).addWidget(split)

        self.timer = QTimer(self, singleShot=True, interval=900)
        self.timer.timeout.connect(self.translate)
        self.input.textChanged.connect(self._on_text_changed)
        self.translate_btn.clicked.connect(self.translate)
        clear_btn.clicked.connect(self.input.clear)
        copy_btn.clicked.connect(self._copy)
        open_btn.clicked.connect(self._open_txt)
        langs.changed.connect(self._on_lang_changed)
        langs.swapped.connect(self._on_swap)
        for seq in ("Ctrl+Return", "Ctrl+Enter"):
            QShortcut(QKeySequence(seq), self, self.translate)

    def _on_text_changed(self):
        text = self.input.toPlainText()
        self.info.setText(f"{len(text)} ký tự")
        if self.auto.isChecked():
            self.timer.start()
        if not text.strip():
            self.output.clear()

    def _on_lang_changed(self):
        if self.input.toPlainText().strip():
            self.translate()

    def _on_swap(self):
        if self.output.toPlainText().strip():
            text = self.output.toPlainText()
            self.input.blockSignals(True)
            self.input.setPlainText(text)
            self.input.blockSignals(False)
        self.translate()

    def _copy(self):
        QApplication.clipboard().setText(self.output.toPlainText())
        self.status("Đã sao chép bản dịch.")

    def _open_txt(self):
        from translator_app.file_translate import read_text_file

        path, _ = QFileDialog.getOpenFileName(self, "Mở tệp văn bản", "", "Văn bản (*.txt *.md *.srt)")
        if path:
            self.input.setPlainText(read_text_file(Path(path)))

    def translate(self):
        text = self.input.toPlainText()
        if not text.strip():
            return
        if self.worker:  # dang dich: dich lai sau khi xong
            self.pending = True
            return
        src, dst = self.langs.source(), self.langs.target()
        self.detected = detect_language(text) if src == AUTO else None
        if self.detected:
            self.info.setText(f"{len(text)} ký tự · Nhận diện: {LANGUAGES[self.detected]}")
        self.translate_btn.setEnabled(False)
        self.status("Đang dịch…")

        def job(w, text, src, dst):
            from translator_app.engine import get_engine

            return get_engine().translate_text(text, src, dst, cancelled=w.cancelled)

        self.worker = start(Worker(job, text, src, dst), done=self._done, failed=self._failed)

    def _finish(self):
        self.worker = None
        self.translate_btn.setEnabled(True)
        if self.pending:
            self.pending = False
            self.translate()

    def _done(self, result: str):
        self.output.setPlainText(result)
        self.status("Đã dịch xong.")
        self._finish()

    def _failed(self, msg: str):
        self.status(msg)
        self.output.setPlainText("⚠ " + msg)
        self._finish()


# ---- Hinh anh ---------------------------------------------------------------

IMAGE_FILTER = "Ảnh (*.png *.jpg *.jpeg *.bmp *.webp *.tif *.tiff)"


class ImageTab(QWidget):
    def __init__(self, langs: LanguageBar, status):
        super().__init__()
        self.langs, self.status = langs, status
        self.image = None
        self.translated = None
        self.worker: Worker | None = None

        self.view = DropLabel("Kéo thả ảnh vào đây\nhoặc bấm “Mở ảnh”, hoặc nhấn Ctrl+V để dán ảnh")
        self.view.setMinimumSize(360, 300)
        self.recognized = QPlainTextEdit()
        self.recognized.setPlaceholderText("Chữ nhận dạng được từ ảnh (có thể sửa rồi bấm “Dịch lại”)")
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Bản dịch")
        self.show_translated = QCheckBox("Hiện ảnh đã dịch")
        self.show_translated.setChecked(True)
        self.show_translated.toggled.connect(self._refresh_view)

        open_btn = _button("🖼️ Mở ảnh…")
        paste_btn = _button("📋 Dán ảnh")
        self.retranslate_btn = _button("Dịch lại", primary=True)
        self.save_btn = _button("💾 Lưu ảnh đã dịch")
        copy_btn = _button("Sao chép bản dịch")

        left = QVBoxLayout()
        left.addWidget(self.view, 1)
        row = QHBoxLayout()
        row.addWidget(open_btn)
        row.addWidget(paste_btn)
        row.addStretch()
        row.addWidget(self.show_translated)
        left.addLayout(row)
        right = QVBoxLayout()
        right.addWidget(QLabel("Chữ trong ảnh"))
        right.addWidget(self.recognized)
        right.addWidget(QLabel("Bản dịch"))
        right.addWidget(self.output)
        row = QHBoxLayout()
        row.addWidget(copy_btn)
        row.addWidget(self.save_btn)
        row.addStretch()
        row.addWidget(self.retranslate_btn)
        right.addLayout(row)

        split = QSplitter()
        for lay in (left, right):
            w = QWidget()
            lay.setContentsMargins(0, 0, 0, 0)
            w.setLayout(lay)
            split.addWidget(w)
        split.setSizes([600, 500])
        QVBoxLayout(self).addWidget(split)

        open_btn.clicked.connect(self._open)
        paste_btn.clicked.connect(self.paste)
        self.view.files_dropped.connect(lambda paths: paths and self.load(paths[0]))
        self.retranslate_btn.clicked.connect(self._retranslate)
        self.save_btn.clicked.connect(self._save)
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(self.output.toPlainText()))
        QShortcut(QKeySequence.StandardKey.Paste, self, self.paste)
        langs.changed.connect(lambda: self.image is not None and self.run_ocr())
        self.save_btn.setEnabled(False)

    def _open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn ảnh", "", IMAGE_FILTER)
        if path:
            self.load(path)

    def paste(self):
        img = QApplication.clipboard().image()
        if img.isNull():
            self.status("Bộ nhớ tạm không có ảnh.")
            return
        self.set_image(qimage_to_pil(img))

    def load(self, path):
        from PIL import Image

        try:
            self.set_image(Image.open(path))
        except Exception as exc:  # noqa: BLE001
            show_error(self, f"Không mở được ảnh: {exc}")

    def set_image(self, img):
        self.image = img.convert("RGB")
        self.translated = None
        self._refresh_view()
        self.run_ocr()

    def _refresh_view(self):
        img = self.translated if (self.translated is not None and self.show_translated.isChecked()) else self.image
        if img is None:
            return
        pix = pil_to_pixmap(img)
        self.view.setPixmap(
            pix.scaled(self.view.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        )

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._refresh_view()

    def _busy(self, busy: bool):
        self.retranslate_btn.setEnabled(not busy)
        self.save_btn.setEnabled(not busy and self.translated is not None)

    def run_ocr(self):
        if self.worker:
            return
        src, dst = self.langs.source(), self.langs.target()
        self.status("Đang nhận dạng chữ trong ảnh… (lần đầu có thể mất chút thời gian)")
        self.recognized.setPlainText("")
        self.output.setPlainText("")
        self._busy(True)

        def job(w, image, src, dst):
            from translator_app import ocr
            from translator_app.engine import get_engine

            blocks, detected = ocr.recognize(image, src)
            texts = get_engine().translate_batch([b.text for b in blocks], detected, dst, cancelled=w.cancelled)
            for b, t in zip(blocks, texts):
                b.translation = t
            return blocks, ocr.render_translation(image, blocks, dst)

        self.worker = start(Worker(job, self.image, src, dst), done=self._ocr_done, failed=self._failed)

    def _ocr_done(self, result):
        from translator_app import ocr

        blocks, self.translated = result
        self.worker = None
        self.recognized.setPlainText(ocr.blocks_to_text(blocks))
        self.output.setPlainText("\n".join(b.translation for b in blocks))
        self._refresh_view()
        self._busy(False)
        self.status("Không tìm thấy chữ trong ảnh." if not blocks else f"Đã dịch {len(blocks)} đoạn chữ trong ảnh.")

    def _failed(self, msg):
        self.worker = None
        self._busy(False)
        self.status(msg)
        show_error(self, msg)

    def _retranslate(self):
        text = self.recognized.toPlainText()
        if not text.strip() or self.worker:
            return
        src, dst = self.langs.source(), self.langs.target()
        self._busy(True)

        def job(w, text, src, dst):
            from translator_app.engine import get_engine

            return get_engine().translate_text(text, src, dst, cancelled=w.cancelled)

        def done(result):
            self.worker = None
            self.output.setPlainText(result)
            self._busy(False)
            self.status("Đã dịch lại.")

        self.worker = start(Worker(job, text, src, dst), done=done, failed=self._failed)

    def _save(self):
        if self.translated is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Lưu ảnh đã dịch", f"anh_{self.langs.target()}.png", "PNG (*.png)")
        if path:
            self.translated.save(path)
            self.status(f"Đã lưu {path}")


# ---- Tep tin ----------------------------------------------------------------

class FileTab(QWidget):
    def __init__(self, langs: LanguageBar, status):
        from translator_app.file_translate import SUPPORTED_EXT

        super().__init__()
        self.langs, self.status = langs, status
        self.supported = SUPPORTED_EXT
        self.worker: Worker | None = None
        self.last_output: Path | None = None

        hint = QLabel(
            "Hỗ trợ: Word (.docx), PowerPoint (.pptx), Excel (.xlsx), PDF (xuất ra .docx), "
            "văn bản (.txt, .md), phụ đề (.srt) và ảnh. Định dạng gốc được giữ nguyên."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        self.files = DropList()
        self.files.setMinimumHeight(180)
        self._placeholder()

        add_btn = _button("➕ Thêm tệp…")
        remove_btn = _button("Bỏ tệp đã chọn")
        clear_btn = _button("Xóa danh sách")
        self.out_dir = QLineEdit()
        self.out_dir.setPlaceholderText("Mặc định: lưu cùng thư mục với tệp gốc")
        out_btn = _button("Chọn thư mục…")
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.run_btn = _button("Dịch tất cả", primary=True)
        self.cancel_btn = _button("Hủy")
        self.cancel_btn.setEnabled(False)
        self.open_btn = _button("📂 Mở thư mục kết quả")
        self.open_btn.setEnabled(False)

        lay = QVBoxLayout(self)
        lay.addWidget(hint)
        lay.addWidget(self.files, 1)
        row = QHBoxLayout()
        for b in (add_btn, remove_btn, clear_btn):
            row.addWidget(b)
        row.addStretch()
        lay.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(QLabel("Lưu kết quả vào:"))
        row.addWidget(self.out_dir, 1)
        row.addWidget(out_btn)
        lay.addLayout(row)
        lay.addWidget(self.progress)
        row = QHBoxLayout()
        row.addWidget(self.open_btn)
        row.addStretch()
        row.addWidget(self.cancel_btn)
        row.addWidget(self.run_btn)
        lay.addLayout(row)

        add_btn.clicked.connect(self._add_dialog)
        remove_btn.clicked.connect(self._remove_selected)
        clear_btn.clicked.connect(lambda: (self.files.clear(), self._placeholder()))
        out_btn.clicked.connect(self._choose_out)
        self.files.files_dropped.connect(self.add_files)
        self.files.itemDoubleClicked.connect(self._open_item)
        self.run_btn.clicked.connect(self.run)
        self.cancel_btn.clicked.connect(lambda: self.worker and self.worker.cancel())
        self.open_btn.clicked.connect(lambda: self.last_output and open_path(self.last_output.parent))

    def _placeholder(self):
        if self.files.count() == 0:
            item = QListWidgetItem("Kéo thả tệp hoặc thư mục vào đây…")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.files.addItem(item)

    def _paths(self) -> list[Path]:
        return [
            Path(self.files.item(i).data(Qt.ItemDataRole.UserRole))
            for i in range(self.files.count())
            if self.files.item(i).data(Qt.ItemDataRole.UserRole)
        ]

    def add_files(self, paths):
        existing = set(self._paths())
        expanded = []
        for p in map(Path, paths):
            expanded += sorted(p.rglob("*")) if p.is_dir() else [p]
        added = 0
        for p in expanded:
            if p.suffix.lower() in self.supported and p not in existing:
                if not self._paths():
                    self.files.clear()
                item = QListWidgetItem(f"📄 {p.name}    —    {p.parent}")
                item.setData(Qt.ItemDataRole.UserRole, str(p))
                self.files.addItem(item)
                existing.add(p)
                added += 1
        skipped = len(expanded) - added
        self.status(f"Đã thêm {added} tệp" + (f", bỏ qua {skipped} tệp không hỗ trợ/trùng." if skipped else "."))

    def _add_dialog(self):
        exts = " ".join(f"*{e}" for e in sorted(self.supported))
        paths, _ = QFileDialog.getOpenFileNames(self, "Chọn tệp cần dịch", "", f"Tệp hỗ trợ ({exts})")
        self.add_files(paths)

    def _remove_selected(self):
        for item in self.files.selectedItems():
            self.files.takeItem(self.files.row(item))
        self._placeholder()

    def _choose_out(self):
        d = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu kết quả")
        if d:
            self.out_dir.setText(d)

    def _open_item(self, item):
        result = item.data(Qt.ItemDataRole.UserRole + 1)
        if result:
            open_path(result)

    def run(self):
        paths = self._paths()
        if not paths:
            self.status("Chưa có tệp nào. Hãy thêm tệp cần dịch.")
            return
        src, dst = self.langs.source(), self.langs.target()
        out_dir = self.out_dir.text().strip() or None
        self.run_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress.setValue(0)

        def job(w, paths, src, dst, out_dir):
            from translator_app.file_translate import translate_file

            results = []
            for i, p in enumerate(paths):
                if w.cancelled():
                    break
                w.log(f"{i}|⏳ Đang dịch")

                def prog(done, total, i=i):
                    w.progress(int((i + done / max(total, 1)) * 1000 / len(paths)), 1000)

                try:
                    out = translate_file(p, src, dst, out_dir, progress=prog, cancelled=w.cancelled)
                    results.append(out)
                    w.log(f"{i}|✅ Xong → {out.name}|{out}")
                except Exception as exc:  # noqa: BLE001 - mot tep loi khong dung ca dot
                    from .common import friendly_error

                    w.log(f"{i}|❌ {friendly_error(exc)}")
                w.progress((i + 1) * 1000 // len(paths), 1000)
            return results

        self.worker = start(
            Worker(job, paths, src, dst, out_dir),
            done=self._done,
            failed=self._done,
            progress=lambda d, t: (self.progress.setMaximum(t), self.progress.setValue(d)),
            log=self._on_file_status,
        )

    def _on_file_status(self, msg: str):
        idx, text, *out = msg.split("|")
        item = self.files.item(int(idx))
        name = Path(item.data(Qt.ItemDataRole.UserRole)).name
        item.setText(f"{name}    {text}")
        if out:
            item.setData(Qt.ItemDataRole.UserRole + 1, out[0])
            item.setToolTip("Nhấp đúp để mở tệp kết quả")
            self.last_output = Path(out[0])
            self.open_btn.setEnabled(True)

    def _done(self, result):
        self.worker = None
        self.run_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        if isinstance(result, list):
            self.status(f"Hoàn tất: đã dịch {len(result)} tệp. Nhấp đúp vào tệp để mở kết quả.")
        else:
            self.status(result)


# ---- Mo hinh ----------------------------------------------------------------

class ModelTab(QWidget):
    models_changed = Signal(bool)  # True khi da du mo hinh dich

    def __init__(self, status):
        super().__init__()
        self.status = status
        self.worker: Worker | None = None

        intro = QLabel(
            "Ứng dụng dịch hoàn toàn offline. Bạn chỉ cần Internet <b>một lần</b> để tải mô hình "
            "(khoảng 1 GB). Nếu máy không có mạng, có thể cài từ tệp <code>.argosmodel</code> "
            "tải sẵn ở máy khác, hoặc chép nguyên thư mục <code>data</code> sang."
        )
        intro.setWordWrap(True)
        intro.setObjectName("hint")
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Mô hình", "Trạng thái"])
        self.tree.setColumnWidth(0, 320)
        self.tree.setRootIsDecorated(False)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(160)
        self.download_btn = _button("⬇ Tải tất cả mô hình còn thiếu", primary=True)
        file_btn = _button("Cài từ tệp .argosmodel…")
        folder_btn = _button("📂 Mở thư mục dữ liệu")
        refresh_btn = _button("Kiểm tra lại")

        lay = QVBoxLayout(self)
        lay.addWidget(intro)
        lay.addWidget(self.tree, 1)
        row = QHBoxLayout()
        row.addWidget(self.download_btn)
        row.addWidget(file_btn)
        row.addStretch()
        row.addWidget(refresh_btn)
        row.addWidget(folder_btn)
        lay.addLayout(row)
        lay.addWidget(self.log)

        self.download_btn.clicked.connect(self._download)
        file_btn.clicked.connect(self._install_file)
        folder_btn.clicked.connect(lambda: (config.prepare_environment(), open_path(config.DATA_DIR)))
        refresh_btn.clicked.connect(self.refresh)

    def refresh(self):
        def job(w):
            from translator_app import models

            rows = [(s.label, s.installed) for s in models.translation_status()]
            rows.append(("Nhận dạng chữ trong ảnh (Anh/Hàn/Việt)", models.ocr_installed()))
            return rows

        start(Worker(job), done=self._show, failed=lambda m: self.log.appendPlainText("⚠ " + m))

    def _show(self, rows):
        self.tree.clear()
        for label, ok in rows:
            self.tree.addTopLevelItem(QTreeWidgetItem([label, "✅ Đã cài" if ok else "❌ Chưa cài"]))
        self.models_changed.emit(all(ok for _, ok in rows[:-1]))

    def _download(self):
        if self.worker:
            return
        self.download_btn.setEnabled(False)
        self.log.appendPlainText("Bắt đầu tải mô hình (cần Internet)…")

        def job(w):
            from translator_app import models

            models.download_all(log=w.log)

        self.worker = start(
            Worker(job),
            done=lambda _: self._after_download(None),
            failed=self._after_download,
            log=self.log.appendPlainText,
        )

    def _after_download(self, error):
        self.worker = None
        self.download_btn.setEnabled(True)
        if error:
            self.log.appendPlainText(f"⚠ {error} — kiểm tra kết nối Internet rồi thử lại.")
        self.refresh()

    def _install_file(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Chọn gói mô hình", "", "Argos model (*.argosmodel)")
        if not paths:
            return

        def job(w, paths):
            from translator_app import models

            for p in paths:
                models.install_from_file(p)
                w.log(f"✓ Đã cài {Path(p).name}")

        start(
            Worker(job, paths),
            done=lambda _: self.refresh(),
            failed=lambda m: self.log.appendPlainText("⚠ " + m),
            log=self.log.appendPlainText,
        )
