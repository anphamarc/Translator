@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Translator: cai dat ===

where py >nul 2>nul
if %errorlevel%==0 (set PY=py -3) else (set PY=python)
%PY% --version >nul 2>nul
if errorlevel 1 (
    echo [LOI] Chua cai Python. Hay cai Python 3.12 tu https://www.python.org/downloads/
    echo       nho tick "Add python.exe to PATH" khi cai.
    pause
    exit /b 1
)

if not exist .venv (
    echo Dang tao moi truong ao .venv ...
    %PY% -m venv .venv || goto :error
)
echo Dang cai thu vien (lan dau mat vai phut)...
.venv\Scripts\python -m pip install --upgrade pip || goto :error
.venv\Scripts\python -m pip install -r requirements.txt || goto :error

echo.
echo Dang tai mo hinh dich va nhan dang chu (can Internet, khoang 1 GB)...
.venv\Scripts\python -m translator_app.models || goto :error

echo.
echo === Xong! Chay run.bat de mo ung dung. ===
pause
exit /b 0

:error
echo.
echo [LOI] Cai dat khong thanh cong. Xem thong bao loi o tren.
pause
exit /b 1
