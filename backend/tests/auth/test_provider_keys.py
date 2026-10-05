"""A workspace's own API keys: who may set them, that they stay secret, and that
a run calls the provider with them."""

import pytest
from sqlmodel import Session, select

import config
import credentials
from core.llm import SUPPORTED_PROVIDERS
from tables import WorkspaceCredential
from tests.auth.people import add_member

SECRET = "sk-test-0123456789abcdef"


@pytest.fixture(autouse=True)
def encryption_key(monkeypatch):
    monkeypatch.setattr(config, "ENCRYPTION_KEY", "e" * 40)
    for spec in SUPPORTED_PROVIDERS.values():
        monkeypatch.delenv(spec["env_var"], raising=False)


@pytest.fixture
def workspace(alice, bob, engine):
    slug = alice.create_workspace("Keys")
    add_member(engine, slug, bob, "editor")
    return slug


def providers(person, slug):
    return {p["provider"]: p for p in person.get(f"/workspaces/{slug}/providers").json()}


def test_an_owner_stores_a_key_and_only_its_end_comes_back(alice, workspace):
    response = alice.put(
        f"/workspaces/{workspace}/providers/mistral/key", json={"api_key": SECRET}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "workspace"
    assert body["key_hint"] == SECRET[-4:]
    assert SECRET not in response.text
    listed = providers(alice, workspace)["mistral"]
    assert (listed["configured"], listed["source"], listed["key_hint"]) == (
        True,
        "workspace",
        SECRET[-4:],
    )
    assert SECRET not in alice.get(f"/workspaces/{workspace}/providers").text


def test_the_key_is_encrypted_at_rest(alice, workspace, engine):
    alice.put(f"/workspaces/{workspace}/providers/mistral/key", json={"api_key": SECRET})

    with Session(engine) as db:
        row = db.exec(select(WorkspaceCredential)).one()
    assert SECRET not in row.ciphertext
    assert credentials.decrypt(row.ciphertext) == SECRET


def test_only_owners_manage_keys_but_everyone_sees_their_status(alice, bob, workspace):
    url = f"/workspaces/{workspace}/providers/mistral/key"

    assert bob.put(url, json={"api_key": SECRET}).status_code == 403
    assert bob.delete(url).status_code == 403
    alice.put(url, json={"api_key": SECRET})
    assert providers(bob, workspace)["mistral"]["source"] == "workspace"


def test_a_stranger_cannot_even_tell_the_workspace_exists(alice, bob):
    slug = alice.create_workspace("Private")

    response = bob.put(f"/workspaces/{slug}/providers/mistral/key", json={"api_key": SECRET})

    assert response.status_code == 404


def test_keys_do_not_cross_workspaces(alice, workspace):
    other = alice.create_workspace("Other")
    alice.put(f"/workspaces/{workspace}/providers/mistral/key", json={"api_key": SECRET})

    assert providers(alice, other)["mistral"]["source"] is None


def test_without_its_own_key_a_workspace_uses_the_instances(alice, workspace, monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "instance-key-value")

    assert providers(alice, workspace)["mistral"]["source"] == "instance"
    alice.put(f"/workspaces/{workspace}/providers/mistral/key", json={"api_key": SECRET})
    assert providers(alice, workspace)["mistral"]["source"] == "workspace"
    alice.delete(f"/workspaces/{workspace}/providers/mistral/key")
    assert providers(alice, workspace)["mistral"]["source"] == "instance"


def test_replacing_a_key_keeps_a_single_one(alice, workspace, engine):
    url = f"/workspaces/{workspace}/providers/mistral/key"
    alice.put(url, json={"api_key": SECRET})
    alice.put(url, json={"api_key": "another-key-9999"})

    with Session(engine) as db:
        (row,) = db.exec(select(WorkspaceCredential)).all()
    assert row.last4 == "9999"


@pytest.mark.parametrize("bad", ["", "short", "has a space in it", "x" * 600])
def test_something_that_is_not_a_key_is_refused(alice, workspace, bad):
    response = alice.put(
        f"/workspaces/{workspace}/providers/mistral/key", json={"api_key": bad}
    )

    assert response.status_code == 422


def test_a_self_hosted_provider_takes_no_workspace_key(alice, workspace):
    response = alice.put(
        f"/workspaces/{workspace}/providers/ollama/key", json={"api_key": SECRET}
    )

    assert response.status_code == 422
    assert providers(alice, workspace)["ollama"]["can_store_key"] is False


def test_an_unknown_provider_is_a_404(alice, workspace):
    response = alice.put(
        f"/workspaces/{workspace}/providers/nope/key", json={"api_key": SECRET}
    )

    assert response.status_code == 404


def test_deleting_a_key_that_is_not_there_is_a_404(alice, workspace):
    assert alice.delete(f"/workspaces/{workspace}/providers/mistral/key").status_code == 404


def test_without_an_encryption_key_nothing_can_be_stored(alice, workspace, monkeypatch):
    monkeypatch.setattr(config, "ENCRYPTION_KEY", "")

    response = alice.put(
        f"/workspaces/{workspace}/providers/mistral/key", json={"api_key": SECRET}
    )

    assert response.status_code == 503
    assert providers(alice, workspace)["mistral"]["can_store_key"] is False


def test_a_weak_encryption_key_stops_the_app_from_starting(monkeypatch):
    monkeypatch.setattr(config, "ENCRYPTION_KEY", "too short")

    with pytest.raises(credentials.CredentialError):
        credentials.check_config()


class TestAccessTo:
    def access(self, engine, workspace_id, provider="mistral"):
        from tests.conftest import scoped

        with scoped(engine, workspace_id) as s:
            return credentials.access_to(s, provider)

    def store(self, engine, workspace_id, key=SECRET):
        from tests.conftest import scoped

        with scoped(engine, workspace_id) as s:
            credentials.set_key(s, "mistral", key)

    def test_the_workspace_key_is_used_and_has_its_own_quota(self, engine):
        self.store(engine, 1)

        access = self.access(engine, 1)

        assert (access.source, access.api_key) == ("workspace", SECRET)
        assert access.key_id.startswith("key:") and SECRET not in access.key_id

    def test_the_instance_key_is_left_to_the_environment(self, engine, monkeypatch):
        monkeypatch.setenv("MISTRAL_API_KEY", "instance-key-value")

        access = self.access(engine, 1)

        assert (access.source, access.api_key, access.key_id) == ("instance", None, "instance")

    def test_nothing_configured_is_said_so(self, engine):
        assert self.access(engine, 1).source is None

    def test_a_key_that_can_no_longer_be_decrypted_falls_back(self, engine, monkeypatch):
        self.store(engine, 1)
        monkeypatch.setattr(config, "ENCRYPTION_KEY", "z" * 40)
        monkeypatch.setenv("MISTRAL_API_KEY", "instance-key-value")

        assert self.access(engine, 1).source == "instance"

    def test_two_workspaces_with_the_same_key_share_its_quota(self, engine):
        from sqlalchemy import text

        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO workspace (slug, name, created_at) VALUES ('b', 'B', now())")
            )
        self.store(engine, 1)
        self.store(engine, 2)

        assert self.access(engine, 1).key_id == self.access(engine, 2).key_id


class TestWithoutInstanceFallback:
    @pytest.fixture(autouse=True)
    def no_fallback(self, monkeypatch):
        monkeypatch.setattr(config, "PROVIDERS_INSTANCE_FALLBACK", False)
        monkeypatch.setenv("MISTRAL_API_KEY", "instance-key-value")
        monkeypatch.setenv("OLLAMA_API_BASE", "http://localhost:11434")

    def test_the_instance_key_is_not_offered_to_workspaces(self, alice, workspace):
        listed = providers(alice, workspace)

        assert listed["mistral"]["configured"] is False
        assert listed["mistral"]["source"] is None

    def test_a_workspace_key_still_works(self, alice, workspace):
        alice.put(f"/workspaces/{workspace}/providers/mistral/key", json={"api_key": SECRET})

        assert providers(alice, workspace)["mistral"]["source"] == "workspace"

    def test_a_self_hosted_provider_stays_instance_wide(self, alice, workspace):
        assert providers(alice, workspace)["ollama"]["source"] == "instance"

    def test_a_run_without_its_own_key_fails_instead_of_using_the_instances(self, engine):
        from tests.conftest import scoped

        with scoped(engine) as s:
            access = credentials.access_to(s, "mistral")

        assert access.source is None
        assert access.api_key is None
        assert "no mistral API key" in access.error


def test_an_agent_without_access_fails_before_calling_the_provider(monkeypatch):
    import asyncio

    from core import orchestrator
    from core.orchestrator import AgentConfig

    async def must_not_be_called(**_):
        raise AssertionError("the provider was called")

    monkeypatch.setattr(orchestrator, "call_llm", must_not_be_called)
    agent = AgentConfig(
        name="a", team_name="t", system_prompt=None, user_prompt="hi", variables=[],
        model="m", provider="mistral", access_error="no key here",
    )

    trace = asyncio.run(orchestrator._execute_agent(agent, {}))

    assert trace.error == "no key here"


def test_a_provider_error_never_carries_the_workspace_key(monkeypatch):
    import asyncio

    from core import orchestrator
    from core.orchestrator import AgentConfig

    async def refuses(**kwargs):
        raise RuntimeError(f"401 for key={kwargs['api_key']} on https://api.example")

    monkeypatch.setattr(orchestrator, "call_llm", refuses)
    agent = AgentConfig(
        name="a", team_name="t", system_prompt=None, user_prompt="hi", variables=[],
        model="m", provider="mistral", api_key=SECRET,
    )

    trace = asyncio.run(orchestrator._execute_agent(agent, {}))

    assert SECRET not in trace.error
    assert "[API key]" in trace.error
