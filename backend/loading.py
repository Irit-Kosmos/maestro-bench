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
