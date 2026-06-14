import asyncio
import os

from anthropic import Anthropic

from .base import OPTIMIZER_SYSTEM_PROMPT, OptimizerBase


class ClaudeOptimizer(OptimizerBase):
    """Prompt optimizer using Anthropic Claude API."""

    def __init__(self) -> None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

        base_url = os.getenv("ANTHROPIC_BASE_URL")
        self._client = Anthropic(
            api_key=api_key,
            **(dict(base_url=base_url) if base_url else {}),
        )
        self._model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    @property
    def provider_name(self) -> str:
        return f"Claude ({self._model})"

    async def optimize(self, text: str) -> str:
        # Anthropic SDK is synchronous; run in thread pool for async compatibility.
        return await asyncio.to_thread(self._optimize_sync, text)

    def _optimize_sync(self, text: str) -> str:
        message = self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            system=OPTIMIZER_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": text}],
        )
        return message.content[0].text
