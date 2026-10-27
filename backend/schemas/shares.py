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
Request and response models for the public links API
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

ShareKind = Literal["experiment", "batch", "analysis", "study"]


class ShareCreate(BaseModel):
    kind: ShareKind
    item_id: int


class ShareResponse(BaseModel):
    id: int
    kind: ShareKind
    item_id: int
    # The part of the link after /s/: whoever has it can read the item
    token: str
    created_at: datetime


class SharedRoot(BaseModel):
    """What a link points to, as its page needs to start."""

    kind: ShareKind
    item_id: int
    name: str
