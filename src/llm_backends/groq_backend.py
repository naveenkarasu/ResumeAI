"""Groq LLM Backend - FREE tier available"""

from typing import Optional, List, AsyncGenerator
from .base import BaseLLM, LLMType, LLMResponse, Message

import sys
sys.path.append(str(__file__).rsplit("src", 1)[0])
from config.settings import settings


class GroqLLM(BaseLLM):
    """
    Groq LLM Backend

    FREE tier with rate limits:
    - LLaMA 3.1 70B: 30 requests/min, 6000 tokens/min
    - Very fast inference (fastest available)

    Get API key: https://console.groq.com/keys
    """

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        model = model or settings.groq_model
        super().__init__(model)
        self.api_key = api_key or settings.groq_api_key
        self._client = None

    @property
    def backend_type(self) -> LLMType:
        return LLMType.GROQ

    @property
    def is_available(self) -> bool:
        if self._is_available is not None:
            return self._is_available
        self._is_available = bool(self.api_key)
        return self._is_available

    def _get_client(self):
        if self._client is None:
            from groq import Groq
            self._client = Groq(api_key=self.api_key)
        return self._client

    async def generate(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response using Groq"""
        if not self.is_available:
            raise ValueError("Groq API key not configured. Set GROQ_API_KEY in .env")

        client = self._get_client()

        # Convert messages to Groq format
        groq_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        response = client.chat.completions.create(
            model=self.model,
            messages=groq_messages,
            temperature=temperature,
            max_tokens=max_tokens or 4096,
            **kwargs
        )

        return LLMResponse(
            content=response.choices[0].message.content,
            model=self.model,
            backend=self.backend_type,
            tokens_used=response.usage.total_tokens if response.usage else None,
            finish_reason=response.choices[0].finish_reason,
            raw_response=response.model_dump() if hasattr(response, 'model_dump') else None
        )

    async def stream(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream response using Groq"""
        if not self.is_available:
            raise ValueError("Groq API key not configured. Set GROQ_API_KEY in .env")

        client = self._get_client()

        groq_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        stream = client.chat.completions.create(
            model=self.model,
            messages=groq_messages,
            temperature=temperature,
            max_tokens=max_tokens or 4096,
            stream=True,
            **kwargs
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
