"""Bo may dich offline.

Mac dinh dung Argos Translate (OpenNMT/CTranslate2, chay hoan toan tren may).
Cap Han <-> Viet duoc dich qua trung gian tieng Anh.
"""

from __future__ import annotations

import re
import threading
from typing import Callable, Iterable

from translator_app import config
from translator_app.languages import AUTO, detect_language

ProgressFn = Callable[[int, int], None]
CancelFn = Callable[[], bool]

# Cac goi mo hinh can co: Anh <-> Han, Anh <-> Viet
REQUIRED_PAIRS: list[tuple[str, str]] = [("en", "ko"), ("ko", "en"), ("en", "vi"), ("vi", "en")]

_HAS_LETTER = re.compile(r"[^\W\d_]")


class Cancelled(Exception):
    """Nguoi dung bam Huy."""


class MissingModelError(RuntimeError):
    pass


class TranslationEngine:
    """Giao dien chung cho moi bo may dich."""

    name = "base"

    def installed_pairs(self) -> set[tuple[str, str]]:
        raise NotImplementedError

    def _translate_one(self, text: str, src: str, dst: str) -> str:
        raise NotImplementedError

    def reload(self) -> None:
        """Nap lai danh sach mo hinh sau khi cai them."""

    # ---- cac ham dung chung -------------------------------------------------

    def can_translate(self, src: str, dst: str) -> bool:
        if src == dst:
            return True
        pairs = self.installed_pairs()
        if (src, dst) in pairs:
            return True
        return (src, "en") in pairs and ("en", dst) in pairs

    def ensure_pair(self, src: str, dst: str) -> None:
        if not self.can_translate(src, dst):
            raise MissingModelError(
                f"Chưa cài mô hình dịch {src} → {dst}. "
                "Vào thẻ 'Mô hình' để tải hoặc cài từ file."
            )

    def translate_segment(self, text: str, src: str, dst: str) -> str:
        """Dich mot doan, giu nguyen khoang trang dau/cuoi va cac dong trong."""
        if not _HAS_LETTER.search(text):
            return text
        if src == AUTO:
            src = detect_language(text)
        if src == dst:
            return text
        self.ensure_pair(src, dst)
        lead = text[: len(text) - len(text.lstrip())]
        trail = text[len(text.rstrip()) :]
        core = text.strip()
        lines = core.split("\n")
        out = [self._translate_one(line, src, dst) if _HAS_LETTER.search(line) else line for line in lines]
        return lead + "\n".join(out) + trail

    def translate_batch(
        self,
        texts: Iterable[str],
        src: str,
        dst: str,
        progress: ProgressFn | None = None,
        cancelled: CancelFn | None = None,
    ) -> list[str]:
        """Dich nhieu doan; doan trung lap chi dich mot lan."""
        texts = list(texts)
        cache: dict[str, str] = {}
        unique = [t for t in dict.fromkeys(texts) if _HAS_LETTER.search(t)]
        total = len(unique)
        for i, t in enumerate(unique):
            if cancelled and cancelled():
                raise Cancelled()
            cache[t] = self.translate_segment(t, src, dst)
            if progress:
                progress(i + 1, total)
        return [cache.get(t, t) for t in texts]

    def translate_text(
        self,
        text: str,
        src: str,
        dst: str,
        progress: ProgressFn | None = None,
        cancelled: CancelFn | None = None,
    ) -> str:
        """Dich van ban dai theo tung doan (giu bo cuc xuong dong)."""
        paragraphs = re.split(r"(\n\s*\n)", text)
        idx = [i for i, p in enumerate(paragraphs) if i % 2 == 0]
        done = self.translate_batch([paragraphs[i] for i in idx], src, dst, progress, cancelled)
        for i, t in zip(idx, done):
            paragraphs[i] = t
        return "".join(paragraphs)


class ArgosEngine(TranslationEngine):
    name = "Argos Translate"

    def __init__(self) -> None:
        config.prepare_environment()
        self._lock = threading.Lock()
        self._translations: dict[tuple[str, str], object] = {}

    def installed_pairs(self) -> set[tuple[str, str]]:
        pkg = config.import_argos().package
        return {
            (p.from_code, p.to_code)
            for p in pkg.get_installed_packages()
            if getattr(p, "type", "translate") == "translate"
        }

    def reload(self) -> None:
        with self._lock:
            self._translations.clear()

    def _get(self, src: str, dst: str):
        key = (src, dst)
        if key not in self._translations:
            tr = config.import_argos().translate
            if (src, dst) not in self.installed_pairs():
                # Dich qua trung gian tieng Anh, vd. ko -> en -> vi
                first, second = self._get(src, "en"), self._get("en", dst)
                self._translations[key] = tr.CompositeTranslation(first, second)
            else:
                self._translations[key] = tr.get_translation_from_codes(src, dst)
        return self._translations[key]

    def _translate_one(self, text: str, src: str, dst: str) -> str:
        with self._lock:
            return self._get(src, dst).translate(text)


_engine: TranslationEngine | None = None


def get_engine() -> TranslationEngine:
    global _engine
    if _engine is None:
        _engine = ArgosEngine()
    return _engine


def set_engine(engine: TranslationEngine) -> None:
    """Dung trong kiem thu hoac khi them bo may dich khac."""
    global _engine
    _engine = engine
