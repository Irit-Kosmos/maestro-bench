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
API router for LLM providers: which are usable, and the workspace's own API keys.
"""


from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import credentials
from auth.workspaces import requires
from core.llm import SUPPORTED_PROVIDERS
from db import SessionDep
from workspace_scope import current_user_id

router = APIRouter(tags=["providers"])


class ApiKeyIn(BaseModel):
    api_key: str


class ProviderResponse(BaseModel):
    provider: str
    configured: bool
    env_var: str
    kind: str
    # Where the calls get their key: the workspace's own, or the instance's
    source: Literal["workspace", "instance"] | None
    # The workspace's key is never shown again, only its end
    key_hint: str | None
    can_store_key: bool


def _provider_view(provider: str, spec: dict, stored) -> ProviderResponse:
    kind = spec.get("kind", "key")
    return ProviderResponse(
        provider=provider,
        configured=stored is not None or credentials.instance_provides(provider),
        env_var=spec["env_var"],
        kind=kind,
        source="workspace"
        if stored is not None
        else "instance"
        if credentials.instance_provides(provider)
        else None,
        key_hint=stored.last4 if stored is not None else None,
        can_store_key=kind == "key" and credentials.keys_enabled(),
    )


@router.get("/providers")
def list_providers(session: SessionDep) -> list[ProviderResponse]:
    """List supported providers, whether the workspace can call them, and with whose key."""
    stored = credentials.stored_keys(session)
    return [
        _provider_view(provider, spec, stored.get(provider))
        for provider, spec in SUPPORTED_PROVIDERS.items()
    ]


def _checked(provider: str) -> str:
    name = provider.lower()
    spec = SUPPORTED_PROVIDERS.get(name)
    if spec is None:
        raise HTTPException(404, "Unknown provider")
    if spec.get("kind", "key") != "key":
        raise HTTPException(
            422, f"{name} is configured for the whole instance, not per workspace"
        )
    return name


@router.put("/providers/{provider}/key")
@requires("owner")
def set_provider_key(
    provider: str,
    data: ApiKeyIn,
    session: SessionDep,
) -> ProviderResponse:
    """Store the workspace's own API key for a provider, replacing any previous one."""
    name = _checked(provider)
    if not credentials.keys_enabled():
        raise HTTPException(
            503, "This instance has no ENCRYPTION_KEY: workspaces cannot store keys"
        )
    try:
        row = credentials.set_key(session, name, data.api_key, current_user_id(session))
    except credentials.CredentialError as e:
        raise HTTPException(422, str(e)) from e
    return _provider_view(name, SUPPORTED_PROVIDERS[name], row)


@router.delete("/providers/{provider}/key", status_code=204)
@requires("owner")
def delete_provider_key(
    provider: str, session: SessionDep
):
    """Forget the workspace's key: the provider goes back to the instance's, if any."""
    if not credentials.delete_key(session, _checked(provider)):
        raise HTTPException(404, "This workspace has no key for this provider")
