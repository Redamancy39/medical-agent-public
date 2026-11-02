@echo off
cd /d "%~dp0"
if exist "backend\.venv\Scripts\python.exe" (
    "backend\.venv\Scripts\python.exe" "launcher.py" --stop
) else (
    echo [ERROR] Python environment not found at backend\.venv\Scripts\python.exe
    pause
)
