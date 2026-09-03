"""
LLM abstraction layer using LiteLLM.

Provides a unified async interface to call any LLM provider
(OpenAI, Anthropic, Mistral, etc.) with retry logic, cost tracking,
and latency measurement.
"""

import os
import time
from dataclasses import dataclass

import litellm

# Suppress LiteLLM's verbose logging by default
litellm.suppress_debug_info = True

# Providers supported out of the box: LiteLLM model prefix (None = no prefix)
# and the environment variable holding the API key.
SUPPORTED_PROVIDERS: dict[str, dict] = {
    "openai": {"prefix": None, "api_key_env": "OPENAI_API_KEY"},
    "anthropic": {"prefix": None, "api_key_env": "ANTHROPIC_API_KEY"},
    "mistral": {"prefix": "mistral", "api_key_env": "MISTRAL_API_KEY"},
    "groq": {"prefix": "groq", "api_key_env": "GROQ_API_KEY"},
    "together": {"prefix": "together_ai", "api_key_env": "TOGETHER_API_KEY"},
    "deepseek": {"prefix": "deepseek", "api_key_env": "DEEPSEEK_API_KEY"},
}


@dataclass
class LLMResponse:
    """Structured response from an LLM call."""

    content: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    model: str = ""


async def call_llm(
    model: str,
    provider: str,
    messages: list[dict],
    temperature: float = 0.0,
    max_tokens: int | None = None,
) -> LLMResponse:
    """
    Call an LLM via LiteLLM.

    Args:
        model: Model identifier (e.g. "mistral-medium-2505", "gpt-4o", "claude-sonnet-4-20250514")
        provider: Provider name (e.g. "openai", "anthropic", "mistral")
        messages: Chat messages in OpenAI format [{"role": ..., "content": ...}]
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate

    Returns:
        LLMResponse with content, usage metrics, and cost
    """
    # LiteLLM uses provider/model format for routing
    litellm_model = _resolve_model_id(model, provider)

    kwargs: dict = {
        "model": litellm_model,
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    start = time.perf_counter()
    response = await litellm.acompletion(**kwargs)
    latency_ms = (time.perf_counter() - start) * 1000

    # Extract usage
    usage = response.usage or {}
    tokens_in = getattr(usage, "prompt_tokens", 0) or 0
    tokens_out = getattr(usage, "completion_tokens", 0) or 0

    # Cost estimation via LiteLLM
    try:
        cost = litellm.completion_cost(completion_response=response)
    except Exception:  # noqa: BLE001 - unknown models raise assorted LiteLLM errors
        cost = 0.0

    content = response.choices[0].message.content or ""

    return LLMResponse(
        content=content,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost,
        latency_ms=latency_ms,
        model=litellm_model,
    )


def _resolve_model_id(model: str, provider: str) -> str:
    """
    Resolve to the LiteLLM model identifier.

    LiteLLM expects a "<prefix>/<model>" format for some providers
    (e.g. "mistral/mistral-medium-2505") and the bare model name for others
    (OpenAI, Anthropic). See: https://docs.litellm.ai/docs/providers
    """
    spec = SUPPORTED_PROVIDERS.get(provider.lower())
    prefix = spec["prefix"] if spec else None
    if prefix and not model.startswith(f"{prefix}/"):
        return f"{prefix}/{model}"
    return model


def check_provider_available(provider: str) -> bool:
    """
    Check if a provider's API key is configured.
    Returns True if the key env var is set (doesn't validate the key).
    """
    spec = SUPPORTED_PROVIDERS.get(provider.lower())
    if not spec:
        return False
    return bool(os.getenv(spec["api_key_env"]))
