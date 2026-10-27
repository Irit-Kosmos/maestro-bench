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
API router for signing in and out.

The browser is sent to the identity provider, comes back to the callback, and
leaves it with a session cookie; the API never hands a token to the page.
"""

import asyncio
import logging
from typing import Annotated
from urllib.parse import quote, urlsplit

from authlib.integrations.base_client import OAuthError
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.engine import Engine
from sqlmodel import Session

import config
from auth import providers
from auth.deps import CurrentUser, get_engine, require_user
from auth.policy import Profile, has_restriction, is_allowed
from auth.sessions import create_session, csrf_token, end_session
from auth.users import sign_in
from auth.workspaces import can_create_workspace, claim_default_workspace

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class ProviderOut(BaseModel):
    name: str
    label: str


class UserOut(BaseModel):
    id: int
    display_name: str
    email: str | None
    avatar_url: str | None
    is_instance_admin: bool


class MeOut(BaseModel):
    user: UserOut
    csrf_token: str
    can_create_workspace: bool
    # Whether items can be shared through a public link on this instance
    public_sharing: bool


def _safe_next(value: str | None) -> str:
    """Only paths of this app: anything else would make an open redirect."""
    if not value or not value.startswith("/") or value.startswith("//"):
        return "/"
    if "\\" in value or urlsplit(value).netloc:
        return "/"
    return value


def _login_error(code: str) -> RedirectResponse:
    return RedirectResponse(f"{config.FRONTEND_URL}/login?error={code}")


@router.get("/providers", response_model=list[ProviderOut])
def list_providers():
    """The ways to sign in, for the login page."""
    return [
        ProviderOut(name=p.name, label=p.label) for p in providers.enabled_providers()
    ]


@router.get("/me", response_model=MeOut)
def me(user: Annotated[CurrentUser, Depends(require_user)]):
    """The signed-in user, and the CSRF token to send with every write."""
    return MeOut(
        user=UserOut(**{k: v for k, v in vars(user).items() if k != "session_id"}),
        csrf_token=csrf_token(user.session_id),
        can_create_workspace=can_create_workspace(user),
        public_sharing=config.PUBLIC_SHARING_ENABLED,
    )


@router.post("/logout", status_code=204)
def logout(
    user: Annotated[CurrentUser, Depends(require_user)],
    engine: Annotated[Engine, Depends(get_engine)],
):
    with Session(engine) as db:
        end_session(db, user.session_id)
    response = Response(status_code=204)
    response.delete_cookie(config.SESSION_COOKIE_NAME, path="/")
    return response


def _open_session(engine: Engine, profile: Profile) -> tuple[int, str | None]:
    """Find or create the user of a profile; the session token, None when deactivated."""
    with Session(engine) as db:
        user = sign_in(db, profile)
        if not user.is_active:
            return user.id, None
        claim_default_workspace(db, user)
        return user.id, create_session(db, user.id)


@router.get("/{provider}/login")
async def login(provider: str, request: Request, next: str | None = None):
    client = providers.get_client(provider)
    if client is None:
        return _login_error("unknown_provider")
    request.session["next"] = _safe_next(next)
    redirect_uri = f"{config.PUBLIC_API_URL}/auth/{provider}/callback"
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/{provider}/callback")
async def callback(
    provider: str, request: Request, engine: Annotated[Engine, Depends(get_engine)]
):
    client = providers.get_client(provider)
    if client is None:
        return _login_error("unknown_provider")
    next_path = _safe_next(request.session.pop("next", None))

    try:
        token = await client.authorize_access_token(request)
        claims = dict(token.get("userinfo") or {})
        if has_restriction() and "groups_direct" not in claims:
            claims.update(await client.userinfo(token=token))
        profile = providers.PROVIDERS[provider].to_profile(claims)
    except (OAuthError, KeyError) as error:
        logger.warning("Sign-in with %s failed: %s", provider, error)
        return _login_error("login_failed")

    if not is_allowed(profile):
        logger.warning(
            "Sign-in refused for %s account %s (%s)",
            provider,
            profile.subject,
            profile.email,
        )
        return _login_error("not_allowed")

    user_id, token_value = await asyncio.to_thread(_open_session, engine, profile)
    if token_value is None:
        logger.warning("Sign-in refused: user %s is deactivated", user_id)
        return _login_error("inactive")

    response = RedirectResponse(
        f"{config.FRONTEND_URL}{quote(next_path, safe='/?=&%')}"
    )
    response.set_cookie(
        config.SESSION_COOKIE_NAME,
        token_value,
        max_age=config.SESSION_MAX_DAYS * 86400,
        httponly=True,
        samesite="lax",
        secure=config.COOKIE_SECURE,
        path="/",
    )
    return response
