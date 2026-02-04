"""HuggingFace Inference API Backend - FREE tier available"""

from typing import Optional, List, AsyncGenerator
from .base import BaseLLM, LLMType, LLMResponse, Message

import sys
sys.path.append(str(__file__).rsplit("src", 1)[0])
from config.settings import settings


class HuggingFaceLLM(BaseLLM):
    """
    HuggingFace Inference API Backend

    FREE tier available with rate limits (~1000 requests/day).
    Access to thousands of open-source models.

    Get API token: https://huggingface.co/settings/tokens

    Popular models:
    - Qwen/Qwen2.5-72B-Instruct (best quality)
    - meta-llama/Llama-3.1-8B-Instruct
    - mistralai/Mistral-7B-Instruct-v0.3
    - microsoft/Phi-3-mini-4k-instruct
    """

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        model = model or settings.huggingface_model
        super().__init__(model)
        self.api_key = api_key or settings.huggingface_api_key
        self._client = None

    @property
    def backend_type(self) -> LLMType:
        return LLMType.HUGGINGFACE

    @property
    def is_available(self) -> bool:
        if self._is_available is not None:
            return self._is_available
        self._is_available = bool(self.api_key)
        return self._is_available

    def _get_client(self):
        if self._client is None:
            from huggingface_hub import InferenceClient
            self._client = InferenceClient(token=self.api_key)
        return self._client

    def _format_messages(self, messages: List[Message]) -> List[dict]:
        """Convert messages to HuggingFace chat format"""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

    async def generate(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response using HuggingFace Inference API"""
        if not self.is_available:
            raise ValueError("HuggingFace API token not configured. Set HUGGINGFACE_API_KEY in .env")

        client = self._get_client()
        hf_messages = self._format_messages(messages)

        response = client.chat_completion(
            model=self.model,
            messages=hf_messages,
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
        """Stream response using HuggingFace Inference API"""
        if not self.is_available:
            raise ValueError("HuggingFace API token not configured. Set HUGGINGFACE_API_KEY in .env")

        client = self._get_client()
        hf_messages = self._format_messages(messages)

        stream = client.chat_completion(
            model=self.model,
            messages=hf_messages,
            temperature=temperature,
            max_tokens=max_tokens or 4096,
            stream=True,
            **kwargs
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
