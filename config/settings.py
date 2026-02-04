"""
Configuration settings for ResumeAI
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, Literal
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Project paths
    project_root: Path = Path(__file__).parent.parent
    data_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "data")
    resumes_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "data" / "resumes")
    chroma_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "data" / "chroma_db")

    # LLM Settings
    default_llm: Literal["groq", "ollama", "openai", "chatgpt_web", "gemini", "claude", "xai", "huggingface", "deepseek", "openrouter"] = "groq"

    # Groq Settings (FREE)
    groq_api_key: Optional[str] = None
    groq_model: str = "llama-3.3-70b-versatile"

    # Ollama Settings (LOCAL)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    # OpenAI Settings (PAID)
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4-turbo-preview"

    # ChatGPT Web Settings (RISKY)
    chatgpt_email: Optional[str] = None
    chatgpt_password: Optional[str] = None
    chatgpt_session_token: Optional[str] = None  # Alternative to email/password

    # Gemini Settings (Google AI)
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-1.5-pro"

    # Claude Settings (Anthropic)
    claude_api_key: Optional[str] = None
    claude_model: str = "claude-3-5-sonnet-20241022"

    # xAI Grok Settings (FREE tier available)
    xai_api_key: Optional[str] = None
    xai_model: str = "grok-2-latest"

    # HuggingFace Settings (FREE tier available)
    huggingface_api_key: Optional[str] = None
    huggingface_model: str = "Qwen/Qwen2.5-72B-Instruct"

    # DeepSeek Settings (FREE tier available)
    deepseek_api_key: Optional[str] = None
    deepseek_model: str = "deepseek-chat"

    # OpenRouter Settings (aggregator - access 100+ models)
    openrouter_api_key: Optional[str] = None
    openrouter_model: str = "meta-llama/llama-3.1-8b-instruct:free"

    # Embedding Settings
    embedding_model: str = "all-MiniLM-L6-v2"  # Free, local

    # ChromaDB Settings
    chroma_collection_name: str = "resumes"

    # Web Search Settings
    web_search_enabled: bool = True
    web_search_max_results: int = 5

    # UI Settings
    streamlit_port: int = 8501

    # Rate Limiting
    groq_requests_per_minute: int = 30

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings instance
settings = Settings()
