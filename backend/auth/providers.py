"""Identity providers: one entry of configuration and one profile adapter each."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from authlib.integrations.starlette_client import OAuth, StarletteOAuth2App

import config
from auth.policy import Profile

oauth = OAuth()


@dataclass(frozen=True)
class Provider:
    name: str
    label: str
    is_configured: Callable[[], bool]
    register: Callable[[], None]
    to_profile: Callable[[dict[str, Any]], Profile]


def _is_true(value: Any) -> bool:
    return value is True or str(value).lower() == "true"


def gitlab_profile(claims: dict[str, Any]) -> Profile:
    """GitLab's OIDC claims; `groups_direct` lists the paths of the groups joined directly."""
    email = claims.get("email")
    vouched = email if email and _is_true(claims.get("email_verified")) else None
    return Profile(
        provider="gitlab",
        subject=str(claims["sub"]),
        display_name=(
            claims.get("name")
            or claims.get("nickname")
            or claims.get("preferred_username")
            or vouched
            or str(claims["sub"])
        ),
        email=vouched.lower() if vouched else None,
        avatar_url=claims.get("picture"),
        groups=tuple(claims.get("groups_direct") or ()),
    )


def _register_gitlab() -> None:
    oauth.register(
        name="gitlab",
        client_id=config.AUTH_GITLAB_CLIENT_ID,
        client_secret=config.AUTH_GITLAB_CLIENT_SECRET,
        server_metadata_url=(
            f"{config.AUTH_GITLAB_BASE_URL}/.well-known/openid-configuration"
        ),
        client_kwargs={"scope": "openid profile email"},
    )


PROVIDERS: dict[str, Provider] = {
    "gitlab": Provider(
        name="gitlab",
        label="GitLab",
        is_configured=lambda: bool(
            config.AUTH_GITLAB_BASE_URL
            and config.AUTH_GITLAB_CLIENT_ID
            and config.AUTH_GITLAB_CLIENT_SECRET
        ),
        register=_register_gitlab,
        to_profile=gitlab_profile,
    ),
}

_registered: set[str] = set()


def setup_providers() -> list[Provider]:
    """Register the providers that are configured; safe to call more than once."""
    enabled = [p for p in PROVIDERS.values() if p.is_configured()]
    for provider in enabled:
        if provider.name not in _registered:
            provider.register()
            _registered.add(provider.name)
    return enabled


def enabled_providers() -> list[Provider]:
    return [p for p in PROVIDERS.values() if p.name in _registered]


def get_client(name: str) -> StarletteOAuth2App | None:
    if name not in _registered:
        return None
    return oauth.create_client(name)
