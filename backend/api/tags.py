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

from fastapi import APIRouter, HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, delete, select

from db import SessionDep
from schemas.tags import TagAssign, TagCreate, TagResponse, TagUpdate
from tables import Tag, TagLink
from tag_utils import add_and_remove_tags, normalize_tag_name

router = APIRouter(tags=["tags"])


def _name_taken(session: Session, name: str, except_id: int | None = None) -> bool:
    query = select(Tag.id).where(func.lower(Tag.name) == name.lower())
    if except_id is not None:
        query = query.where(Tag.id != except_id)
    return session.exec(query).first() is not None


def _checked_name(name: str) -> str:
    cleaned = normalize_tag_name(name)
    if not cleaned:
        raise HTTPException(status_code=422, detail="A tag needs a name")
    return cleaned


def _commit(session: Session, name: str) -> None:
    """Commit; the unique index catches a same-named tag created since `_name_taken` looked."""
    try:
        session.commit()
    except IntegrityError as e:
        session.rollback()
        raise HTTPException(
            status_code=409, detail=f'Tag "{name}" already exists'
        ) from e


@router.get("/tags", response_model=list[TagResponse])
def list_tags(session: SessionDep):
    """Every tag, by name."""
    return sorted(session.exec(select(Tag)).all(), key=lambda t: t.name.lower())


@router.post("/tags", response_model=TagResponse, status_code=201)
def create_tag(data: TagCreate, session: SessionDep):
    name = _checked_name(data.name)
    if _name_taken(session, name):
        raise HTTPException(status_code=409, detail=f'Tag "{name}" already exists')
    tag = Tag(name=name, color=data.color)
    session.add(tag)
    _commit(session, name)
    session.refresh(tag)
    return tag


@router.post("/tags/assign", status_code=204)
def assign_tags(data: TagAssign, session: SessionDep):
    """Put tags on several items, take tags off them, or both, in one go."""
    add_and_remove_tags(session, data.kind, data.item_ids, data.add, data.remove)
    session.commit()


@router.put("/tags/{tag_id}", response_model=TagResponse)
def update_tag(
    tag_id: int, data: TagUpdate, session: SessionDep
):
    tag = session.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    if data.name is not None:
        name = _checked_name(data.name)
        if _name_taken(session, name, except_id=tag_id):
            raise HTTPException(status_code=409, detail=f'Tag "{name}" already exists')
        tag.name = name
    if data.color is not None:
        tag.color = data.color
    session.add(tag)
    _commit(session, tag.name)
    session.refresh(tag)
    return tag


@router.delete("/tags/{tag_id}", status_code=204)
def delete_tag(tag_id: int, session: SessionDep):
    """Delete a tag and take it off every item that carried it."""
    tag = session.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    session.exec(delete(TagLink).where(col(TagLink.tag_id) == tag_id))
    session.delete(tag)
    session.commit()
