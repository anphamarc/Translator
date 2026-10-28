# Translator

Ứng dụng dịch **Anh ↔ Hàn ↔ Việt** chạy **hoàn toàn offline** trên máy tính, giao diện tiếng Việt, dễ dùng.

| Thẻ | Chức năng |
| --- | --- |
| 📝 **Văn bản** | Gõ/dán văn bản, tự dịch khi đang gõ, tự nhận diện ngôn ngữ, sao chép bản dịch, mở tệp `.txt` |
| 🖼️ **Hình ảnh** | Kéo thả, mở hoặc **dán ảnh (Ctrl+V)** → nhận dạng chữ (OCR) → dịch → xem và lưu **ảnh đã được phủ bản dịch** |
| 📄 **Tệp tin** | Dịch hàng loạt Word `.docx`, PowerPoint `.pptx`, Excel `.xlsx`, PDF (xuất ra `.docx`, có OCR cho trang scan), `.txt`, `.md`, phụ đề `.srt`, ảnh — **giữ nguyên định dạng gốc** |
| ⚙ **Mô hình** | Xem mô hình đã cài, tải mô hình (cần mạng một lần) hoặc cài từ tệp khi máy không có mạng |

Dịch Hàn ↔ Việt được thực hiện qua trung gian tiếng Anh.

## Cài đặt trên Windows

1. Cài **Python 3.12** từ <https://www.python.org/downloads/> — khi cài nhớ tick **“Add python.exe to PATH”**.
2. Tải mã nguồn về:
   ```bash
   git clone https://github.com/anphamarc/Translator.git
   ```
3. Mở thư mục `Translator`, nhấp đúp **`install.bat`**. Script sẽ tạo môi trường `.venv`, cài thư viện và tải mô hình (khoảng 1–2 GB, chỉ cần Internet **một lần**).
4. Từ đó về sau, nhấp đúp **`run.bat`** để mở ứng dụng — không cần mạng.

### Dùng trên máy không có Internet

Cài đặt trên một máy có mạng, rồi chép **cả thư mục `Translator`** (gồm `.venv` và `data`) sang máy kia. Mô hình được lưu trong thư mục `data/` cạnh mã nguồn.

Hoặc tải các tệp `.argosmodel` (en→ko, ko→en, en→vi, vi→en) ở máy khác, rồi vào thẻ **⚙ Mô hình → Cài từ tệp .argosmodel…**.

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
tests/               # kiểm thử tự động (dùng bộ dịch giả, không cần mô hình)
```

## Giới hạn hiện tại

- Chất lượng dịch của mô hình offline thấp hơn Google/DeepL, nhất là với tiếng Hàn.
- PDF được xuất ra Word (.docx) chứ không giữ nguyên bố cục trang PDF.
- Với Word/PowerPoint, mỗi đoạn văn lấy định dạng của phần chữ đầu tiên trong đoạn (ví dụ chữ in đậm giữa câu sẽ không còn đậm riêng).
