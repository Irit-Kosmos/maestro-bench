"""
API router for LLM provider status.
"""

from fastapi import APIRouter

from core.llm import check_provider_available

router = APIRouter(prefix="/api/providers", tags=["providers"])

KNOWN_PROVIDERS = ["openai", "anthropic", "mistral"]


@router.get("")
async def list_providers():
    """List all known providers and whether their API key is configured."""
    results = []
    for provider in KNOWN_PROVIDERS:
        available = await check_provider_available(provider)
        results.append({"provider": provider, "configured": available})
    return results
