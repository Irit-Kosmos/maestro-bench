"""
API router for LLM provider status.
"""

from fastapi import APIRouter

from core.llm import SUPPORTED_PROVIDERS, check_provider_available

router = APIRouter(tags=["providers"])


@router.get("/providers")
def list_providers():
    """List supported providers, whether their API key is configured, and where it is set."""
    return [
        {
            "provider": provider,
            "configured": check_provider_available(provider),
            "api_key_env": spec["api_key_env"],
        }
        for provider, spec in SUPPORTED_PROVIDERS.items()
    ]
