import os
from dataclasses import dataclass, field

from .base import OptimizerBase
from .claude_provider import ClaudeOptimizer
from .openai_provider import OpenAIOptimizer


# ── Public data types ──────────────────────────────────────────────

@dataclass
class ProviderInfo:
    """One selectable option in the UI: a provider + model combination."""
    provider: str       # e.g. "deepseek"
    model_id: str       # e.g. "deepseek-v4-flash"
    label: str          # e.g. "DeepSeek · V4 Flash"
    configured: bool


# ── Internal config ─────────────────────────────────────────────────

@dataclass
class _ModelDef:
    """A model offered by a provider."""
    id: str
    label: str = ""     # short display label; derived from id if omitted


@dataclass
class _ProviderDef:
    """Internal definition for a provider."""
    label: str                          # e.g. "NVIDIA NIM"
    env_prefix: str                     # e.g. "NVIDIA" → reads NVIDIA_API_KEY, NVIDIA_BASE_URL
    cls: type = OpenAIOptimizer         # which class to instantiate
    models: list[_ModelDef] | None = None  # None → read single model from {PREFIX}_MODEL env


_providers: dict[str, _ProviderDef] = {
    "claude": _ProviderDef(
        label="Claude",
        env_prefix="ANTHROPIC",
        cls=ClaudeOptimizer,
    ),
    "modelscope": _ProviderDef(
        label="ModelScope",
        env_prefix="MODELSCOPE",
    ),
    "deepseek": _ProviderDef(
        label="DeepSeek",
        env_prefix="DEEPSEEK",
    ),
    "nvidia": _ProviderDef(
        label="NVIDIA NIM",
        env_prefix="NVIDIA",
        models=[
            _ModelDef(id="openai/gpt-oss-120b", label="GPT-OSS 120B"),
            _ModelDef(id="stepfun-ai/step-3.7-flash", label="Step 3.7 Flash"),
        ],
    ),
}


# ── Public API ──────────────────────────────────────────────────────

def list_providers() -> list[ProviderInfo]:
    """Return every provider × model combination that is available."""
    result: list[ProviderInfo] = []
    for pkey, pdef in _providers.items():
        api_key_env = f"{pdef.env_prefix}_API_KEY"
        configured = bool(os.getenv(api_key_env))

        models = pdef.models
        if models is None:
            # Single model — read from env var
            model_env = f"{pdef.env_prefix}_MODEL"
            default_model = os.getenv(model_env, "unknown")
            models = [_ModelDef(id=default_model)]

        for m in models:
            label = m.label or m.id
            result.append(ProviderInfo(
                provider=pkey,
                model_id=m.id,
                label=f"{pdef.label} · {label}",
                configured=configured,
            ))
    return result


def get_optimizer(provider: str | None = None, model: str | None = None) -> OptimizerBase:
    """Factory — create an optimizer for a specific provider and model.

    Args:
        provider: Provider key (e.g. 'nvidia').
        model: Model ID (e.g. 'openai/gpt-oss-120b').
               If None, reads {PREFIX}_MODEL from env.

    Raises:
        ValueError: Unknown provider or missing API key.
    """
    if provider is None:
        provider = os.getenv("LLM_PROVIDER", "claude")

    provider = provider.lower().strip()
    if provider not in _providers:
        raise ValueError(
            f"Unknown provider: '{provider}'. "
            f"Supported: {', '.join(_providers.keys())}"
        )

    pdef = _providers[provider]
    prefix = pdef.env_prefix

    # Resolve model
    if model is None:
        model = os.getenv(f"{prefix}_MODEL", "unknown")

    # Claude uses its own class
    if pdef.cls is ClaudeOptimizer:
        return ClaudeOptimizer(model=model)

    # OpenAI-compatible
    api_key = os.getenv(f"{prefix}_API_KEY", "")
    if not api_key:
        raise ValueError(f"{prefix}_API_KEY environment variable is not set")

    base_url = os.getenv(f"{prefix}_BASE_URL") or None

    return OpenAIOptimizer(
        api_key=api_key,
        base_url=base_url,
        model=model,
        label=f"{pdef.label} · {model}",
    )
