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

"""Checks that the rows a request points to exist in the request's workspace."""

from collections.abc import Iterable

from sqlmodel import Session, SQLModel, col, select


def missing_ids(session: Session, table: type[SQLModel], ids: Iterable[object]) -> list:
    """The ids that are not rows of `table` in the session's workspace.

    The session is scoped, so a row of another workspace counts as missing: a
    request can never hold on to something it should not see. Anything that is
    not an integer id is reported as missing too.
    """
    wanted = set()
    invalid = set()
    for value in ids:
        if isinstance(value, bool) or not isinstance(value, int):
            invalid.add(value)
        else:
            wanted.add(value)
    found = (
        set(session.exec(select(table.id).where(col(table.id).in_(wanted))).all())
        if wanted
        else set()
    )
    return sorted(wanted - found) + sorted(invalid, key=str)
