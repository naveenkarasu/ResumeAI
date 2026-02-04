@echo off
echo Starting ResumeAI - CLI
echo.
cd /d "%~dp0"
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)
python main.py cli
pause
