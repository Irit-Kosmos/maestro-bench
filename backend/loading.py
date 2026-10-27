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

"""Loading what a list of rows points to, in one query instead of one per row."""

from collections import defaultdict
from collections.abc import Iterable

from sqlmodel import Session, SQLModel, col, select


def by_id[T: SQLModel](
    session: Session, table: type[T], ids: Iterable[int | None]
) -> dict[int, T]:
    """The rows of `table` with these ids, by id; unknown ids and None are left out.

    Keep the result: the session only holds weak references to its rows, so a later
    `session.get` finds them again only while something else refers to them.
    """
    wanted = {i for i in ids if i is not None}
    if not wanted:
        return {}
    rows = session.exec(select(table).where(col(table.id).in_(wanted))).all()
    return {row.id: row for row in rows}


def grouped_by[T: SQLModel](
    session: Session, table: type[T], column: object, ids: Iterable[int], *order: object
) -> dict[int, list[T]]:
    """The rows of `table` whose `column` is one of `ids`, grouped by that column."""
    wanted = set(ids)
    groups: dict[int, list[T]] = defaultdict(list)
    if not wanted:
        return groups
    query = select(table).where(col(column).in_(wanted))
    if order:
        query = query.order_by(*order)
    for row in session.exec(query).all():
        groups[getattr(row, column.key)].append(row)
    return groups
