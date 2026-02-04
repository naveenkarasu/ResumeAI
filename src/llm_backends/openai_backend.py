"""OpenAI LLM Backend - PAID, best quality"""

from typing import Optional, List, AsyncGenerator
from .base import BaseLLM, LLMType, LLMResponse, Message

import sys
sys.path.append(str(__file__).rsplit("src", 1)[0])
from config.settings import settings


class OpenAILLM(BaseLLM):
    """
    OpenAI LLM Backend

    PAID - Pay per token usage.
    Best quality models (GPT-4, GPT-4 Turbo).

    Get API key: https://platform.openai.com/api-keys
    """

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        model = model or settings.openai_model
        super().__init__(model)
        self.api_key = api_key or settings.openai_api_key
        self._client = None

    @property
    def backend_type(self) -> LLMType:
        return LLMType.OPENAI

    @property
    def is_available(self) -> bool:
        if self._is_available is not None:
            return self._is_available
        self._is_available = bool(self.api_key)
        return self._is_available

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    async def generate(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response using OpenAI"""
        if not self.is_available:
            raise ValueError("OpenAI API key not configured. Set OPENAI_API_KEY in .env")

        client = self._get_client()

        # Convert messages to OpenAI format
        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        response = client.chat.completions.create(
            model=self.model,
            messages=openai_messages,
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
        """Stream response using OpenAI"""
        if not self.is_available:
            raise ValueError("OpenAI API key not configured. Set OPENAI_API_KEY in .env")

        client = self._get_client()

        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        stream = client.chat.completions.create(
            model=self.model,
            messages=openai_messages,
            temperature=temperature,
            max_tokens=max_tokens or 4096,
            stream=True,
            **kwargs
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
