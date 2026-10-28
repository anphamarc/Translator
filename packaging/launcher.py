"""Diem vao cho ban dong goi .exe (PyInstaller)."""

import multiprocessing
import os
import sys

# Ban .exe khong co cua so console: sys.stdout/stderr la None, print() se loi
for _name in ("stdout", "stderr"):
    if getattr(sys, _name) is None:
        setattr(sys, _name, open(os.devnull, "w", encoding="utf-8"))

if __name__ == "__main__":
    multiprocessing.freeze_support()
    if "--selftest" in sys.argv:
        from translator_app.selftest import run_selftest

        raise SystemExit(run_selftest())
    if "--download-models" in sys.argv:
        from translator_app.models import download_all

        download_all()
        raise SystemExit(0)
    from translator_app.gui.main_window import run

    raise SystemExit(run())
