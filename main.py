"""
Resume RAG Assistant - Main Entry Point

Usage:
    # Start web UI
    python main.py web

    # Start CLI interactive mode
    python main.py cli

    # Index resumes
    python main.py index

    # Quick chat
    python main.py chat "What are my top skills?"
"""

import sys
import subprocess
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def main():
    if len(sys.argv) < 2:
        print_help()
        return

    command = sys.argv[1].lower()

    if command == "web":
        # Start Streamlit web UI
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            "src/ui/web.py",
            "--server.port", "8501"
        ])

    elif command == "cli":
        # Start CLI interactive mode
        from src.ui.cli import app
        sys.argv = sys.argv[1:]  # Remove 'cli' from args
        if len(sys.argv) == 1:
            sys.argv.append("interactive")
        app()

    elif command == "index":
        # Index resumes
        from src.rag import ResumeRAG
        from config.settings import settings

        path = sys.argv[2] if len(sys.argv) > 2 else settings.resumes_dir
        print(f"Indexing resumes from: {path}")

        rag = ResumeRAG()
        count = rag.index_resumes(Path(path))
        print(f"Done! Indexed {count} document chunks")

    elif command == "chat":
        # Quick chat
        if len(sys.argv) < 3:
            print("Usage: python main.py chat \"Your message here\"")
            return

        message = " ".join(sys.argv[2:])

        from src.rag import ResumeRAG
        import asyncio

        rag = ResumeRAG()
        print("Thinking...")
        response = asyncio.run(rag.chat(message))
        print(f"\nAssistant:\n{response}")

    elif command == "status":
        # Show status
        from src.rag import ResumeRAG
        from src.llm_backends import LLMRouter

        rag = ResumeRAG()
        router = LLMRouter()

        print("\n=== Resume RAG Assistant Status ===\n")

        status = rag.get_status()
        print(f"Indexed Documents: {status['indexed_documents']}")
        print(f"Resumes Directory: {status['resumes_directory']}")

        print("\nLLM Backends:")
        for name, info in router.list_backends().items():
            status_icon = "✓" if info["available"] else "✗"
            default = " (default)" if info["is_default"] else ""
            print(f"  {status_icon} {name}: {info['model']}{default}")

    elif command in ["help", "-h", "--help"]:
        print_help()

    else:
        print(f"Unknown command: {command}")
        print_help()


def print_help():
    print("""
Resume RAG Assistant
====================

Commands:
    web             Start the Streamlit web interface
    cli             Start interactive CLI mode
    index [path]    Index resumes from a directory
    chat "message"  Quick chat with the assistant
    status          Show system status
    help            Show this help message

Examples:
    python main.py web
    python main.py cli
    python main.py index ./resumes
    python main.py chat "What are my Python skills?"
    python main.py status

For CLI subcommands, run:
    python -m src.ui.cli --help
""")


if __name__ == "__main__":
    main()
