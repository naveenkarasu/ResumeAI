@echo off
echo Starting Resume RAG Assistant - Web UI
echo.
cd /d "%~dp0"
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)
python main.py web
pause
