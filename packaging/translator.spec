# Dong goi Translator thanh thu muc chay doc lap (khong can cai Python).
#   pyinstaller packaging/translator.spec --noconfirm
# Ket qua: dist/Translator/Translator.exe
from PyInstaller.utils.hooks import collect_all, copy_metadata

datas, binaries, hiddenimports = [], [], []
for pkg in (
    "argostranslate", "ctranslate2", "sentencepiece", "minisbd", "stanza", "easyocr", "sacremoses",
    "torchvision", "docx", "pptx",
):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h
for pkg in ("argostranslate", "stanza", "easyocr", "torch", "tqdm", "regex", "requests", "filelock", "numpy"):
    try:
        datas += copy_metadata(pkg)
    except Exception:
        pass

a = Analysis(
    ["launcher.py"],
    pathex=[".."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "matplotlib", "IPython", "jupyter", "pytest", "spacy", "thinc"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Translator",
    console=False,
    icon=None,
)
coll = COLLECT(exe, a.binaries, a.datas, name="Translator")
