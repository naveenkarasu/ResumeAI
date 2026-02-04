@echo off
echo ========================================
echo Resume RAG Assistant - Installation
echo ========================================
echo.

cd /d "%~dp0"

echo [1/5] Creating virtual environment...
python -m venv venv
call venv\Scripts\activate.bat

echo.
echo [2/5] Installing dependencies...
pip install -r requirements.txt

echo.
echo [3/5] Installing Playwright browsers...
playwright install chromium

echo.
echo [4/5] Creating .env file...
if not exist .env (
    copy .env.example .env
    echo Created .env - EDIT THIS FILE AND ADD YOUR API KEYS!
) else (
    echo .env already exists
)

echo.
echo [5/5] Creating data directories...
if not exist data\resumes mkdir data\resumes
if not exist data\chroma_db mkdir data\chroma_db

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Edit .env and add GROQ_API_KEY (get free at https://console.groq.com/keys)
echo 2. Copy resumes to data\resumes\
echo 3. Run: python main.py index
echo 4. Run: start_web.bat or start_cli.bat
echo.
pause
