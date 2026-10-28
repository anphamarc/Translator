import pytest

from translator_app.engine import Cancelled, MissingModelError, TranslationEngine


def test_keeps_whitespace_and_lines(fake_engine):
    out = fake_engine.translate_segment("  Hello\n\nWorld  ", "en", "vi")
    assert out == "  [en>vi] Hello\n\n[en>vi] World  "


def test_skips_numbers_and_same_language(fake_engine):
    assert fake_engine.translate_segment("12.5 %", "en", "vi") == "12.5 %"
    assert fake_engine.translate_segment("Xin chào", "auto", "vi") == "Xin chào"
    assert fake_engine.calls == []


def test_auto_detect_per_segment(fake_engine):
    out = fake_engine.translate_batch(["안녕", "Hello", "Hello"], "auto", "vi")
    assert out == ["[ko>vi] 안녕", "[en>vi] Hello", "[en>vi] Hello"]
    assert len(fake_engine.calls) == 2  # doan trung lap chi dich mot lan


def test_ko_vi_pivot_is_allowed(fake_engine):
    assert fake_engine.can_translate("ko", "vi")


def test_missing_model():
    class Empty(TranslationEngine):
        def installed_pairs(self):
            return set()

    with pytest.raises(MissingModelError):
        Empty().translate_segment("Hello", "en", "ko")


def test_cancel(fake_engine):
    with pytest.raises(Cancelled):
        fake_engine.translate_batch(["a", "b"], "en", "vi", cancelled=lambda: True)


def test_progress(fake_engine):
    seen = []
    fake_engine.translate_text("One\n\nTwo\n\nThree", "en", "ko", progress=lambda d, t: seen.append((d, t)))
    assert seen[-1] == (3, 3)
