import pytest

from translator_app import engine
from translator_app.engine import TranslationEngine


class FakeEngine(TranslationEngine):
    """Bo dich gia: them tien to [src>dst] de kiem tra luong xu ly."""

    name = "fake"

    def __init__(self):
        self.calls = []

    def installed_pairs(self):
        return {("en", "ko"), ("ko", "en"), ("en", "vi"), ("vi", "en")}

    def _translate_one(self, text, src, dst):
        self.calls.append((text, src, dst))
        return f"[{src}>{dst}] {text}"


@pytest.fixture
def fake_engine():
    e = FakeEngine()
    engine.set_engine(e)
    yield e
    engine.set_engine(None)
