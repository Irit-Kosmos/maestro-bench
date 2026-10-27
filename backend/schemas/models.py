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
Request and response models for models API
"""

from __future__ import annotations

from pydantic import BaseModel


class ModelCreate(BaseModel):
    name: str
    provider: str
    description: str | None = None
    max_tokens: int | None = None
    default_temperature: float | None = 0.7
    default_max_tokens: int | None = None
    is_active: bool = True


class ModelUpdate(BaseModel):
    name: str | None = None
    provider: str | None = None
    description: str | None = None
    max_tokens: int | None = None
    default_temperature: float | None = None
    default_max_tokens: int | None = None
    is_active: bool | None = None



