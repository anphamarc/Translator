from PIL import Image

from translator_app.ocr import TextBlock, render_translation


def test_render_covers_original_text_with_background():
    img = Image.new("RGB", (300, 100), (250, 240, 200))
    img.paste((0, 0, 0), (20, 20, 120, 60))  # gia lam chu den
    out = render_translation(img, [TextBlock((20, 20, 120, 60), "x", "Xin chào")], "vi")
    assert out.size == img.size
    assert out.getpixel((5, 5)) == (250, 240, 200)
    # nen trong khoi chu da duoc to lai bang mau nen (khong con toan mau den)
    colors = {out.getpixel((x, 58)) for x in range(20, 120)}
    assert (250, 240, 200) in colors
