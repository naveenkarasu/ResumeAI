"""DeepSeek LLM Backend - FREE tier available, excellent for coding"""

from typing import Optional, List, AsyncGenerator
from .base import BaseLLM, LLMType, LLMResponse, Message

import sys
sys.path.append(str(__file__).rsplit("src", 1)[0])
from config.settings import settings


class DeepSeekLLM(BaseLLM):
    """
    DeepSeek LLM Backend

    FREE tier available with generous limits.
    Excellent for coding and reasoning tasks.
    Uses OpenAI-compatible API.

    Get API key: https://platform.deepseek.com/api_keys

    Models:
    - deepseek-chat (general purpose)
    - deepseek-coder (coding specialized)
    - deepseek-reasoner (reasoning/math)
    """

    DEEPSEEK_BASE_URL = "https://api.deepseek.com"

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        model = model or settings.deepseek_model
        super().__init__(model)
        self.api_key = api_key or settings.deepseek_api_key
        self._client = None

    @property
    def backend_type(self) -> LLMType:
        return LLMType.DEEPSEEK

    @property
    def is_available(self) -> bool:
        if self._is_available is not None:
            return self._is_available
        self._is_available = bool(self.api_key)
        return self._is_available

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.DEEPSEEK_BASE_URL
            )
        return self._client

    async def generate(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response using DeepSeek"""
        if not self.is_available:
            raise ValueError("DeepSeek API key not configured. Set DEEPSEEK_API_KEY in .env")

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
        """Stream response using DeepSeek"""
        if not self.is_available:
            raise ValueError("DeepSeek API key not configured. Set DEEPSEEK_API_KEY in .env")

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
