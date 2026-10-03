"""
API router for LLM provider status.
"""

from fastapi import APIRouter

from core.llm import SUPPORTED_PROVIDERS, check_provider_available

router = APIRouter(tags=["providers"])


@router.get("/providers")
def list_providers():
    """List supported providers, whether they are configured, and where (an API key, or a server URL for self-hosted ones)."""
    return [
        {
            "provider": provider,
            "configured": check_provider_available(provider),
            "env_var": spec["env_var"],
            "kind": spec.get("kind", "key"),
        }
        for provider, spec in SUPPORTED_PROVIDERS.items()
    ]
