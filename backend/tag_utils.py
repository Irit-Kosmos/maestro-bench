"""Tags shared by prompts, analyses and agents: the palette and the helpers that read and write links."""

from collections.abc import Iterable
from typing import Literal, get_args

from fastapi import HTTPException
from sqlmodel import Session, col, delete, select

from tables import Agent, Analysis, Prompt, Tag, TagLink

# Mid-scale hues that read on both light and dark surfaces; the frontend maps each to a dot colour
TagColor = Literal[
    "red",
    "orange",
    "amber",
    "green",
    "teal",
    "blue",
    "indigo",
    "purple",
    "pink",
    "gray",
]
TAG_COLORS: tuple[str, ...] = get_args(TagColor)

TaggedKind = Literal["prompt", "analysis", "agent"]


def normalize_tag_name(name: str) -> str:
    """Trimmed, with inner whitespace collapsed: "  my   tag " and "my tag" are the same tag."""
    return " ".join(name.split())


def tags_by_item(
    session: Session, kind: TaggedKind, item_ids: Iterable[int]
) -> dict[int, list[Tag]]:
    """The tags of each item, by name. Items without a tag are left out."""
    ids = list(item_ids)
    if not ids:
        return {}
    rows = session.exec(
        select(TagLink.item_id, Tag)
        .join(Tag, col(Tag.id) == col(TagLink.tag_id))
        .where(TagLink.kind == kind, col(TagLink.item_id).in_(ids))
    ).all()
    found: dict[int, list[Tag]] = {}
    for item_id, tag in rows:
        found.setdefault(item_id, []).append(tag)
    for tags in found.values():
        tags.sort(key=lambda tag: tag.name.lower())
    return found


def item_tags(session: Session, kind: TaggedKind, item_id: int) -> list[Tag]:
    return tags_by_item(session, kind, [item_id]).get(item_id, [])


def set_item_tags(
    session: Session, kind: TaggedKind, item_id: int, tag_ids: Iterable[int]
) -> None:
    """Make `tag_ids` the tags of the item. Nothing is committed."""
    wanted = set(tag_ids)
    if wanted:
        known = set(session.exec(select(Tag.id).where(col(Tag.id).in_(wanted))).all())
        if missing := wanted - known:
            raise HTTPException(
                status_code=422, detail=f"Unknown tags: {sorted(missing)}"
            )
    current = set(
        session.exec(
            select(TagLink.tag_id).where(
                TagLink.kind == kind, TagLink.item_id == item_id
            )
        ).all()
    )
    if removed := current - wanted:
        session.exec(
            delete(TagLink).where(
                TagLink.kind == kind,
                TagLink.item_id == item_id,
                col(TagLink.tag_id).in_(removed),
            )
        )
    for tag_id in wanted - current:
        session.add(TagLink(tag_id=tag_id, kind=kind, item_id=item_id))


def clear_item_tags(session: Session, kind: TaggedKind, item_id: int) -> None:
    """Drop the links of an item that is being deleted. Nothing is committed."""
    session.exec(
        delete(TagLink).where(TagLink.kind == kind, TagLink.item_id == item_id)
    )


def add_and_remove_tags(
    session: Session,
    kind: TaggedKind,
    item_ids: Iterable[int],
    add: Iterable[int],
    remove: Iterable[int],
) -> None:
    """Put the `add` tags on every item and take the `remove` tags off, leaving their other tags be.

    A tag in both lists is added. Nothing is committed.
    """
    items = set(item_ids)
    to_add = set(add)
    to_remove = set(remove) - to_add

    table = {"prompt": Prompt, "analysis": Analysis, "agent": Agent}[kind]
    known_items = set(
        session.exec(select(table.id).where(col(table.id).in_(items))).all()
    )
    if missing := items - known_items:
        raise HTTPException(
            status_code=422, detail=f"Unknown {kind}s: {sorted(missing)}"
        )
    tag_ids = to_add | to_remove
    known_tags = set(session.exec(select(Tag.id).where(col(Tag.id).in_(tag_ids))).all())
    if missing := tag_ids - known_tags:
        raise HTTPException(status_code=422, detail=f"Unknown tags: {sorted(missing)}")

    if to_remove:
        session.exec(
            delete(TagLink).where(
                TagLink.kind == kind,
                col(TagLink.item_id).in_(items),
                col(TagLink.tag_id).in_(to_remove),
            )
        )
    if to_add:
        present = set(
            session.exec(
                select(TagLink.item_id, TagLink.tag_id).where(
                    TagLink.kind == kind,
                    col(TagLink.item_id).in_(items),
                    col(TagLink.tag_id).in_(to_add),
                )
            ).all()
        )
        for item_id in items:
            for tag_id in to_add:
                if (item_id, tag_id) not in present:
                    session.add(TagLink(tag_id=tag_id, kind=kind, item_id=item_id))
