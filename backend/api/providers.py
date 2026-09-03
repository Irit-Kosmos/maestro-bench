"""
API router for LLM provider status.
"""

from fastapi import APIRouter

from core.llm import SUPPORTED_PROVIDERS, check_provider_available

router = APIRouter(tags=["providers"])


@router.get("/providers")
def list_providers():
    """List supported providers and whether their API key is configured."""
    return [
        {"provider": provider, "configured": check_provider_available(provider)}
        for provider in SUPPORTED_PROVIDERS
    ]
