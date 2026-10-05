"""
API keys of the LLM providers, and whose key a call uses.

A workspace may store its own key for a provider. It is encrypted with
``ENCRYPTION_KEY`` before it reaches the database, only its last four characters are
ever shown again, and it is decrypted for the time of a run. A provider the workspace
has no key for falls back to the instance's own (the environment variable).
"""

import base64
import hashlib
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from cryptography.fernet import Fernet, InvalidToken
from sqlmodel import Session, select

import config
from core.llm import SUPPORTED_PROVIDERS, check_provider_available
from tables import WorkspaceCredential

logger = logging.getLogger(__name__)

MIN_ENCRYPTION_KEY_LENGTH = 32
MIN_API_KEY_LENGTH = 8
MAX_API_KEY_LENGTH = 512


class CredentialError(ValueError):
    """The key cannot be stored or read."""


@dataclass(frozen=True)
class ProviderAccess:
    """How a provider is reached for a workspace."""

    # "workspace" (its own key), "instance" (the environment), or None (not configured)
    source: str | None
    # Passed to the provider; None lets LiteLLM read the environment
    api_key: str | None = None
    # Which quota the call counts against, whatever the workspace
    key_id: str = "instance"
    # Why the call must not be made at all (the instance's key is not shared with workspaces)
    error: str | None = None


def check_config() -> None:
    """Refuse to start with an encryption key that is too weak to use."""
    if config.ENCRYPTION_KEY and len(config.ENCRYPTION_KEY) < MIN_ENCRYPTION_KEY_LENGTH:
        raise CredentialError(
            f"ENCRYPTION_KEY must have at least {MIN_ENCRYPTION_KEY_LENGTH} characters"
        )


def keys_enabled() -> bool:
    return bool(config.ENCRYPTION_KEY)


def _fernet() -> Fernet:
    if not config.ENCRYPTION_KEY:
        raise CredentialError("The instance has no ENCRYPTION_KEY: keys cannot be stored")
    digest = hashlib.sha256(
        b"maestro-bench workspace credentials\0" + config.ENCRYPTION_KEY.encode()
    ).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(secret: str) -> str:
    return _fernet().encrypt(secret.encode()).decode()


def decrypt(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as e:
        raise CredentialError(
            "The stored key cannot be decrypted: ENCRYPTION_KEY has changed"
        ) from e


def _keyed_provider(provider: str) -> str:
    """The provider's name, if it takes an API key (self-hosted ones take a URL)."""
    name = provider.lower()
    spec = SUPPORTED_PROVIDERS.get(name)
    if spec is None:
        raise CredentialError(f"Unknown provider {provider!r}")
    if spec.get("kind", "key") != "key":
        raise CredentialError(
            f"{name} is configured for the whole instance, not per workspace"
        )
    return name


def _stored(session: Session, provider: str) -> WorkspaceCredential | None:
    return session.exec(
        select(WorkspaceCredential).where(WorkspaceCredential.provider == provider)
    ).first()


def set_key(
    session: Session, provider: str, api_key: str, user_id: int | None = None
) -> WorkspaceCredential:
    """Store (or replace) the key of the session's workspace for a provider."""
    name = _keyed_provider(provider)
    api_key = api_key.strip()
    if not MIN_API_KEY_LENGTH <= len(api_key) <= MAX_API_KEY_LENGTH or any(
        c.isspace() for c in api_key
    ):
        raise CredentialError("This does not look like an API key")
    row = _stored(session, name) or WorkspaceCredential(provider=name, ciphertext="", last4="")
    row.ciphertext = encrypt(api_key)
    row.last4 = api_key[-4:]
    row.updated_at = datetime.now(UTC)
    row.updated_by = user_id
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def delete_key(session: Session, provider: str) -> bool:
    """Forget the workspace's key; returns whether there was one."""
    row = _stored(session, _keyed_provider(provider))
    if row is None:
        return False
    session.delete(row)
    session.commit()
    return True


def stored_keys(session: Session) -> dict[str, WorkspaceCredential]:
    return {row.provider: row for row in session.exec(select(WorkspaceCredential)).all()}


def instance_provides(provider: str) -> bool:
    """Whether the instance's own key or URL is there for workspaces to use."""
    name = (provider or "").lower()
    spec = SUPPORTED_PROVIDERS.get(name)
    if spec is None or not check_provider_available(name):
        return False
    return spec.get("kind", "key") == "url" or config.PROVIDERS_INSTANCE_FALLBACK


def access_to(session: Session, provider: str) -> ProviderAccess:
    """The key a call to this provider uses on behalf of the session's workspace."""
    name = (provider or "").lower()
    spec = SUPPORTED_PROVIDERS.get(name)
    if spec is not None and spec.get("kind", "key") == "key":
        row = _stored(session, name)
        if row is not None:
            try:
                secret = decrypt(row.ciphertext)
            except CredentialError:
                logger.error(
                    "The key of workspace %s for %s cannot be decrypted",
                    row.workspace_id,
                    name,
                )
            else:
                fingerprint = hashlib.sha256(secret.encode()).hexdigest()[:16]
                return ProviderAccess("workspace", secret, f"key:{fingerprint}")
        if not config.PROVIDERS_INSTANCE_FALLBACK:
            return ProviderAccess(
                None,
                error=(
                    f"This workspace has no {name} API key, and the instance's keys "
                    "are not shared: an owner must set one in Settings"
                ),
            )
    return ProviderAccess("instance" if instance_provides(name) else None)
