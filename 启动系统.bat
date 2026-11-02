@echo off
cd /d "%~dp0"
if exist "backend\.venv\Scripts\python.exe" (
    "backend\.venv\Scripts\python.exe" "launcher.py" %*
) else (
    echo [ERROR] Python environment not found at backend\.venv\Scripts\python.exe
    echo Please make sure the virtual environment exists.
    pause
)
