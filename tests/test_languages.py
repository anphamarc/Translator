from translator_app.languages import detect_language


def test_detect_korean():
    assert detect_language("안녕하세요, 만나서 반갑습니다") == "ko"


def test_detect_vietnamese():
    assert detect_language("Xin chào, rất vui được gặp bạn") == "vi"


def test_detect_english():
    assert detect_language("Hello, nice to meet you") == "en"


def test_mixed_korean_with_english_terms():
    assert detect_language("오늘 meeting은 3시에 시작합니다") == "ko"
