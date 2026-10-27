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

import pytest

import config
from auth.policy import (
    AuthConfigError,
    Profile,
    is_allowed,
    is_instance_admin,
    validate_config,
)
from auth.providers import gitlab_profile


def profile(email="remi@irit.fr", groups=()):
    return Profile(
        provider="gitlab", subject="1", display_name="Rémi", email=email, groups=groups
    )


def test_an_email_domain_must_match_exactly():
    assert is_allowed(profile("remi@irit.fr"))
    assert is_allowed(profile("remi@IRIT.fr"))
    assert not is_allowed(profile("remi@evil.irit.fr"))
    assert not is_allowed(profile("remi@irit.fr.evil.com"))
    assert not is_allowed(profile(None))


def test_several_domains_are_alternatives(monkeypatch):
    monkeypatch.setattr(config, "AUTH_ALLOWED_EMAIL_DOMAINS", ["irit.fr", "kosmos.fr"])

    assert is_allowed(profile("remi@kosmos.fr"))
    assert not is_allowed(profile("remi@gmail.com"))


def test_a_group_admits_its_members_and_those_of_its_subgroups(monkeypatch):
    monkeypatch.setattr(config, "AUTH_ALLOWED_EMAIL_DOMAINS", [])
    monkeypatch.setattr(config, "AUTH_GITLAB_ALLOWED_GROUPS", ["irit/team"])

    assert is_allowed(profile(groups=("irit/team",)))
    assert is_allowed(profile(groups=("Irit/Team/sub",)))
    assert not is_allowed(profile(groups=("irit/teammates",)))
    assert not is_allowed(profile(groups=("irit",)))
    assert not is_allowed(profile(groups=()))


def test_every_restriction_that_is_set_must_hold(monkeypatch):
    monkeypatch.setattr(config, "AUTH_GITLAB_ALLOWED_GROUPS", ["irit/team"])

    assert is_allowed(profile("remi@irit.fr", groups=("irit/team",)))
    assert not is_allowed(profile("remi@irit.fr", groups=()))
    assert not is_allowed(profile("remi@gmail.com", groups=("irit/team",)))


def test_without_restriction_only_the_explicit_opt_in_lets_anyone_in(monkeypatch):
    monkeypatch.setattr(config, "AUTH_ALLOWED_EMAIL_DOMAINS", [])
    assert not is_allowed(profile("remi@irit.fr"))

    monkeypatch.setattr(config, "AUTH_ALLOW_ANY_USER", True)
    assert is_allowed(profile("anyone@example.com"))


def test_an_unverified_email_is_not_trusted():
    claims = {"sub": "7", "email": "remi@irit.fr", "email_verified": False}

    assert gitlab_profile(claims).email is None
    assert not is_allowed(gitlab_profile(claims))
    assert gitlab_profile({**claims, "email_verified": True}).email == "remi@irit.fr"


def test_gitlab_profile_reads_the_oidc_claims():
    result = gitlab_profile(
        {
            "sub": 42,
            "name": "Rémi Saurel",
            "email": "Remi@IRIT.fr",
            "email_verified": True,
            "picture": "https://gitlab/avatar.png",
            "groups_direct": ["irit/team"],
        }
    )

    assert result == Profile(
        provider="gitlab",
        subject="42",
        display_name="Rémi Saurel",
        email="remi@irit.fr",
        avatar_url="https://gitlab/avatar.png",
        groups=("irit/team",),
    )


def test_instance_admins_are_matched_ignoring_case(monkeypatch):
    monkeypatch.setattr(config, "INSTANCE_ADMINS", ["remi@kosmos.fr"])

    assert is_instance_admin("Remi@Kosmos.fr")
    assert not is_instance_admin("other@kosmos.fr")
    assert not is_instance_admin(None)


def test_valid_settings_are_accepted():
    validate_config(["gitlab"])


@pytest.mark.parametrize(
    ("setting", "value", "providers", "message"),
    [
        ("SECRET_KEY", "short", ["gitlab"], "SECRET_KEY"),
        ("SECRET_KEY", "", ["gitlab"], "SECRET_KEY"),
        ("FRONTEND_URL", "", ["gitlab"], "FRONTEND_URL"),
        ("AUTH_ALLOWED_EMAIL_DOMAINS", [], ["gitlab"], "nobody is allowed"),
        ("SECRET_KEY", "k" * 48, [], "no identity provider"),
    ],
)
def test_the_app_refuses_to_start_with_unsafe_settings(
    monkeypatch, setting, value, providers, message
):
    monkeypatch.setattr(config, setting, value)

    with pytest.raises(AuthConfigError, match=message):
        validate_config(providers)


def test_accepting_any_user_must_be_asked_for(monkeypatch):
    monkeypatch.setattr(config, "AUTH_ALLOWED_EMAIL_DOMAINS", [])
    monkeypatch.setattr(config, "AUTH_ALLOW_ANY_USER", True)

    validate_config(["gitlab"])
