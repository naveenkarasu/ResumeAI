"""Ollama LLM Backend - FREE, runs locally"""

from typing import Optional, List, AsyncGenerator
from .base import BaseLLM, LLMType, LLMResponse, Message

import sys
sys.path.append(str(__file__).rsplit("src", 1)[0])
from config.settings import settings


class OllamaLLM(BaseLLM):
    """
    Ollama LLM Backend

    100% FREE, runs locally on your machine.
    Requires Ollama to be installed and running.

    Install: https://ollama.ai/download
    Pull model: ollama pull llama3.1
    """

    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        model = model or settings.ollama_model
        super().__init__(model)
        self.base_url = base_url or settings.ollama_base_url
        self._client = None

    @property
    def backend_type(self) -> LLMType:
        return LLMType.OLLAMA

    @property
    def is_available(self) -> bool:
        if self._is_available is not None:
            return self._is_available

        try:
            import httpx
            response = httpx.get(f"{self.base_url}/api/tags", timeout=5.0)
            self._is_available = response.status_code == 200
        except Exception:
            self._is_available = False

        return self._is_available

    def _get_client(self):
        if self._client is None:
            import ollama
            self._client = ollama.Client(host=self.base_url)
        return self._client

    async def generate(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response using Ollama"""
        if not self.is_available:
            raise ValueError(
                f"Ollama not available at {self.base_url}. "
                "Make sure Ollama is installed and running."
            )

        client = self._get_client()

        # Convert messages to Ollama format
        ollama_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        options = {"temperature": temperature}
        if max_tokens:
            options["num_predict"] = max_tokens

        response = client.chat(
            model=self.model,
            messages=ollama_messages,
            options=options,
            **kwargs
        )

        return LLMResponse(
            content=response["message"]["content"],
            model=self.model,
            backend=self.backend_type,
            tokens_used=response.get("eval_count"),
            finish_reason="stop",
            raw_response=response
        )

    async def stream(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream response using Ollama"""
        if not self.is_available:
            raise ValueError(
                f"Ollama not available at {self.base_url}. "
                "Make sure Ollama is installed and running."
            )

        client = self._get_client()

        ollama_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        options = {"temperature": temperature}
        if max_tokens:
            options["num_predict"] = max_tokens

        stream = client.chat(
            model=self.model,
            messages=ollama_messages,
            options=options,
            stream=True,
            **kwargs
        )

        for chunk in stream:
            if chunk["message"]["content"]:
                yield chunk["message"]["content"]

    def list_models(self) -> List[str]:
        """List available models in Ollama"""
        if not self.is_available:
            return []

        client = self._get_client()
        response = client.list()
        return [model["name"] for model in response.get("models", [])]

    def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama registry"""
        try:
            client = self._get_client()
            client.pull(model_name)
            return True
        except Exception as e:
            print(f"Failed to pull model {model_name}: {e}")
            return False
