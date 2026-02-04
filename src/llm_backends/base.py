"""Base LLM interface for all backends"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, AsyncGenerator
from enum import Enum


class LLMType(str, Enum):
    """Supported LLM types"""
    GROQ = "groq"
    OLLAMA = "ollama"
    OPENAI = "openai"
    CHATGPT_WEB = "chatgpt_web"
    GEMINI = "gemini"
    CLAUDE = "claude"
    XAI = "xai"
    HUGGINGFACE = "huggingface"
    DEEPSEEK = "deepseek"
    OPENROUTER = "openrouter"


@dataclass
class LLMResponse:
    """Standardized response from any LLM backend"""
    content: str
    model: str
    backend: LLMType
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None


@dataclass
class Message:
    """Chat message format"""
    role: str  # "system", "user", "assistant"
    content: str


class BaseLLM(ABC):
    """Abstract base class for all LLM backends"""

    def __init__(self, model: str):
        self.model = model
        self._is_available: Optional[bool] = None

    @property
    @abstractmethod
    def backend_type(self) -> LLMType:
        """Return the backend type"""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this backend is available (API key set, service running, etc.)"""
        pass

    @abstractmethod
    async def generate(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a response from the LLM"""
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream a response from the LLM"""
        pass

    def chat(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[Message]] = None,
        **kwargs
    ) -> LLMResponse:
        """Synchronous chat helper"""
        import asyncio
        return asyncio.run(self.achat(user_message, system_prompt, history, **kwargs))

    async def achat(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[Message]] = None,
        **kwargs
    ) -> LLMResponse:
        """Async chat helper"""
        messages = []

        if system_prompt:
            messages.append(Message(role="system", content=system_prompt))

        if history:
            messages.extend(history)

        messages.append(Message(role="user", content=user_message))

        return await self.generate(messages, **kwargs)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model}, available={self.is_available})"
