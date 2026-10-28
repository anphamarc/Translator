"""Nhan dang chu trong anh (OCR) offline bang EasyOCR."""

from __future__ import annotations

import functools
import sys
import threading
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from translator_app import config
from translator_app.languages import AUTO, detect_language

# EasyOCR khong ghep duoc tieng Han va tieng Viet trong cung mot bo doc,
# nen moi ngon ngu co mot bo doc rieng (deu doc kem tieng Anh).
# Bo doc "vi" (chu Latin) doc duoc ca tieng Anh.
_READER_LANGS = {"ko": ["ko", "en"], "vi": ["vi", "en"]}
_readers: dict[str, object] = {}
_lock = threading.Lock()


@dataclass
class TextBlock:
    box: tuple[int, int, int, int]  # x0, y0, x1, y1
    text: str
    translation: str = ""


def get_reader(lang: str, download: bool = False):
    key = "ko" if lang == "ko" else "vi"
    with _lock:
        if key not in _readers:
            config.prepare_environment()
            import easyocr

            _readers[key] = easyocr.Reader(
                _READER_LANGS[key],
                gpu=False,
                model_storage_directory=str(config.OCR_DIR),
                user_network_directory=str(config.OCR_DIR),
                download_enabled=download,
                verbose=False,
            )
        return _readers[key]


def _read(image: Image.Image, lang: str) -> list[TextBlock]:
    import numpy as np

    reader = get_reader(lang)
    arr = np.array(image.convert("RGB"))
    result = reader.readtext(arr, paragraph=True, x_ths=0.8, y_ths=0.4)
    blocks = []
    for box, text in result:
        xs = [int(p[0]) for p in box]
        ys = [int(p[1]) for p in box]
        blocks.append(TextBlock((min(xs), min(ys), max(xs), max(ys)), text))
    blocks.sort(key=lambda b: (b.box[1] // 20, b.box[0]))
    return blocks


def recognize(image: Image.Image, lang: str = AUTO) -> tuple[list[TextBlock], str]:
    """Tra ve (cac khoi chu, ngon ngu nhan dien duoc)."""
    if lang != AUTO:
        return _read(image, lang), lang
    # Thu bo doc Han truoc; neu khong thay chu Han thi doc lai bang bo doc Viet
    blocks = _read(image, "ko")
    joined = " ".join(b.text for b in blocks)
    if detect_language(joined) == "ko":
        return blocks, "ko"
    blocks = _read(image, "vi")
    return blocks, detect_language(" ".join(b.text for b in blocks))


def blocks_to_text(blocks: list[TextBlock]) -> str:
    return "\n".join(b.text for b in blocks)


# ---- ve ban dich len anh ----------------------------------------------------

_FONT_CANDIDATES = {
    "ko": ["malgun.ttf", "NotoSansCJK-Regular.ttc", "NotoSansKR-Regular.otf", "AppleGothic.ttf"],
    "default": ["arial.ttf", "segoeui.ttf", "DejaVuSans.ttf", "NotoSans-Regular.ttf", "Arial Unicode.ttf"],
}


def _font_dirs() -> list[Path]:
    if sys.platform.startswith("win"):
        return [Path(r"C:\Windows\Fonts")]
    if sys.platform == "darwin":
        return [Path("/Library/Fonts"), Path("/System/Library/Fonts"), Path("/System/Library/Fonts/Supplemental")]
    return [Path("/usr/share/fonts"), Path.home() / ".fonts"]


@functools.lru_cache(maxsize=None)
def _find_font(lang: str) -> str | None:
    for name in _FONT_CANDIDATES.get(lang, []) + _FONT_CANDIDATES["default"]:
        for d in _font_dirs():
            hits = [d / name] if (d / name).exists() else list(d.rglob(name)) if d.exists() else []
            if hits:
                return str(hits[0])
    return None


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, width: int) -> list[str]:
    lines, cur = [], ""
    for u in text.split(" "):
        trial = f"{cur} {u}" if cur else u
        if draw.textlength(trial, font=font) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = u
    if cur:
        lines.append(cur)
    return lines


def _background_color(img: Image.Image, box: tuple[int, int, int, int]) -> tuple[int, int, int]:
    """Mau nen = mau pho bien nhat tren vien quanh khoi chu."""
    x0, y0, x1, y1 = box
    x0, y0 = max(x0 - 2, 0), max(y0 - 2, 0)
    x1, y1 = min(x1 + 2, img.width - 1), min(y1 + 2, img.height - 1)
    pixels = [img.getpixel((x, y)) for x in range(x0, x1 + 1, 2) for y in (y0, y1)]
    pixels += [img.getpixel((x, y)) for y in range(y0, y1 + 1, 2) for x in (x0, x1)]
    # lam tron de gom cac mau gan giong nhau
    buckets: dict[tuple, list] = {}
    for px in pixels:
        buckets.setdefault(tuple(c // 16 for c in px[:3]), []).append(px)
    best = max(buckets.values(), key=len)
    return tuple(sum(c[i] for c in best) // len(best) for i in range(3))


def render_translation(image: Image.Image, blocks: list[TextBlock], target: str) -> Image.Image:
    """Phu ban dich len vi tri chu goc trong anh."""
    out = image.convert("RGB").copy()
    draw = ImageDraw.Draw(out)
    for b in blocks:
        if not b.translation:
            continue
        # Chon font theo noi dung thuc te (ban dich co the con sot chu Han)
        font_path = _find_font("ko" if detect_language(b.translation) == "ko" else target)
        x0, y0, x1, y1 = b.box
        w, h = max(x1 - x0, 10), max(y1 - y0, 10)
        edge = _background_color(out, b.box)
        draw.rectangle((x0, y0, x1, y1), fill=edge)
        lum = 0.299 * edge[0] + 0.587 * edge[1] + 0.114 * edge[2]
        color = (0, 0, 0) if lum > 128 else (255, 255, 255)
        size = max(int(h * 0.8), 10)
        while True:
            font = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default(size)
            lines = _wrap(draw, b.translation, font, w)
            line_h = size * 1.2
            if len(lines) * line_h <= h * 1.15 or size <= 9:
                break
            size -= 1
        for i, line in enumerate(lines):
            draw.text((x0, y0 + i * line_h), line, fill=color, font=font)
    return out
