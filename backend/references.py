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
