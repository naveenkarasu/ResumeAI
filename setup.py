"""
Setup script for ResumeAI

Run this after cloning/downloading to:
1. Install dependencies
2. Copy your resumes
3. Set up environment variables
4. Initialize the vector store
"""

import subprocess
import sys
import shutil
from pathlib import Path


def main():
    project_root = Path(__file__).parent
    data_dir = project_root / "data"
    resumes_dir = data_dir / "resumes"

    print("=" * 50)
    print("ResumeAI - Setup")
    print("=" * 50)

    # Step 1: Create directories
    print("\n[1/5] Creating directories...")
    resumes_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "chroma_db").mkdir(exist_ok=True)
    print("  ✓ Directories created")

    # Step 2: Install dependencies
    print("\n[2/5] Installing dependencies...")
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], check=True)
        print("  ✓ Dependencies installed")
    except subprocess.CalledProcessError:
        print("  ✗ Failed to install dependencies. Run manually:")
        print("    pip install -r requirements.txt")

    # Step 3: Install Playwright browsers (for ChatGPT Web)
    print("\n[3/5] Installing Playwright browsers (for ChatGPT Web)...")
    try:
        subprocess.run([
            sys.executable, "-m", "playwright", "install", "chromium"
        ], check=True)
        print("  ✓ Playwright browsers installed")
    except subprocess.CalledProcessError:
        print("  ⚠ Playwright install failed. ChatGPT Web backend may not work.")
        print("    Run manually: playwright install chromium")

    # Step 4: Create .env file
    print("\n[4/5] Setting up environment...")
    env_example = project_root / ".env.example"
    env_file = project_root / ".env"

    if not env_file.exists() and env_example.exists():
        shutil.copy(env_example, env_file)
        print("  ✓ Created .env file from .env.example")
        print("  ⚠ IMPORTANT: Edit .env and add your API keys!")
    elif env_file.exists():
        print("  ✓ .env file already exists")
    else:
        print("  ✗ .env.example not found")

    # Step 5: Copy resumes prompt
    print("\n[5/5] Resume setup...")
    print(f"  Copy your resume files to: {resumes_dir}")
    print("  Supported formats: .tex (LaTeX), .txt")

    # Check for existing resumes in common locations
    common_paths = [
        Path("C:/Users/karas/OneDrive/Desktop/tes/bullet/W2/resumes_latex"),
        Path.home() / "Documents" / "resumes",
        Path.home() / "resumes",
    ]

    for path in common_paths:
        if path.exists():
            print(f"\n  Found resumes at: {path}")
            response = input("  Copy these resumes? (y/n): ").strip().lower()
            if response == 'y':
                for ext in ['*.tex', '*.txt']:
                    for file in path.rglob(ext):
                        dest = resumes_dir / file.name
                        shutil.copy(file, dest)
                        print(f"    Copied: {file.name}")
                break

    print("\n" + "=" * 50)
    print("Setup Complete!")
    print("=" * 50)

    print("\nNext steps:")
    print("1. Edit .env and add your API keys:")
    print("   - GROQ_API_KEY (FREE): https://console.groq.com/keys")
    print("   - Or install Ollama: https://ollama.ai/download")
    print("")
    print("2. Index your resumes:")
    print("   python main.py index")
    print("")
    print("3. Start the assistant:")
    print("   python main.py web    # Web UI")
    print("   python main.py cli    # Command line")


if __name__ == "__main__":
    main()
