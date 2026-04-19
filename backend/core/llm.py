"""
LLM abstraction layer using LiteLLM.

Provides a unified async interface to call any LLM provider
(OpenAI, Anthropic, Mistral, etc.) with retry logic, cost tracking,
and latency measurement.
"""

import time
from dataclasses import dataclass, field
from typing import Optional

import litellm

# Suppress LiteLLM's verbose logging by default
litellm.suppress_debug_info = True


@dataclass
class LLMResponse:
    """Structured response from an LLM call."""

    content: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    model: str = ""
    raw_response: Optional[dict] = field(default=None, repr=False)


async def call_llm(
    model: str,
    provider: str,
    messages: list[dict],
    temperature: float = 0.0,
    max_tokens: Optional[int] = None,
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
    except Exception:
        cost = 0.0

    content = response.choices[0].message.content or ""

    return LLMResponse(
        content=content,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost,
        latency_ms=latency_ms,
        model=litellm_model,
        raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
    )


def _resolve_model_id(model: str, provider: str) -> str:
    """
    Resolve to the LiteLLM model identifier.

    LiteLLM expects a prefix for some providers:
    - OpenAI models: just the model name (e.g. "gpt-4o")
    - Anthropic: just the model name (e.g. "claude-sonnet-4-20250514")
    - Mistral: "mistral/<model>" (e.g. "mistral/mistral-medium-2505")

    See: https://docs.litellm.ai/docs/providers
    """
    provider_lower = provider.lower()

    # Providers that need a prefix
    prefixed_providers = {
        "mistral": "mistral",
        "groq": "groq",
        "together": "together_ai",
        "deepseek": "deepseek",
        "ollama": "ollama",
    }

    prefix = prefixed_providers.get(provider_lower)
    if prefix and not model.startswith(f"{prefix}/"):
        return f"{prefix}/{model}"

    return model


async def check_provider_available(provider: str) -> bool:
    """
    Check if a provider's API key is configured.
    Returns True if the key env var is set (doesn't validate the key).
    """
    import os

    key_env_vars = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "mistral": "MISTRAL_API_KEY",
        "groq": "GROQ_API_KEY",
        "together": "TOGETHER_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
    }

    env_var = key_env_vars.get(provider.lower())
    if not env_var:
        return False
    return bool(os.getenv(env_var))
