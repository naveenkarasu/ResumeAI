"""LLM Backend implementations for Resume RAG Assistant"""

from .base import BaseLLM, LLMResponse, Message, LLMType
from .router import LLMRouter
from .groq_backend import GroqLLM
from .ollama_backend import OllamaLLM
from .openai_backend import OpenAILLM
from .chatgpt_web_backend import ChatGPTWebLLM
from .gemini_backend import GeminiLLM
from .claude_backend import ClaudeLLM
from .xai_backend import XaiLLM
from .huggingface_backend import HuggingFaceLLM
from .deepseek_backend import DeepSeekLLM
from .openrouter_backend import OpenRouterLLM

# Backend registry
BACKENDS = {
    "groq": GroqLLM,
    "ollama": OllamaLLM,
    "openai": OpenAILLM,
    "chatgpt": ChatGPTWebLLM,
    "gemini": GeminiLLM,
    "claude": ClaudeLLM,
    "xai": XaiLLM,
    "huggingface": HuggingFaceLLM,
    "deepseek": DeepSeekLLM,
    "openrouter": OpenRouterLLM,
}


def get_backend(name: str) -> BaseLLM:
    """Get an LLM backend by name.

    Args:
        name: Backend name (groq, ollama, openai, chatgpt, gemini, claude)

    Returns:
        Initialized LLM backend instance

    Raises:
        ValueError: If backend name is not recognized
    """
    name = name.lower()
    if name not in BACKENDS:
        raise ValueError(f"Unknown backend: {name}. Available: {list(BACKENDS.keys())}")
    return BACKENDS[name]()


__all__ = [
    "BaseLLM",
    "LLMResponse",
    "Message",
    "LLMType",
    "LLMRouter",
    "GroqLLM",
    "OllamaLLM",
    "OpenAILLM",
    "ChatGPTWebLLM",
    "GeminiLLM",
    "ClaudeLLM",
    "XaiLLM",
    "HuggingFaceLLM",
    "DeepSeekLLM",
    "OpenRouterLLM",
    "BACKENDS",
    "get_backend",
]
