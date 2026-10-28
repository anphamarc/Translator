"""Quan ly mo hinh: kiem tra, tai (can Internet mot lan) va cai tu file."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from translator_app import config
from translator_app.engine import REQUIRED_PAIRS, get_engine
from translator_app.languages import LANGUAGES

LogFn = Callable[[str], None]


@dataclass
class ModelStatus:
    label: str
    installed: bool


def translation_status() -> list[ModelStatus]:
    installed = get_engine().installed_pairs()
    return [
        ModelStatus(f"{LANGUAGES[s]} → {LANGUAGES[d]}", (s, d) in installed)
        for s, d in REQUIRED_PAIRS
    ]


def missing_pairs() -> list[tuple[str, str]]:
    installed = get_engine().installed_pairs()
    return [p for p in REQUIRED_PAIRS if p not in installed]


def install_from_file(path: str | Path) -> None:
    """Cai goi .argosmodel da tai san (dung khi may khong co Internet)."""
    config.prepare_environment()
    import argostranslate.package as pkg

    pkg.install_from_path(Path(path))
    get_engine().reload()


def download_translation_models(log: LogFn = print) -> None:
    """Tai va cai cac goi dich con thieu (can Internet)."""
    config.prepare_environment()
    import argostranslate.package as pkg

    todo = missing_pairs()
    if not todo:
        log("Mô hình dịch đã đủ.")
        return
    log("Đang lấy danh sách mô hình…")
    pkg.update_package_index()
    available = {(p.from_code, p.to_code): p for p in pkg.get_available_packages()}
    for pair in todo:
        p = available.get(pair)
        if p is None:
            log(f"Không tìm thấy mô hình {pair[0]} → {pair[1]} trên máy chủ.")
            continue
        log(f"Đang tải {LANGUAGES[pair[0]]} → {LANGUAGES[pair[1]]}…")
        pkg.install_from_path(p.download())
        log("  ✓ Xong")
    get_engine().reload()


def download_ocr_models(log: LogFn = print) -> None:
    """Tai mo hinh nhan dang chu cho Anh, Han, Viet (can Internet)."""
    from translator_app import ocr

    for lang in ("ko", "vi"):
        log(f"Đang tải mô hình nhận dạng chữ ({LANGUAGES[lang]})…")
        ocr.get_reader(lang, download=True)
        log("  ✓ Xong")


def ocr_installed() -> bool:
    files = {p.name for p in config.OCR_DIR.glob("*.pth")}
    return {"craft_mlt_25k.pth", "korean_g2.pth", "latin_g2.pth"} <= files


def download_all(log: LogFn = print) -> None:
    download_translation_models(log)
    download_ocr_models(log)
    log("Hoàn tất. Từ giờ ứng dụng có thể chạy hoàn toàn offline.")


if __name__ == "__main__":
    download_all()
