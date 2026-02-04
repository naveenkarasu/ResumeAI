"""Gemini LLM Backend - Google AI"""

from typing import Optional, List, AsyncGenerator
from .base import BaseLLM, LLMType, LLMResponse, Message

import sys
sys.path.append(str(__file__).rsplit("src", 1)[0])
from config.settings import settings


class GeminiLLM(BaseLLM):
    """
    Google Gemini LLM Backend

    Supports:
    - gemini-1.5-pro: Best quality, multimodal
    - gemini-1.5-flash: Fast and efficient
    - gemini-pro: Previous generation

    Get API key: https://aistudio.google.com/app/apikey
    """

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        model = model or settings.gemini_model
        super().__init__(model)
        self.api_key = api_key or settings.gemini_api_key
        self._client = None

    @property
    def backend_type(self) -> LLMType:
        return LLMType.GEMINI

    @property
    def is_available(self) -> bool:
        if self._is_available is not None:
            return self._is_available
        self._is_available = bool(self.api_key)
        return self._is_available

    def _get_client(self):
        """Get configured Gemini client (configures API only once)"""
        if self._client is None:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._genai = genai  # Cache the module reference
            self._client = True  # Mark as configured
        return self._genai

    def _convert_messages(self, messages: List[Message]) -> tuple:
        """Convert messages to Gemini format (history + current message)"""
        history = []
        system_instruction = None
        current_message = None

        for msg in messages:
            if msg.role == "system":
                system_instruction = msg.content
            elif msg.role == "user":
                current_message = msg.content
                if history and history[-1]["role"] == "user":
                    # Gemini requires alternating roles, merge consecutive user messages
                    history[-1]["parts"][0] += "\n" + msg.content
                else:
                    history.append({"role": "user", "parts": [msg.content]})
            elif msg.role == "assistant":
                history.append({"role": "model", "parts": [msg.content]})

        # Remove the last user message from history (it will be the current input)
        if history and history[-1]["role"] == "user":
            current_message = history.pop()["parts"][0]

        return history, current_message, system_instruction

    async def generate(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response using Gemini"""
        if not self.is_available:
            raise ValueError("Gemini API key not configured. Set GEMINI_API_KEY in .env")

        # Use cached client (configures API only once)
        genai = self._get_client()

        history, current_message, system_instruction = self._convert_messages(messages)

        # Create model with optional system instruction
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens or 4096,
        )

        model_kwargs = {"generation_config": generation_config}
        if system_instruction:
            model_kwargs["system_instruction"] = system_instruction

        model = genai.GenerativeModel(self.model, **model_kwargs)

        # Start chat with history if available
        chat = model.start_chat(history=history if history else [])

        # Generate response
        response = chat.send_message(current_message or "Hello")

        # Extract token counts if available
        tokens_used = None
        if hasattr(response, 'usage_metadata'):
            tokens_used = (
                response.usage_metadata.prompt_token_count +
                response.usage_metadata.candidates_token_count
            )

        return LLMResponse(
            content=response.text,
            model=self.model,
            backend=self.backend_type,
            tokens_used=tokens_used,
            finish_reason=response.candidates[0].finish_reason.name if response.candidates else None,
            raw_response=None
        )

    async def stream(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream response using Gemini"""
        if not self.is_available:
            raise ValueError("Gemini API key not configured. Set GEMINI_API_KEY in .env")

        # Use cached client (configures API only once)
        genai = self._get_client()

        history, current_message, system_instruction = self._convert_messages(messages)

        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens or 4096,
        )

        model_kwargs = {"generation_config": generation_config}
        if system_instruction:
            model_kwargs["system_instruction"] = system_instruction

        model = genai.GenerativeModel(self.model, **model_kwargs)
        chat = model.start_chat(history=history if history else [])

        response = chat.send_message(current_message or "Hello", stream=True)

        for chunk in response:
            if chunk.text:
                yield chunk.text
