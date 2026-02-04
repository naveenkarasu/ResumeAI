"""
Command-Line Interface for Resume RAG Assistant

Usage:
    python -m src.ui.cli chat "What are my top skills?"
    python -m src.ui.cli email --job "job description here"
    python -m src.ui.cli index --path ./resumes
    python -m src.ui.cli status
"""

import typer
from typing import Optional
from pathlib import Path
from functools import lru_cache
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
import asyncio

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.rag import ResumeRAG
from src.llm_backends import LLMRouter
from src.web_search import WebSearch
from config.settings import settings

app = typer.Typer(
    name="resume-rag",
    help="AI-powered Resume Assistant with RAG",
    add_completion=False
)
console = Console()


@lru_cache(maxsize=1)
def get_rag() -> ResumeRAG:
    """Get RAG instance (cached to avoid reinitializing embedding model ~2-3s)"""
    return ResumeRAG()


@app.command()
def chat(
    message: str = typer.Argument(..., help="Your message or question"),
    backend: Optional[str] = typer.Option(None, "--backend", "-b", help="LLM backend (groq/ollama/openai/chatgpt_web)"),
    task: str = typer.Option("default", "--task", "-t", help="Task type (default/email_draft/resume_tailor/interview_prep)")
):
    """Chat with the Resume RAG Assistant"""
    rag = get_rag()

    with console.status("[bold green]Thinking..."):
        response = asyncio.run(rag.chat(message, task_type=task, backend=backend))

    console.print(Panel(Markdown(response), title="Assistant", border_style="green"))


@app.command()
def email(
    job: str = typer.Option(..., "--job", "-j", help="Job description or URL"),
    recipient: Optional[str] = typer.Option(None, "--to", help="Recipient name"),
    tone: str = typer.Option("professional", "--tone", help="Email tone"),
    backend: Optional[str] = typer.Option(None, "--backend", "-b", help="LLM backend")
):
    """Draft a job application email"""
    rag = get_rag()

    with console.status("[bold green]Drafting email..."):
        response = asyncio.run(rag.draft_email(job, recipient, tone, backend))

    console.print(Panel(response, title="Draft Email", border_style="blue"))


@app.command()
def tailor(
    job: str = typer.Option(..., "--job", "-j", help="Job description"),
    section: Optional[str] = typer.Option(None, "--section", "-s", help="Resume section to focus on"),
    backend: Optional[str] = typer.Option(None, "--backend", "-b", help="LLM backend")
):
    """Get resume tailoring suggestions for a job"""
    rag = get_rag()

    with console.status("[bold green]Analyzing..."):
        response = asyncio.run(rag.tailor_resume(job, section, backend))

    console.print(Panel(Markdown(response), title="Resume Suggestions", border_style="yellow"))


@app.command()
def interview(
    question: str = typer.Argument(..., help="Interview question to prepare for"),
    company: Optional[str] = typer.Option(None, "--company", "-c", help="Company name"),
    backend: Optional[str] = typer.Option(None, "--backend", "-b", help="LLM backend")
):
    """Prepare for an interview question"""
    rag = get_rag()

    with console.status("[bold green]Preparing response..."):
        response = asyncio.run(rag.interview_prep(question, company, backend))

    console.print(Panel(Markdown(response), title="Interview Prep", border_style="magenta"))


@app.command()
def index(
    path: Optional[Path] = typer.Option(None, "--path", "-p", help="Path to resumes directory"),
    clear: bool = typer.Option(False, "--clear", "-c", help="Clear existing index first")
):
    """Index resumes for RAG"""
    rag = get_rag()

    if clear:
        console.print("[yellow]Clearing existing index...[/yellow]")
        rag.clear_index()

    path = path or settings.resumes_dir

    with console.status(f"[bold green]Indexing resumes from {path}..."):
        count = rag.index_resumes(path)

    console.print(f"[green]✓ Indexed {count} document chunks[/green]")


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    web: bool = typer.Option(False, "--web", "-w", help="Search the web instead of resumes")
):
    """Search resumes or the web"""
    if web:
        ws = WebSearch()
        results = ws.search(query)

        table = Table(title="Web Search Results")
        table.add_column("Title", style="cyan")
        table.add_column("Snippet", style="white")

        for r in results:
            table.add_row(r["title"][:50], r["snippet"][:100] + "...")

        console.print(table)
    else:
        rag = get_rag()
        results = rag.retriever.search(query)

        table = Table(title="Resume Search Results")
        table.add_column("Section", style="cyan")
        table.add_column("Content", style="white")
        table.add_column("Relevance", style="green")

        for r in results:
            table.add_row(
                r["metadata"].get("section", "unknown"),
                r["content"][:80] + "...",
                f"{r['relevance']:.2f}"
            )

        console.print(table)


@app.command()
def backends():
    """List available LLM backends"""
    router = LLMRouter()
    backends_info = router.list_backends()

    table = Table(title="LLM Backends")
    table.add_column("Name", style="cyan")
    table.add_column("Model", style="white")
    table.add_column("Available", style="green")
    table.add_column("Default", style="yellow")

    for name, info in backends_info.items():
        available = "✓" if info["available"] else "✗"
        default = "★" if info["is_default"] else ""
        table.add_row(name, info["model"], available, default)

    console.print(table)


@app.command()
def status():
    """Show system status"""
    rag = get_rag()
    status = rag.get_status()

    table = Table(title="System Status")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Indexed Documents", str(status["indexed_documents"]))
    table.add_row("Chat History", str(status["chat_history_length"]))
    table.add_row("Current Backend", status["current_backend"])
    table.add_row("Available Backends", ", ".join(status["available_backends"]) or "None")
    table.add_row("Resumes Directory", status["resumes_directory"])

    console.print(table)


@app.command()
def interactive(
    backend: Optional[str] = typer.Option(None, "--backend", "-b", help="LLM backend to use")
):
    """Start interactive chat mode"""
    rag = get_rag()

    if backend:
        rag.llm_router.set_backend(backend)

    console.print(Panel(
        "[bold]Resume RAG Assistant[/bold]\n\n"
        "Commands:\n"
        "  /email <job>  - Draft an email\n"
        "  /tailor <job> - Get resume suggestions\n"
        "  /search <query> - Search resumes\n"
        "  /web <query>  - Search the web\n"
        "  /backend <name> - Switch LLM backend\n"
        "  /clear        - Clear chat history\n"
        "  /quit         - Exit\n\n"
        "Or just type your question!",
        title="Welcome",
        border_style="blue"
    ))

    while True:
        try:
            user_input = console.input("\n[bold cyan]You:[/bold cyan] ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["/quit", "/exit", "/q"]:
                console.print("[yellow]Goodbye![/yellow]")
                break

            if user_input.lower() == "/clear":
                rag.clear_history()
                console.print("[green]Chat history cleared.[/green]")
                continue

            if user_input.lower().startswith("/backend "):
                new_backend = user_input[9:].strip()
                try:
                    rag.llm_router.set_backend(new_backend)
                    console.print(f"[green]Switched to {new_backend}[/green]")
                except ValueError as e:
                    console.print(f"[red]{e}[/red]")
                continue

            if user_input.lower().startswith("/email "):
                job = user_input[7:].strip()
                with console.status("[bold green]Drafting..."):
                    response = asyncio.run(rag.draft_email(job))
                console.print(Panel(response, title="Draft Email", border_style="blue"))
                continue

            if user_input.lower().startswith("/tailor "):
                job = user_input[8:].strip()
                with console.status("[bold green]Analyzing..."):
                    response = asyncio.run(rag.tailor_resume(job))
                console.print(Panel(Markdown(response), title="Suggestions", border_style="yellow"))
                continue

            if user_input.lower().startswith("/search "):
                query = user_input[8:].strip()
                results = rag.retriever.search(query, n_results=3)
                for r in results:
                    console.print(f"[cyan]{r['metadata'].get('section')}:[/cyan] {r['content'][:100]}...")
                continue

            if user_input.lower().startswith("/web "):
                query = user_input[5:].strip()
                ws = WebSearch()
                results = ws.search(query, max_results=3)
                for r in results:
                    console.print(f"[cyan]{r['title']}[/cyan]\n  {r['snippet'][:100]}...")
                continue

            # Regular chat
            with console.status("[bold green]Thinking..."):
                response = asyncio.run(rag.chat(user_input))

            console.print(Panel(Markdown(response), title="Assistant", border_style="green"))

        except KeyboardInterrupt:
            console.print("\n[yellow]Use /quit to exit[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    app()
