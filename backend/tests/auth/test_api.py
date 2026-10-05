from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.responses import RedirectResponse
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from starlette.middleware.sessions import SessionMiddleware

import config
from api import auth as auth_api
from auth import providers
from auth.deps import get_engine, require_user
from auth.sessions import create_session, csrf_token, hash_token
from auth.users import set_active
from tables import AuthSession, User

FRONTEND = "http://localhost:3000"

CLAIMS = {
    "sub": "42",
    "name": "Rémi Saurel",
    "email": "remi@irit.fr",
    "email_verified": True,
    "groups_direct": [],
}


class FakeClient:
    """Stands in for Authlib's client: the identity provider answers with CLAIMS."""

    def __init__(self, claims):
        self.claims = claims

    async def authorize_redirect(self, request, redirect_uri):
        return RedirectResponse(f"https://gitlab.example/authorize?to={redirect_uri}")

    async def authorize_access_token(self, request):
        return {"userinfo": self.claims}

    async def userinfo(self, token):
        return self.claims


@pytest.fixture
def idp(monkeypatch):
    """The claims the fake identity provider returns; tests edit them in place."""
    claims = dict(CLAIMS)
    fake = FakeClient(claims)
    monkeypatch.setattr(providers, "_registered", {"gitlab"})
    monkeypatch.setattr(
        providers, "get_client", lambda name: fake if name == "gitlab" else None
    )
    return claims


@pytest.fixture
def client(engine, idp):
    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key=config.SECRET_KEY, max_age=600)
    app.include_router(auth_api.router)

    protected = APIRouter(dependencies=[Depends(require_user)])

    @protected.get("/things")
    def read_things():
        return ["a"]

    @protected.post("/things", status_code=201)
    def create_thing():
        return {"id": 1}

    app.include_router(protected)
    app.dependency_overrides[get_engine] = lambda: engine
    return TestClient(app, follow_redirects=False)


def sign_in_via_callback(client):
    response = client.get("/auth/gitlab/callback")
    assert response.status_code in (302, 307)
    return response


def csrf_headers(client):
    return {"X-CSRF-Token": client.get("/auth/me").json()["csrf_token"]}


def test_every_protected_route_needs_a_session(client):
    assert client.get("/things").status_code == 401
    assert client.post("/things").status_code == 401
    assert client.get("/auth/me").status_code == 401


def test_the_login_page_can_list_the_providers_without_a_session(client):
    assert client.get("/auth/providers").json() == [
        {"name": "gitlab", "label": "GitLab"}
    ]


def test_signing_in_opens_a_session_and_goes_back_to_the_app(client, session):
    response = sign_in_via_callback(client)

    assert response.headers["location"] == FRONTEND + "/"
    cookie = response.headers["set-cookie"]
    assert cookie.startswith("maestro_session=")
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Secure" not in cookie
    assert client.get("/things").json() == ["a"]
    user = session.exec(select(User)).one()
    assert (user.email, user.display_name) == ("remi@irit.fr", "Rémi Saurel")


def test_the_session_cookie_is_secure_when_the_ui_is_served_over_https(
    client, monkeypatch
):
    monkeypatch.setattr(config, "COOKIE_SECURE", True)

    assert "Secure" in sign_in_via_callback(client).headers["set-cookie"]


def test_login_remembers_where_to_go_back_to(client):
    client.get("/auth/gitlab/login", params={"next": "/experiments/3?tab=runs"})

    response = client.get("/auth/gitlab/callback")

    assert response.headers["location"] == FRONTEND + "/experiments/3?tab=runs"


def test_login_redirects_to_the_provider_with_the_registered_callback(client):
    response = client.get("/auth/gitlab/login")

    assert response.headers["location"].endswith(
        "to=http://localhost:8000/auth/gitlab/callback"
    )


@pytest.mark.parametrize(
    "target", ["https://evil.example", "//evil.example", "/\\evil.example", "evil"]
)
def test_login_never_redirects_outside_the_app(client, target):
    client.get("/auth/gitlab/login", params={"next": target})

    response = client.get("/auth/gitlab/callback")

    assert response.headers["location"] == FRONTEND + "/"


def test_an_unknown_provider_is_refused(client):
    for path in ("/auth/nope/login", "/auth/nope/callback"):
        location = client.get(path).headers["location"]
        assert parse_qs(urlsplit(location).query) == {"error": ["unknown_provider"]}


def test_an_account_outside_the_allowed_domains_gets_no_session_and_no_user(
    client, idp, session
):
    idp["email"] = "someone@gmail.com"

    response = client.get("/auth/gitlab/callback")

    assert response.headers["location"] == f"{FRONTEND}/login?error=not_allowed"
    assert "set-cookie" not in response.headers
    assert client.get("/things").status_code == 401
    assert session.exec(select(User)).all() == []


def test_an_unverified_email_does_not_pass_the_domain_check(client, idp):
    idp["email_verified"] = False

    response = client.get("/auth/gitlab/callback")

    assert response.headers["location"] == f"{FRONTEND}/login?error=not_allowed"


def test_a_deactivated_user_cannot_sign_in(client, session):
    sign_in_via_callback(client)
    user = session.exec(select(User)).one()
    set_active(session, user, False)

    response = client.get("/auth/gitlab/callback")

    assert response.headers["location"] == f"{FRONTEND}/login?error=inactive"
    assert client.get("/things").status_code == 401


def test_a_failed_exchange_with_the_provider_is_reported(client, monkeypatch):
    from authlib.integrations.base_client import OAuthError

    async def fail(request):
        raise OAuthError(error="access_denied")

    monkeypatch.setattr(providers.get_client("gitlab"), "authorize_access_token", fail)

    response = client.get("/auth/gitlab/callback")

    assert response.headers["location"] == f"{FRONTEND}/login?error=login_failed"


def test_me_describes_the_user_and_gives_the_csrf_token(client, session, monkeypatch):
    monkeypatch.setattr(config, "INSTANCE_ADMINS", ["remi@irit.fr"])
    sign_in_via_callback(client)

    body = client.get("/auth/me").json()

    session_id = session.exec(select(AuthSession)).one().id
    assert body["user"]["email"] == "remi@irit.fr"
    assert body["user"]["is_instance_admin"] is True
    assert body["csrf_token"] == csrf_token(session_id)
    assert "session_id" not in body["user"]


def test_writes_need_the_csrf_token(client):
    sign_in_via_callback(client)

    assert client.post("/things").status_code == 403
    assert client.post("/things", headers={"X-CSRF-Token": "wrong"}).status_code == 403
    assert client.post("/things", headers=csrf_headers(client)).status_code == 201


def test_a_csrf_token_of_another_session_is_refused(client, engine):
    sign_in_via_callback(client)
    with Session(engine) as db:
        other = create_session(db, db.exec(select(User)).one().id)
    stolen = {"X-CSRF-Token": csrf_token(hash_token(other))}

    assert client.post("/things", headers=stolen).status_code == 403


def test_writes_from_another_origin_are_refused_even_with_the_token(client):
    sign_in_via_callback(client)
    headers = {**csrf_headers(client), "Origin": "https://evil.example"}

    assert client.post("/things", headers=headers).status_code == 403
    assert (
        client.post("/things", headers={**headers, "Origin": FRONTEND}).status_code
        == 201
    )


def test_reads_do_not_need_the_csrf_token(client):
    sign_in_via_callback(client)

    assert (
        client.get("/things", headers={"Origin": "https://evil.example"}).status_code
        == 200
    )


def test_logging_out_ends_the_session(client, session):
    sign_in_via_callback(client)

    response = client.post("/auth/logout", headers=csrf_headers(client))

    assert response.status_code == 204
    assert session.exec(select(AuthSession)).all() == []
    assert client.get("/things").status_code == 401


def test_logging_out_needs_the_csrf_token(client):
    sign_in_via_callback(client)

    assert client.post("/auth/logout").status_code == 403
    assert client.get("/things").status_code == 200


def test_deactivating_a_user_cuts_them_off_at_once(client, session):
    sign_in_via_callback(client)
    set_active(session, session.exec(select(User)).one(), False)

    assert client.get("/things").status_code == 401
