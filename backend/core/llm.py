# MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
# Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
# Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
LLM abstraction layer using LiteLLM.

Provides a unified async interface to call any LLM provider
(OpenAI, Anthropic, Mistral, etc.) with retry logic, cost tracking,
and latency measurement.
"""

import asyncio
import logging
import os
import random
import time
from dataclasses import dataclass

import litellm

logger = logging.getLogger(__name__)

# Suppress LiteLLM's verbose logging by default
litellm.suppress_debug_info = True

# Providers supported out of the box: LiteLLM model prefix (None = no prefix)
# and the environment variable that makes them callable. "kind" says what that
# variable holds: an API key ("key", the default) or the URL of a server you
# host yourself ("url"), which needs no key. Any other LiteLLM provider can be
# added here: https://docs.litellm.ai/docs/providers
SUPPORTED_PROVIDERS: dict[str, dict] = {
    "openai": {"prefix": None, "env_var": "OPENAI_API_KEY"},
    "anthropic": {"prefix": None, "env_var": "ANTHROPIC_API_KEY"},
    "mistral": {"prefix": "mistral", "env_var": "MISTRAL_API_KEY"},
    "groq": {"prefix": "groq", "env_var": "GROQ_API_KEY"},
    "together": {"prefix": "together_ai", "env_var": "TOGETHER_API_KEY"},
    "deepseek": {"prefix": "deepseek", "env_var": "DEEPSEEK_API_KEY"},
    # LiteLLM calls Google AI Studio "gemini"; the provider keeps the name people know
    "google": {"prefix": "gemini", "env_var": "GEMINI_API_KEY"},
    "xai": {"prefix": "xai", "env_var": "XAI_API_KEY"},
    "cerebras": {"prefix": "cerebras", "env_var": "CEREBRAS_API_KEY"},
    "perplexity": {"prefix": "perplexity", "env_var": "PERPLEXITYAI_API_KEY"},
    "openrouter": {"prefix": "openrouter", "env_var": "OPENROUTER_API_KEY"},
    # LiteLLM reads OLLAMA_API_BASE itself (default http://localhost:11434)
    "ollama": {"prefix": "ollama_chat", "env_var": "OLLAMA_API_BASE", "kind": "url"},
}


# Transient provider errors worth retrying (429, timeouts, 5xx)
RETRYABLE_ERRORS: tuple[type[Exception], ...] = (
    litellm.RateLimitError,
    litellm.Timeout,
    litellm.APIConnectionError,
    litellm.ServiceUnavailableError,
    litellm.InternalServerError,
)

LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "6"))
LLM_RETRY_BASE_DELAY = float(os.getenv("LLM_RETRY_BASE_DELAY", "1.0"))
LLM_RETRY_MAX_DELAY = float(os.getenv("LLM_RETRY_MAX_DELAY", "60.0"))


class _RateLimiter:
    """
    Spaces out request starts to at most `rps` per second.

    Shared by every experiment calling with the same API key, since provider
    quotas apply per API key rather than per experiment.
    """

    def __init__(self, rps: float):
        self.interval = 1.0 / rps
        self._next_slot = 0.0

    async def acquire(self) -> None:
        # No await between reading and booking the slot, so this is atomic
        # on a single event loop.
        now = time.monotonic()
        slot = max(now, self._next_slot)
        self._next_slot = slot + self.interval
        if slot > now:
            await asyncio.sleep(slot - now)


_rate_limiters: dict[tuple[str, str], _RateLimiter | None] = {}


def _get_rate_limiter(provider: str, key_id: str = "instance") -> _RateLimiter | None:
    """
    Return the limiter of a provider's API key, configured by e.g. MISTRAL_MAX_RPS.

    Each key has its own limit, as it has its own quota: workspaces using their own
    key do not slow each other down, while those sharing the instance's key do.
    """
    provider = provider.lower()
    if (provider, key_id) not in _rate_limiters:
        rps = os.getenv(f"{provider.upper()}_MAX_RPS")
        _rate_limiters[provider, key_id] = _RateLimiter(float(rps)) if rps else None
    return _rate_limiters[provider, key_id]


def _retry_delay(error: Exception, attempt: int) -> float:
    """Honor the provider's Retry-After header, else exponential backoff."""
    response = getattr(error, "response", None)
    headers = getattr(response, "headers", None) or {}
    retry_after = headers.get("retry-after")
    if retry_after:
        try:
            return min(float(retry_after), LLM_RETRY_MAX_DELAY)
        except ValueError:
            pass  # HTTP-date form, fall back to backoff
    backoff = min(LLM_RETRY_BASE_DELAY * 2**attempt, LLM_RETRY_MAX_DELAY)
    # Full jitter so concurrent rows don't retry in lockstep
    return random.uniform(backoff / 2, backoff)


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
    api_key: str | None = None,
    key_id: str = "instance",
) -> LLMResponse:
    """
    Call an LLM via LiteLLM.

    Args:
        model: Model identifier (e.g. "mistral-medium-2505", "gpt-4o", "claude-sonnet-4-20250514")
        provider: Provider name (e.g. "openai", "anthropic", "mistral")
        messages: Chat messages in OpenAI format [{"role": ..., "content": ...}]
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        api_key: Key to call the provider with; None uses the instance's
            (the environment variable LiteLLM reads)
        key_id: Which rate limit the call counts against (see _get_rate_limiter)

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
    if api_key is not None:
        kwargs["api_key"] = api_key

    rate_limiter = _get_rate_limiter(provider, key_id)
    for attempt in range(LLM_MAX_RETRIES + 1):
        if rate_limiter:
            await rate_limiter.acquire()
        # Latency covers the successful attempt only, not retries and waits
        start = time.perf_counter()
        try:
            response = await litellm.acompletion(**kwargs)
        except RETRYABLE_ERRORS as e:
            if attempt == LLM_MAX_RETRIES:
                raise
            delay = _retry_delay(e, attempt)
            logger.warning(
                "%s on %s, retry %d/%d in %.1fs",
                type(e).__name__,
                litellm_model,
                attempt + 1,
                LLM_MAX_RETRIES,
                delay,
            )
            await asyncio.sleep(delay)
        else:
            break
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
    Check if a provider is configured: its API key or server URL is set.
    Returns True if the env var is set (doesn't validate it or reach the server).
    """
    spec = SUPPORTED_PROVIDERS.get(provider.lower())
    if not spec:
        return False
    return bool(os.getenv(spec["env_var"]))
