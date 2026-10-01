import asyncio
from types import SimpleNamespace

import httpx
import litellm
import pytest

from core import llm


def _response(content="ok"):
    return SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=3, completion_tokens=2),
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
    )


def _rate_limit_error(headers=None):
    return litellm.RateLimitError(
        message="Rate limit exceeded",
        llm_provider="mistral",
        model="mistral-small",
        response=httpx.Response(
            429,
            headers=headers or {},
            request=httpx.Request("POST", "https://api.mistral.ai"),
        ),
    )


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    sleeps = []

    async def fake_sleep(delay):
        sleeps.append(delay)

    monkeypatch.setattr(llm.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(llm.litellm, "completion_cost", lambda **_: 0.0)
    return sleeps


def _call():
    return asyncio.run(
        llm.call_llm("mistral-small", "mistral", [{"role": "user", "content": "hi"}])
    )


def test_retries_rate_limit_then_succeeds(monkeypatch, no_sleep):
    outcomes = [_rate_limit_error(), _rate_limit_error(), _response("done")]

    async def fake_acompletion(**_):
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(llm.litellm, "acompletion", fake_acompletion)

    assert _call().content == "done"
    assert len(no_sleep) == 2


def test_honors_retry_after_header(monkeypatch, no_sleep):
    outcomes = [_rate_limit_error({"retry-after": "7"}), _response()]

    async def fake_acompletion(**_):
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(llm.litellm, "acompletion", fake_acompletion)

    _call()
    assert no_sleep == [7.0]


def test_gives_up_after_max_retries(monkeypatch, no_sleep):
    monkeypatch.setattr(llm, "LLM_MAX_RETRIES", 2)

    async def fake_acompletion(**_):
        raise _rate_limit_error()

    monkeypatch.setattr(llm.litellm, "acompletion", fake_acompletion)

    with pytest.raises(litellm.RateLimitError):
        _call()
    assert len(no_sleep) == 2


def test_does_not_retry_non_transient_errors(monkeypatch, no_sleep):
    calls = []

    async def fake_acompletion(**_):
        calls.append(1)
        raise ValueError("bad prompt")

    monkeypatch.setattr(llm.litellm, "acompletion", fake_acompletion)

    with pytest.raises(ValueError):
        _call()
    assert len(calls) == 1
    assert no_sleep == []


def test_rate_limiter_spaces_out_requests(no_sleep):
    limiter = llm._RateLimiter(rps=2)

    async def burst():
        for _ in range(3):
            await limiter.acquire()

    asyncio.run(burst())
    # First request goes immediately, the next two wait for their slot
    assert no_sleep == [pytest.approx(0.5, abs=0.05), pytest.approx(1.0, abs=0.05)]
