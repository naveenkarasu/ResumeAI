"""
ChatGPT Web LLM Backend - RISKY, uses browser automation

WARNING: This backend automates the ChatGPT web interface.
- May violate OpenAI's Terms of Service
- Could result in account suspension/ban
- Unreliable - UI changes can break it
- Use at your own risk!
"""

from typing import Optional, List, AsyncGenerator
import asyncio
import json
from pathlib import Path
from .base import BaseLLM, LLMType, LLMResponse, Message

import sys
sys.path.append(str(__file__).rsplit("src", 1)[0])
from config.settings import settings


class ChatGPTWebLLM(BaseLLM):
    """
    ChatGPT Web Backend using Playwright browser automation

    ⚠️  WARNING: RISKY - USE AT YOUR OWN RISK ⚠️

    This backend:
    - Automates the ChatGPT web interface
    - May violate OpenAI ToS
    - Can get your account banned
    - Is unreliable (UI changes break it)

    Only use if you accept these risks!
    """

    def __init__(
        self,
        email: Optional[str] = None,
        password: Optional[str] = None,
        session_token: Optional[str] = None
    ):
        super().__init__(model="chatgpt-web")
        self.email = email or settings.chatgpt_email
        self.password = password or settings.chatgpt_password
        self.session_token = session_token or settings.chatgpt_session_token
        self._browser = None
        self._page = None
        self._logged_in = False
        self._session_file = Path(settings.data_dir) / "chatgpt_session.json"

    @property
    def backend_type(self) -> LLMType:
        return LLMType.CHATGPT_WEB

    @property
    def is_available(self) -> bool:
        if self._is_available is not None:
            return self._is_available
        # Available if we have credentials or a saved session
        self._is_available = bool(
            (self.email and self.password) or
            self.session_token or
            self._session_file.exists()
        )
        return self._is_available

    async def _init_browser(self):
        """Initialize Playwright browser"""
        if self._browser is not None:
            return

        from playwright.async_api import async_playwright

        playwright = await async_playwright().start()
        self._browser = await playwright.chromium.launch(
            headless=True,  # Set to False to see the browser
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ]
        )

        context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # Load saved session if exists
        if self._session_file.exists():
            try:
                with open(self._session_file, "r") as f:
                    cookies = json.load(f)
                await context.add_cookies(cookies)
            except Exception:
                pass

        self._page = await context.new_page()

    async def _login(self):
        """Login to ChatGPT"""
        if self._logged_in:
            return

        await self._init_browser()

        # Navigate to ChatGPT
        await self._page.goto("https://chat.openai.com/", wait_until="networkidle")
        await asyncio.sleep(2)

        # Check if already logged in
        if "chat" in self._page.url.lower():
            self._logged_in = True
            await self._save_session()
            return

        # Click login button
        try:
            login_btn = await self._page.wait_for_selector(
                "button:has-text('Log in')",
                timeout=10000
            )
            await login_btn.click()
            await asyncio.sleep(2)
        except Exception:
            pass

        # Enter email
        if self.email:
            email_input = await self._page.wait_for_selector(
                "input[name='username'], input[type='email']",
                timeout=10000
            )
            await email_input.fill(self.email)
            await self._page.click("button[type='submit'], button:has-text('Continue')")
            await asyncio.sleep(2)

            # Enter password
            if self.password:
                password_input = await self._page.wait_for_selector(
                    "input[name='password'], input[type='password']",
                    timeout=10000
                )
                await password_input.fill(self.password)
                await self._page.click("button[type='submit'], button:has-text('Continue')")
                await asyncio.sleep(5)

        # Wait for chat interface
        await self._page.wait_for_selector(
            "textarea, [contenteditable='true']",
            timeout=30000
        )

        self._logged_in = True
        await self._save_session()

    async def _save_session(self):
        """Save session cookies for reuse"""
        if self._page:
            cookies = await self._page.context.cookies()
            self._session_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._session_file, "w") as f:
                json.dump(cookies, f)

    async def _send_message(self, message: str) -> str:
        """Send a message and get response"""
        await self._login()

        # Find the input textarea
        textarea = await self._page.wait_for_selector(
            "textarea, [contenteditable='true']",
            timeout=10000
        )

        # Clear and type message
        await textarea.fill(message)
        await asyncio.sleep(0.5)

        # Click send button or press Enter
        try:
            send_btn = await self._page.query_selector(
                "button[data-testid='send-button'], button:has-text('Send')"
            )
            if send_btn:
                await send_btn.click()
            else:
                await textarea.press("Enter")
        except Exception:
            await textarea.press("Enter")

        # Wait for response
        await asyncio.sleep(2)

        # Wait for response to complete (stop generating)
        max_wait = 120  # Max 2 minutes
        for _ in range(max_wait):
            # Check if still generating
            generating = await self._page.query_selector(
                "button:has-text('Stop generating'), .result-streaming"
            )
            if not generating:
                break
            await asyncio.sleep(1)

        # Get the last response
        responses = await self._page.query_selector_all(
            "[data-message-author-role='assistant'] .markdown, .agent-turn .markdown"
        )

        if responses:
            last_response = responses[-1]
            return await last_response.inner_text()

        return "Failed to get response"

    async def generate(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response using ChatGPT Web"""
        if not self.is_available:
            raise ValueError(
                "ChatGPT Web credentials not configured. "
                "Set CHATGPT_EMAIL and CHATGPT_PASSWORD in .env"
            )

        # Build conversation context
        # Note: Web interface doesn't support system prompts directly
        # We prepend it to the first user message
        full_message_parts = []

        for msg in messages:
            if msg.role == "system":
                full_message_parts.insert(0, f"[System Instructions: {msg.content}]\n\n")
            elif msg.role == "user":
                full_message_parts.append(f"User: {msg.content}\n")
            elif msg.role == "assistant":
                full_message_parts.append(f"Assistant: {msg.content}\n")

        full_message = "".join(full_message_parts)

        # For single turn, just send the last user message
        last_user_msg = None
        for msg in reversed(messages):
            if msg.role == "user":
                last_user_msg = msg.content
                break

        if last_user_msg is None:
            last_user_msg = full_message

        try:
            response_text = await self._send_message(last_user_msg)

            return LLMResponse(
                content=response_text,
                model="chatgpt-web",
                backend=self.backend_type,
                tokens_used=None,  # Can't track tokens via web
                finish_reason="stop",
                raw_response=None
            )
        except Exception as e:
            return LLMResponse(
                content=f"Error: {str(e)}",
                model="chatgpt-web",
                backend=self.backend_type,
                tokens_used=None,
                finish_reason="error",
                raw_response={"error": str(e)}
            )

    async def stream(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream not fully supported - returns complete response"""
        response = await self.generate(messages, temperature, max_tokens, **kwargs)
        yield response.content

    async def close(self):
        """Close browser"""
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._page = None
            self._logged_in = False

    def __del__(self):
        """Cleanup on deletion"""
        if self._browser:
            asyncio.run(self.close())
