"""Claude LLM Backend - Anthropic AI"""

from typing import Optional, List, AsyncGenerator
from .base import BaseLLM, LLMType, LLMResponse, Message

import sys
sys.path.append(str(__file__).rsplit("src", 1)[0])
from config.settings import settings


class ClaudeLLM(BaseLLM):
    """
    Anthropic Claude LLM Backend

    Supports:
    - claude-3-5-sonnet-20241022: Best balance of intelligence and speed
    - claude-3-opus-20240229: Most capable model
    - claude-3-haiku-20240307: Fastest, most economical

    Get API key: https://console.anthropic.com/
    """

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        model = model or settings.claude_model
        super().__init__(model)
        self.api_key = api_key or settings.claude_api_key
        self._client = None

    @property
    def backend_type(self) -> LLMType:
        return LLMType.CLAUDE

    @property
    def is_available(self) -> bool:
        if self._is_available is not None:
            return self._is_available
        self._is_available = bool(self.api_key)
        return self._is_available

    def _get_client(self):
        if self._client is None:
            from anthropic import Anthropic
            self._client = Anthropic(api_key=self.api_key)
        return self._client

    async def generate(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response using Claude"""
        if not self.is_available:
            raise ValueError("Claude API key not configured. Set CLAUDE_API_KEY in .env")

        client = self._get_client()

        # Separate system message from conversation
        system_prompt = None
        claude_messages = []

        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
            else:
                claude_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        # Build request kwargs
        request_kwargs = {
            "model": self.model,
            "messages": claude_messages,
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
        }

        if system_prompt:
            request_kwargs["system"] = system_prompt

        response = client.messages.create(**request_kwargs)

        return LLMResponse(
            content=response.content[0].text,
            model=self.model,
            backend=self.backend_type,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens,
            finish_reason=response.stop_reason,
            raw_response=response.model_dump() if hasattr(response, 'model_dump') else None
        )

    async def stream(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream response using Claude"""
        if not self.is_available:
            raise ValueError("Claude API key not configured. Set CLAUDE_API_KEY in .env")

        client = self._get_client()

        # Separate system message from conversation
        system_prompt = None
        claude_messages = []

        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
            else:
                claude_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        request_kwargs = {
            "model": self.model,
            "messages": claude_messages,
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
        }

        if system_prompt:
            request_kwargs["system"] = system_prompt

        with client.messages.stream(**request_kwargs) as stream:
            for text in stream.text_stream:
                yield text
