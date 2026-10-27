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
Request and response models for prompts API
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, ConfigDict

from schemas.tags import TagResponse


def _json_or_none(value: str | None) -> str | None:
    """The variables are kept as JSON: blank means none, anything else must parse."""
    if value is None or not value.strip():
        return None
    try:
        json.loads(value)
    except ValueError as e:
        raise ValueError("must be valid JSON") from e
    return value


JsonString = Annotated[str | None, AfterValidator(_json_or_none)]


class PromptCreate(BaseModel):
    name: str
    description: str | None = None
    tag_ids: list[int] = []


class PromptUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    # Left out: the tags stay as they are. Sent: they become exactly these.
    tag_ids: list[int] | None = None


class PromptRenderRequest(BaseModel):
    system_prompt: str | None = None
    user_prompt: str | None = None
    # Value of each variable, as the agent would receive it
    variables: dict[str, Any] = {}


class PromptRenderResponse(BaseModel):
    system: str
    user: str


class PromptVersionCreate(BaseModel):
    version: str
    system_prompt: str | None = None
    user_prompt: str | None = None
    variables: JsonString = None
    is_active: bool = True
    is_default: bool = False
    notes: str | None = None


class PromptVersionUpdate(BaseModel):
    version: str | None = None
    system_prompt: str | None = None
    user_prompt: str | None = None
    variables: JsonString = None
    is_active: bool | None = None
    is_default: bool | None = None
    notes: str | None = None


class PromptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    created_at: datetime


class PromptDetail(PromptResponse):
    """A prompt with its tags (the tags are not read where a prompt only gives context)"""

    tags: list[TagResponse] = []


class PromptVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    prompt_id: int
    version: str
    system_prompt: str | None
    user_prompt: str | None
    variables: str | None
    is_active: bool
    is_default: bool
    notes: str | None
    created_at: datetime
    prompt: PromptResponse | None = None


# Rebuild for forward references
PromptVersionResponse.model_rebuild()
