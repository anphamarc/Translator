"""Danh sach ngon ngu ho tro va nhan dien ngon ngu don gian (offline)."""

from __future__ import annotations

import re

# code -> ten hien thi
LANGUAGES: dict[str, str] = {
    "en": "Tiếng Anh",
    "ko": "Tiếng Hàn",
    "vi": "Tiếng Việt",
}

AUTO = "auto"

_HANGUL = re.compile(r"[가-힣ᄀ-ᇿ㄰-㆏]")
_LATIN = re.compile(r"[A-Za-zÀ-ɏḀ-ỿ]")
# Ky tu chi co trong tieng Viet (khong co trong tieng Anh)
_VIETNAMESE = re.compile(
    r"[ăâđêôơưĂÂĐÊÔƠƯàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợ"
    r"ùúủũụừứửữựỳýỷỹỵÀÁẢÃẠẰẮẲẴẶẦẤẨẪẬÈÉẺẼẸỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌỒỐỔỖỘỜỚỞỠỢ"
    r"ÙÚỦŨỤỪỨỬỮỰỲÝỶỸỴ]"
)


def detect_language(text: str) -> str:
    """Doan ngon ngu cua doan van dua tren bang chu cai.

    Tra ve "ko", "vi" hoac "en" (mac dinh khi khong xac dinh duoc).
    """
    hangul = len(_HANGUL.findall(text))
    latin = len(_LATIN.findall(text))
    if hangul and hangul >= latin * 0.3:
        return "ko"
    if latin and len(_VIETNAMESE.findall(text)) >= max(1, latin * 0.02):
        return "vi"
    return "en"


def resolve_source(source: str, text: str) -> str:
    return detect_language(text) if source == AUTO else source
