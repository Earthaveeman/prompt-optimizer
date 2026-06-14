import os
from dataclasses import dataclass

from .base import OptimizerBase
from .claude_provider import ClaudeOptimizer
from .openai_provider import OpenAIOptimizer


# ── Public data types ──────────────────────────────────────────────

@dataclass
class ModelInfo:
    """A single model under a provider."""
    id: str             # e.g. "openai/gpt-oss-120b"
    label: str          # e.g. "GPT-OSS 120B"


@dataclass
class ProviderGroup:
    """A provider with its available models (for two-level UI)."""
    key: str                            # e.g. "nvidia"
    label: str                          # e.g. "NVIDIA NIM"
    configured: bool
    models: list[ModelInfo]


# ── Internal config ─────────────────────────────────────────────────

@dataclass
class _ProviderDef:
    """Internal definition for a provider.

    Models are NOT hardcoded here — they are read from env vars:
      {PREFIX}_MODELS  → comma-separated "id:label" pairs (multi-model)
      {PREFIX}_MODEL   → fallback single model
    """
    label: str                          # e.g. "NVIDIA NIM"
    env_prefix: str                     # e.g. "NVIDIA" → reads NVIDIA_API_KEY, NVIDIA_BASE_URL, NVIDIA_MODELS
    cls: type = OpenAIOptimizer         # which class to instantiate


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
    ),
}


# ── Model resolution from env ───────────────────────────────────────

def _parse_models(prefix: str) -> list[ModelInfo]:
    """Parse model list from {PREFIX}_MODELS or fall back to {PREFIX}_MODEL.

    {PREFIX}_MODELS format:  "id1:Label 1,id2:Label 2,id3"
      - Each entry is "id" or "id:label"
      - Commas separate entries
      - If label is omitted, id is used as label

    Falls back to {PREFIX}_MODEL for backward compatibility.
    """
    models_str = os.getenv(f"{prefix}_MODELS", "")
    if models_str:
        models: list[ModelInfo] = []
        for entry in models_str.split(","):
            entry = entry.strip()
            if not entry:
                continue
            if ":" in entry:
                mid, _, mlabel = entry.partition(":")
                models.append(ModelInfo(id=mid.strip(), label=mlabel.strip()))
            else:
                models.append(ModelInfo(id=entry, label=entry))
        if models:
            return models

    # Fallback: single model from {PREFIX}_MODEL
    single = os.getenv(f"{prefix}_MODEL", "unknown")
    return [ModelInfo(id=single, label=single)]


# ── Public API ──────────────────────────────────────────────────────

def list_provider_groups() -> list[ProviderGroup]:
    """Return providers grouped with their models — for two-level UI."""
    result: list[ProviderGroup] = []
    for pkey, pdef in _providers.items():
        api_key_env = f"{pdef.env_prefix}_API_KEY"
        configured = bool(os.getenv(api_key_env))
        result.append(ProviderGroup(
            key=pkey,
            label=pdef.label,
            configured=configured,
            models=_parse_models(pdef.env_prefix),
        ))
    return result


def get_optimizer(provider: str | None = None, model: str | None = None) -> OptimizerBase:
    """Factory — create an optimizer for a specific provider and model.

    Args:
        provider: Provider key (e.g. 'nvidia').
        model: Model ID (e.g. 'openai/gpt-oss-120b').

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

    # Resolve model: use provided or take the first from the configured list
    if model is None:
        models = _parse_models(prefix)
        model = models[0].id if models else "unknown"

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
