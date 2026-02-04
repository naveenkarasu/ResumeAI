"""
LLM Router - Unified interface to switch between LLM backends
"""

from typing import Optional, List, Dict, AsyncGenerator
from .base import BaseLLM, LLMType, LLMResponse, Message
from .groq_backend import GroqLLM
from .ollama_backend import OllamaLLM
from .openai_backend import OpenAILLM
from .chatgpt_web_backend import ChatGPTWebLLM
from .gemini_backend import GeminiLLM
from .claude_backend import ClaudeLLM

import sys
sys.path.append(str(__file__).rsplit("src", 1)[0])
from config.settings import settings


class LLMRouter:
    """
    Router to manage and switch between multiple LLM backends.

    Usage:
        router = LLMRouter()
        router.set_backend("groq")  # Switch to Groq
        response = router.chat("Hello!")

        # Or use specific backend directly
        response = router.chat("Hello!", backend="ollama")
    """

    def __init__(self, default_backend: Optional[str] = None):
        self.default_backend = default_backend or settings.default_llm
        self._backends: Dict[str, BaseLLM] = {}
        self._initialize_backends()

    def _initialize_backends(self):
        """Initialize all available backends"""
        # Groq (FREE)
        self._backends["groq"] = GroqLLM()

        # Ollama (LOCAL)
        self._backends["ollama"] = OllamaLLM()

        # OpenAI (PAID)
        self._backends["openai"] = OpenAILLM()

        # ChatGPT Web (RISKY)
        self._backends["chatgpt_web"] = ChatGPTWebLLM()

        # Gemini (Google AI)
        self._backends["gemini"] = GeminiLLM()

        # Claude (Anthropic)
        self._backends["claude"] = ClaudeLLM()

    def get_backend(self, name: Optional[str] = None) -> BaseLLM:
        """Get a specific backend or the default"""
        name = name or self.default_backend
        if name not in self._backends:
            raise ValueError(f"Unknown backend: {name}. Available: {list(self._backends.keys())}")
        return self._backends[name]

    def set_backend(self, name: str):
        """Set the default backend"""
        if name not in self._backends:
            raise ValueError(f"Unknown backend: {name}. Available: {list(self._backends.keys())}")
        self.default_backend = name

    def list_backends(self) -> Dict[str, Dict]:
        """List all backends with their status"""
        return {
            name: {
                "type": backend.backend_type.value,
                "model": backend.model,
                "available": backend.is_available,
                "is_default": name == self.default_backend
            }
            for name, backend in self._backends.items()
        }

    def get_available_backends(self) -> List[str]:
        """Get list of available (configured) backends"""
        return [name for name, backend in self._backends.items() if backend.is_available]

    def chat(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[Message]] = None,
        backend: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Synchronous chat with automatic backend selection"""
        import asyncio
        return asyncio.run(self.achat(user_message, system_prompt, history, backend, **kwargs))

    async def achat(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[Message]] = None,
        backend: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Async chat with automatic backend selection"""
        llm = self.get_backend(backend)

        if not llm.is_available:
            # Try to find an available backend
            available = self.get_available_backends()
            if not available:
                raise ValueError(
                    "No LLM backends available. Please configure at least one:\n"
                    "- Groq: Set GROQ_API_KEY in .env (FREE)\n"
                    "- Ollama: Install and run Ollama (FREE, LOCAL)\n"
                    "- OpenAI: Set OPENAI_API_KEY in .env (PAID)\n"
                    "- Gemini: Set GEMINI_API_KEY in .env (FREE tier available)\n"
                    "- Claude: Set CLAUDE_API_KEY in .env (PAID)\n"
                    "- ChatGPT Web: Set CHATGPT_EMAIL and CHATGPT_PASSWORD (RISKY)"
                )

            # Use first available
            llm = self.get_backend(available[0])
            print(f"Note: Switched to {available[0]} (requested backend not available)")

        return await llm.achat(user_message, system_prompt, history, **kwargs)

    async def generate(
        self,
        messages: List[Message],
        backend: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response from messages"""
        llm = self.get_backend(backend)
        return await llm.generate(messages, **kwargs)

    async def stream(
        self,
        messages: List[Message],
        backend: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream response from messages"""
        llm = self.get_backend(backend)
        async for chunk in llm.stream(messages, **kwargs):
            yield chunk

    def __repr__(self) -> str:
        backends_info = ", ".join([
            f"{name}={'✓' if b.is_available else '✗'}"
            for name, b in self._backends.items()
        ])
        return f"LLMRouter(default={self.default_backend}, backends=[{backends_info}])"


# Convenience function for quick usage
def get_llm(backend: Optional[str] = None) -> BaseLLM:
    """Get an LLM backend instance"""
    router = LLMRouter()
    return router.get_backend(backend)
