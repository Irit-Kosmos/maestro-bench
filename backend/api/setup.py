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
API router for the getting-started checklist: what the workspace has set up so far.
"""


from fastapi import APIRouter
from pydantic import BaseModel
from sqlmodel import select

import credentials
from core.llm import SUPPORTED_PROVIDERS
from db import SessionDep
from tables import Agent, Dataset, Experiment, Model, PromptVersion

router = APIRouter(tags=["setup"])


class SetupProgress(BaseModel):
    """One flag per step of the way to a first run, in the order to take them."""

    provider: bool
    dataset: bool
    prompt: bool
    model: bool
    agent: bool
    experiment: bool


@router.get("/setup", response_model=SetupProgress)
def get_setup(session: SessionDep):
    """Which steps of the first run the workspace has taken."""
    stored = credentials.stored_keys(session)

    def has(table) -> bool:
        return session.exec(select(table.id).limit(1)).first() is not None

    return SetupProgress(
        provider=any(
            name in stored or credentials.instance_provides(name)
            for name in SUPPORTED_PROVIDERS
        ),
        dataset=has(Dataset),
        # A prompt does nothing without a version to run
        prompt=has(PromptVersion),
        model=has(Model),
        agent=has(Agent),
        experiment=has(Experiment),
    )
