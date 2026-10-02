from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from db import get_session
from schemas.prompts import (
    PromptCreate,
    PromptDetail,
    PromptUpdate,
    PromptVersionCreate,
    PromptVersionResponse,
    PromptVersionUpdate,
)
from tables import Prompt, PromptVersion, Tag
from tag_utils import clear_item_tags, item_tags, set_item_tags, tags_by_item

router = APIRouter(tags=["prompts"])


def _detail(prompt: Prompt, tags: list[Tag]) -> PromptDetail:
    return PromptDetail.model_validate(prompt, from_attributes=True).model_copy(
        update={"tags": tags}
    )


# Prompt endpoints
@router.get("/prompts", response_model=list[PromptDetail])
def list_prompts(session: Annotated[Session, Depends(get_session)]):
    prompts = session.exec(select(Prompt)).all()
    tags = tags_by_item(session, "prompt", [p.id for p in prompts if p.id])
    return [_detail(p, tags.get(p.id or 0, [])) for p in prompts]


@router.post("/prompts", response_model=PromptDetail, status_code=201)
def create_prompt(
    prompt_data: PromptCreate, session: Annotated[Session, Depends(get_session)]
):
    prompt = Prompt(
        name=prompt_data.name,
        description=prompt_data.description,
        category=prompt_data.category,
    )
    session.add(prompt)
    session.flush()
    set_item_tags(session, "prompt", prompt.id or 0, prompt_data.tag_ids)
    session.commit()
    session.refresh(prompt)
    return _detail(prompt, item_tags(session, "prompt", prompt.id or 0))


@router.get("/prompts/{prompt_id}", response_model=PromptDetail)
def get_prompt(prompt_id: int, session: Annotated[Session, Depends(get_session)]):
    prompt = session.get(Prompt, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return _detail(prompt, item_tags(session, "prompt", prompt_id))


@router.put("/prompts/{prompt_id}", response_model=PromptDetail)
def update_prompt(
    prompt_id: int,
    prompt_data: PromptUpdate,
    session: Annotated[Session, Depends(get_session)],
):
    prompt = session.get(Prompt, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    changes = prompt_data.model_dump(exclude_unset=True)
    tag_ids = changes.pop("tag_ids", None)
    for field, value in changes.items():
        setattr(prompt, field, value)
    if tag_ids is not None:
        set_item_tags(session, "prompt", prompt_id, tag_ids)

    session.add(prompt)
    session.commit()
    session.refresh(prompt)
    return _detail(prompt, item_tags(session, "prompt", prompt_id))


@router.delete("/prompts/{prompt_id}")
def delete_prompt(prompt_id: int, session: Annotated[Session, Depends(get_session)]):
    prompt = session.get(Prompt, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    clear_item_tags(session, "prompt", prompt_id)
    session.delete(prompt)
    session.commit()
    return {"message": "Prompt deleted successfully"}


# Prompt Version endpoints
@router.get("/prompt-versions", response_model=list[PromptVersionResponse])
def list_all_prompt_versions(session: Annotated[Session, Depends(get_session)]):
    """Get all prompt versions across all prompts for dropdown selections"""
    # Use JOIN to include prompt data in the query
    query = select(PromptVersion).join(Prompt).where(PromptVersion.is_active)
    versions = session.exec(query).all()

    # Explicitly load prompt relationship for each version
    for version in versions:
        if version.prompt_id and not version.prompt:
            version.prompt = session.get(Prompt, version.prompt_id)

    return versions


@router.get("/prompts/{prompt_id}/versions", response_model=list[PromptVersion])
def list_prompt_versions(
    prompt_id: int, session: Annotated[Session, Depends(get_session)]
):
    return session.exec(
        select(PromptVersion).where(PromptVersion.prompt_id == prompt_id)
    ).all()


@router.post(
    "/prompts/{prompt_id}/versions", response_model=PromptVersion, status_code=201
)
def create_prompt_version(
    prompt_id: int,
    version_data: PromptVersionCreate,
    session: Annotated[Session, Depends(get_session)],
):
    # Check if prompt exists
    prompt = session.get(Prompt, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    # If this is marked as default, unset other defaults
    if version_data.is_default:
        existing_defaults = session.exec(
            select(PromptVersion).where(
                PromptVersion.prompt_id == prompt_id,
                PromptVersion.is_default,
            )
        ).all()
        for default_version in existing_defaults:
            default_version.is_default = False
            session.add(default_version)

    version = PromptVersion(
        prompt_id=prompt_id,
        version=version_data.version,
        system_prompt=version_data.system_prompt,
        user_prompt=version_data.user_prompt,
        variables=version_data.variables,
        is_active=version_data.is_active,
        is_default=version_data.is_default,
        notes=version_data.notes,
    )
    session.add(version)
    session.commit()
    session.refresh(version)
    return version


@router.get("/prompt-versions/{version_id}", response_model=PromptVersion)
def get_prompt_version(
    version_id: int, session: Annotated[Session, Depends(get_session)]
):
    version = session.get(PromptVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Prompt version not found")
    return version


@router.put("/prompt-versions/{version_id}", response_model=PromptVersion)
def update_prompt_version(
    version_id: int,
    version_data: PromptVersionUpdate,
    session: Annotated[Session, Depends(get_session)],
):
    version = session.get(PromptVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Prompt version not found")

    # If setting as default, unset other defaults for the same prompt
    if version_data.is_default:
        existing_defaults = session.exec(
            select(PromptVersion).where(
                PromptVersion.prompt_id == version.prompt_id,
                PromptVersion.is_default,
                PromptVersion.id != version_id,
            )
        ).all()
        for default_version in existing_defaults:
            default_version.is_default = False
            session.add(default_version)

    for field, value in version_data.model_dump(exclude_unset=True).items():
        setattr(version, field, value)

    session.add(version)
    session.commit()
    session.refresh(version)
    return version


@router.delete("/prompt-versions/{version_id}")
def delete_prompt_version(
    version_id: int, session: Annotated[Session, Depends(get_session)]
):
    version = session.get(PromptVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Prompt version not found")

    session.delete(version)
    session.commit()
    return {"message": "Prompt version deleted successfully"}
