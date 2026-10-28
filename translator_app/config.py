"""Duong dan du lieu cua ung dung.

Tat ca mo hinh (dich + OCR) duoc luu trong thu muc `data/` canh ma nguon
(hoac thu muc chi dinh boi bien moi truong TRANSLATOR_DATA_DIR), de co the
sao chep nguyen thu muc sang may khac va chay offline.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _default_data_dir() -> Path:
    if getattr(sys, "frozen", False):  # ban dong goi bang PyInstaller
        return Path(sys.executable).resolve().parent / "data"
    return Path(__file__).resolve().parent.parent / "data"


DATA_DIR = Path(os.environ.get("TRANSLATOR_DATA_DIR") or _default_data_dir())
ARGOS_DIR = DATA_DIR / "argos-packages"
OCR_DIR = DATA_DIR / "ocr-models"
MINISBD_DIR = DATA_DIR / "minisbd"


def prepare_environment() -> None:
    """Tao thu muc va tro Argos Translate vao thu muc du lieu cua ung dung.

    Phai goi truoc khi import argostranslate.
    """
    for d in (DATA_DIR, ARGOS_DIR, OCR_DIR, MINISBD_DIR):
        d.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("ARGOS_PACKAGES_DIR", str(ARGOS_DIR))
    # Chay tren CPU de tuong thich moi may
    os.environ.setdefault("ARGOS_DEVICE_TYPE", "cpu")
    # Tach cau bang MiniSBD (mo hinh nho, tai san vao data/) thay vi Stanza,
    # vi Stanza co the tu truy cap mang khi khoi tao.
    os.environ.setdefault("ARGOS_CHUNK_TYPE", "MINISBD")


def import_argos():
    """Import Argos Translate va tro bo nho dem MiniSBD vao thu muc data/."""
    prepare_environment()
    import argostranslate.package
    import argostranslate.translate
    import minisbd.models

    minisbd.models.cache_dir = str(MINISBD_DIR)
    return argostranslate
