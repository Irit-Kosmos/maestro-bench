"""
API router for the getting-started checklist: what the workspace has set up so far.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select

import credentials
from core.llm import SUPPORTED_PROVIDERS
from db import get_session
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
def get_setup(session: Annotated[Session, Depends(get_session)]):
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
