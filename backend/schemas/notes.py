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
Request and response models for notes API
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from schemas.people import PersonResponse

NoteKind = Literal["experiment", "batch", "analysis", "study"]

BODY_MAX_LENGTH = 50_000


def _not_blank(body: str) -> str:
    if not body.strip():
        raise ValueError("A note cannot be empty")
    return body


class NoteCreate(BaseModel):
    kind: NoteKind
    item_id: int
    body: str = Field(min_length=1, max_length=BODY_MAX_LENGTH)  # markdown

    _body_not_blank = field_validator("body")(_not_blank)


class NoteUpdate(BaseModel):
    body: str = Field(min_length=1, max_length=BODY_MAX_LENGTH)

    _body_not_blank = field_validator("body")(_not_blank)


class NoteResponse(BaseModel):
    id: int
    kind: NoteKind
    item_id: int
    body: str
    # None when the author's account is gone
    author: PersonResponse | None = None
    created_at: datetime
    updated_at: datetime
    # What the caller may do with it: only the author edits, the author or an owner deletes
    can_edit: bool
    can_delete: bool
