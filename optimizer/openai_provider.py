import os

from openai import AsyncOpenAI

from .base import OPTIMIZER_SYSTEM_PROMPT, OptimizerBase


class OpenAIOptimizer(OptimizerBase):
    """Generic OpenAI-compatible provider.

    Works with any OpenAI-compatible API (OpenAI, DeepSeek, ModelScope, etc.).
    Configure via constructor params or environment variables.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        label: str = "OpenAI",
    ) -> None:
        self._label = label
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        if not self._api_key:
            raise ValueError(f"API key not provided for {label}")

        self._base_url = base_url or os.getenv("OPENAI_BASE_URL") or None
        self._model = model or os.getenv("OPENAI_MODEL", "gpt-4o")

        self._client = AsyncOpenAI(
            api_key=self._api_key,
            **(dict(base_url=self._base_url) if self._base_url else {}),
        )

    @property
    def provider_name(self) -> str:
        return f"{self._label} ({self._model})"

    async def optimize(self, text: str) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=2048,
            messages=[
                {"role": "system", "content": OPTIMIZER_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        )
        return response.choices[0].message.content or ""
