"""The instance's doorman: decides which accounts of an identity provider may sign in."""

import logging
from dataclasses import dataclass

import config

logger = logging.getLogger(__name__)

MIN_SECRET_KEY_LENGTH = 32


class AuthConfigError(RuntimeError):
    """The authentication settings cannot be used to start the app."""


@dataclass(frozen=True)
class Profile:
    """What an identity provider tells us about an account, in the app's terms."""

    provider: str
    subject: str
    display_name: str
    email: str | None  # only when the provider vouches for it
    avatar_url: str | None = None
    groups: tuple[str, ...] = ()


def has_restriction() -> bool:
    return bool(config.AUTH_ALLOWED_EMAIL_DOMAINS or config.AUTH_GITLAB_ALLOWED_GROUPS)


def validate_config(providers: list[str]) -> None:
    """Refuse to start with settings that would leave the app open or unusable."""
    problems = []
    if len(config.SECRET_KEY) < MIN_SECRET_KEY_LENGTH:
        problems.append(
            f"SECRET_KEY must be set to at least {MIN_SECRET_KEY_LENGTH} characters"
        )
    if not config.FRONTEND_URL:
        problems.append("FRONTEND_URL (or CORS_ORIGINS) must be set")
    if not providers:
        problems.append(
            "no identity provider is configured: set AUTH_GITLAB_BASE_URL, "
            "AUTH_GITLAB_CLIENT_ID and AUTH_GITLAB_CLIENT_SECRET"
        )
    if not has_restriction() and not config.AUTH_ALLOW_ANY_USER:
        problems.append(
            "nobody is allowed to sign in: set AUTH_ALLOWED_EMAIL_DOMAINS or "
            "AUTH_GITLAB_ALLOWED_GROUPS, or AUTH_ALLOW_ANY_USER=true to accept any account"
        )
    if problems:
        raise AuthConfigError("Invalid authentication settings: " + "; ".join(problems))
    if has_restriction() and config.AUTH_ALLOW_ANY_USER:
        logger.warning("AUTH_ALLOW_ANY_USER is ignored: an allowlist is set")


def _email_domain_allowed(profile: Profile) -> bool:
    if not profile.email or "@" not in profile.email:
        return False
    return profile.email.rsplit("@", 1)[1].lower() in config.AUTH_ALLOWED_EMAIL_DOMAINS


def _group_allowed(profile: Profile) -> bool:
    # A member of a subgroup belongs to the groups above it
    for group in (g.strip("/").lower() for g in profile.groups):
        for allowed in config.AUTH_GITLAB_ALLOWED_GROUPS:
            if group == allowed or group.startswith(f"{allowed}/"):
                return True
    return False


def is_allowed(profile: Profile) -> bool:
    """Every restriction that is configured must be satisfied."""
    if not has_restriction():
        return config.AUTH_ALLOW_ANY_USER
    if config.AUTH_ALLOWED_EMAIL_DOMAINS and not _email_domain_allowed(profile):
        return False
    return not (config.AUTH_GITLAB_ALLOWED_GROUPS and not _group_allowed(profile))


def is_instance_admin(email: str | None) -> bool:
    return bool(email) and email.lower() in config.INSTANCE_ADMINS
