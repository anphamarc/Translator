# Translator

Ứng dụng dịch **Anh ↔ Hàn ↔ Việt** chạy **hoàn toàn offline** trên máy tính, giao diện tiếng Việt, dễ dùng.

| Thẻ | Chức năng |
| --- | --- |
| 📝 **Văn bản** | Gõ/dán văn bản, tự dịch khi đang gõ, tự nhận diện ngôn ngữ, sao chép bản dịch, mở tệp `.txt` |
| 🖼️ **Hình ảnh** | Kéo thả, mở hoặc **dán ảnh (Ctrl+V)** → nhận dạng chữ (OCR) → dịch → xem và lưu **ảnh đã được phủ bản dịch** |
| 📄 **Tệp tin** | Dịch hàng loạt Word `.docx`, PowerPoint `.pptx`, Excel `.xlsx`, PDF (xuất ra `.docx`, có OCR cho trang scan), `.txt`, `.md`, phụ đề `.srt`, ảnh — **giữ nguyên định dạng gốc** |
| ⚙ **Mô hình** | Xem mô hình đã cài, tải mô hình (cần mạng một lần) hoặc cài từ tệp khi máy không có mạng |

Dịch Hàn ↔ Việt được thực hiện qua trung gian tiếng Anh.

## Cài đặt trên Windows (không cần cài Python)

1. Tải tệp **`Translator-windows.zip`**:
   - Bản phát hành ổn định: mục **Releases** ở trang GitHub của repo.
   - Bản mới nhất đang phát triển: thẻ **Actions** → chọn lần chạy **Build Windows app** mới nhất có dấu ✅ → kéo xuống mục **Artifacts** → bấm **Translator-windows** (cần đăng nhập GitHub). Tệp tải về là một zip chứa `Translator-windows.zip`, giải nén thêm một lần nữa.
2. Giải nén ra một thư mục, ví dụ `C:\Translator`.
3. Nhấp đúp **`Translator.exe`**. Nếu Windows hiện cảnh báo “Windows protected your PC”, bấm **More info → Run anyway** (do ứng dụng chưa được ký số).

Bản đóng gói đã kèm sẵn toàn bộ mô hình, nên **chạy offline ngay**, không cần Internet. Muốn chuyển sang máy khác thì chép nguyên thư mục.

### Cài từ mã nguồn (cho nhà phát triển)

Cần Python 3.12: nhấp đúp `install.bat` để cài, sau đó dùng `run.bat` để chạy. Nếu máy không có mạng, có thể tải các tệp `.argosmodel` ở máy khác rồi vào thẻ **⚙ Mô hình → Cài từ tệp .argosmodel…**.

### Tự đóng gói

Mỗi lần đẩy code lên GitHub, workflow `.github/workflows/build-windows.yml` sẽ tự build bản Windows, tải mô hình, chạy tự kiểm tra (dịch thật và OCR thật), rồi nén thành `Translator-windows.zip`. Khi đẩy một tag dạng `v0.1.0`, tệp zip sẽ được đăng lên mục Releases.

## Chạy từ dòng lệnh (macOS / Linux / nhà phát triển)

```bash
python -m venv .venv
```
```bash
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
```
```bash
.venv/bin/python -m translator_app.models
```
```bash
.venv/bin/python -m translator_app
```

Chạy kiểm thử:

```bash
.venv/bin/python -m pytest
```

## Công nghệ

- **Giao diện:** PySide6 (Qt)
- **Dịch offline:** [Argos Translate](https://github.com/argosopentech/argos-translate) (OpenNMT + CTranslate2, chạy trên CPU)
- **Nhận dạng chữ trong ảnh:** [EasyOCR](https://github.com/JaidedAI/EasyOCR)
- **Đọc/ghi tệp:** python-docx, python-pptx, openpyxl, PyMuPDF, Pillow

## Cấu trúc mã nguồn

```
translator_app/
  __main__.py        # điểm khởi chạy: python -m translator_app
  config.py          # đường dẫn thư mục dữ liệu / mô hình
  languages.py       # danh sách ngôn ngữ, tự nhận diện Anh/Hàn/Việt
  engine.py          # bộ máy dịch (Argos), dịch theo đoạn, dịch trung gian qua tiếng Anh
  models.py          # kiểm tra / tải / cài mô hình
  ocr.py             # nhận dạng chữ trong ảnh và vẽ bản dịch lên ảnh
  file_translate.py  # dịch từng loại tệp, giữ định dạng
  gui/               # giao diện: cửa sổ chính, các thẻ, kiểu dáng
  selftest.py        # tự kiểm tra bản đóng gói: Translator.exe --selftest
packaging/           # cấu hình PyInstaller để đóng gói thành .exe
tests/               # kiểm thử tự động (dùng bộ dịch giả, không cần mô hình)
```

## Giới hạn hiện tại

- Chất lượng dịch của mô hình offline thấp hơn Google/DeepL, nhất là với tiếng Hàn.
- PDF được xuất ra Word (.docx) chứ không giữ nguyên bố cục trang PDF.
- Với Word/PowerPoint, mỗi đoạn văn lấy định dạng của phần chữ đầu tiên trong đoạn (ví dụ chữ in đậm giữa câu sẽ không còn đậm riêng).
