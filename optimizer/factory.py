import os
from dataclasses import dataclass, field

from .base import OptimizerBase
from .claude_provider import ClaudeOptimizer
from .openai_provider import OpenAIOptimizer


@dataclass
class ProviderInfo:
    key: str
    label: str
    configured: bool


@dataclass
class _ProviderDef:
    """Internal definition for a provider."""
    label: str
    env_prefix: str = ""         # e.g. "OPENAI" → reads OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
    cls: type = OpenAIOptimizer  # which class to instantiate


# Register all providers here. To add a new OpenAI-compatible provider,
# just add a row — no new code needed.
_providers: dict[str, _ProviderDef] = {
    "claude": _ProviderDef(
        label="Claude (Anthropic)",
        cls=ClaudeOptimizer,
        env_prefix="ANTHROPIC",
    ),
    "modelscope": _ProviderDef(
        label="ModelScope (Step-3.7-Flash)",
        env_prefix="MODELSCOPE",
    ),
    "deepseek": _ProviderDef(
        label="DeepSeek (V4-Flash)",
        env_prefix="DEEPSEEK",
    ),
}


def list_providers() -> list[ProviderInfo]:
    """Return all registered providers and whether they are configured."""
    result = []
    for key, pdef in _providers.items():
        api_key_env = f"{pdef.env_prefix}_API_KEY" if pdef.env_prefix else "ANTHROPIC_API_KEY"
        result.append(ProviderInfo(
            key=key,
            label=pdef.label,
            configured=bool(os.getenv(api_key_env)),
        ))
    return result


def get_optimizer(provider: str | None = None) -> OptimizerBase:
    """Factory function to create an optimizer instance.

    Args:
        provider: Provider key (e.g. 'claude', 'openai', 'deepseek').
                  If None, reads LLM_PROVIDER env var.

    Raises:
        ValueError: If the provider is unknown or required API key is missing.
    """
    if provider is None:
        provider = os.getenv("LLM_PROVIDER", "claude")

    provider = provider.lower().strip()
    if provider not in _providers:
        raise ValueError(
            f"Unknown LLM provider: '{provider}'. "
            f"Supported: {', '.join(_providers.keys())}"
        )

    pdef = _providers[provider]

    if pdef.cls is ClaudeOptimizer:
        return ClaudeOptimizer()

    # OpenAI-compatible: read config from the provider's env prefix
    prefix = pdef.env_prefix
    api_key = os.getenv(f"{prefix}_API_KEY", "")
    if not api_key:
        raise ValueError(f"{prefix}_API_KEY environment variable is not set")

    base_url = os.getenv(f"{prefix}_BASE_URL") or None
    model = os.getenv(f"{prefix}_MODEL", "gpt-4o")

    return OpenAIOptimizer(
        api_key=api_key,
        base_url=base_url,
        model=model,
        label=pdef.label,
    )
