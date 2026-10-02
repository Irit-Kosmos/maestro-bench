from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlmodel import Session, col, delete, select

from db import get_session
from schemas.tags import TagCreate, TagResponse, TagUpdate, TagWithCount
from tables import Tag, TagLink
from tag_utils import normalize_tag_name

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


@router.get("/tags", response_model=list[TagWithCount])
def list_tags(session: Annotated[Session, Depends(get_session)]):
    """Every tag with the number of items carrying it, by name."""
    counts = dict(
        session.exec(
            select(TagLink.tag_id, func.count()).group_by(TagLink.tag_id)
        ).all()
    )
    tags = sorted(session.exec(select(Tag)).all(), key=lambda t: t.name.lower())
    return [
        TagWithCount(
            id=t.id or 0, name=t.name, color=t.color, count=counts.get(t.id, 0)
        )
        for t in tags
    ]


@router.post("/tags", response_model=TagResponse, status_code=201)
def create_tag(data: TagCreate, session: Annotated[Session, Depends(get_session)]):
    name = _checked_name(data.name)
    if _name_taken(session, name):
        raise HTTPException(status_code=409, detail=f'Tag "{name}" already exists')
    tag = Tag(name=name, color=data.color)
    session.add(tag)
    session.commit()
    session.refresh(tag)
    return tag


@router.put("/tags/{tag_id}", response_model=TagResponse)
def update_tag(
    tag_id: int, data: TagUpdate, session: Annotated[Session, Depends(get_session)]
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
    session.commit()
    session.refresh(tag)
    return tag


@router.delete("/tags/{tag_id}")
def delete_tag(tag_id: int, session: Annotated[Session, Depends(get_session)]):
    """Delete a tag and take it off every item that carried it."""
    tag = session.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    session.exec(delete(TagLink).where(col(TagLink.tag_id) == tag_id))
    session.delete(tag)
    session.commit()
    return {"message": "Tag deleted successfully"}
