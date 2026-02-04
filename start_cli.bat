@echo off
echo Starting Resume RAG Assistant - CLI
echo.
cd /d "%~dp0"
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)
python main.py cli
pause
