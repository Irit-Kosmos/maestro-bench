
from fastapi import APIRouter, HTTPException
from jinja2 import TemplateError
from sqlalchemy.orm import selectinload
from sqlmodel import select

from auth.workspaces import requires
from core.prompt_renderer import render_prompt
from db import SessionDep
from schemas.prompts import (
    PromptCreate,
    PromptDetail,
    PromptRenderRequest,
    PromptRenderResponse,
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
def list_prompts(session: SessionDep):
    prompts = session.exec(select(Prompt)).all()
    tags = tags_by_item(session, "prompt", [p.id for p in prompts if p.id])
    return [_detail(p, tags.get(p.id or 0, [])) for p in prompts]


@router.post("/prompts", response_model=PromptDetail, status_code=201)
def create_prompt(
    prompt_data: PromptCreate, session: SessionDep
):
    prompt = Prompt(
        name=prompt_data.name,
        description=prompt_data.description,
    )
    session.add(prompt)
    session.flush()
    set_item_tags(session, "prompt", prompt.id or 0, prompt_data.tag_ids)
    session.commit()
    session.refresh(prompt)
    return _detail(prompt, item_tags(session, "prompt", prompt.id or 0))


@router.post("/prompts/render", response_model=PromptRenderResponse)
@requires("viewer")
def render_prompts(request: PromptRenderRequest):
    """
    The prompts as an agent would receive them, rendered with these values.

    Nothing is stored or sent to a model, so reading access is enough. The template
    comes from the request, so it renders in Jinja's sandbox.
    """
    try:
        return PromptRenderResponse(
            system=render_prompt(
                request.system_prompt or "", request.variables, sandboxed=True
            ),
            user=render_prompt(
                request.user_prompt or "", request.variables, sandboxed=True
            ),
        )
    except TemplateError as e:
        raise HTTPException(422, f"The prompt cannot be rendered: {e}") from e


@router.get("/prompts/{prompt_id}", response_model=PromptDetail)
def get_prompt(prompt_id: int, session: SessionDep):
    prompt = session.get(Prompt, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return _detail(prompt, item_tags(session, "prompt", prompt_id))


@router.put("/prompts/{prompt_id}", response_model=PromptDetail)
def update_prompt(
    prompt_id: int,
    prompt_data: PromptUpdate,
    session: SessionDep,
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


@router.delete("/prompts/{prompt_id}", status_code=204)
def delete_prompt(prompt_id: int, session: SessionDep):
    prompt = session.get(Prompt, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    clear_item_tags(session, "prompt", prompt_id)
    session.delete(prompt)
    session.commit()


# Prompt Version endpoints
@router.get("/prompt-versions", response_model=list[PromptVersionResponse])
def list_all_prompt_versions(session: SessionDep):
    """Get all prompt versions across all prompts for dropdown selections"""
    query = (
        select(PromptVersion)
        .where(PromptVersion.is_active)
        .options(selectinload(PromptVersion.prompt))
    )
    return session.exec(query).all()


@router.get("/prompts/{prompt_id}/versions", response_model=list[PromptVersion])
def list_prompt_versions(
    prompt_id: int, session: SessionDep
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
    session: SessionDep,
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
    version_id: int, session: SessionDep
):
    version = session.get(PromptVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Prompt version not found")
    return version


@router.put("/prompt-versions/{version_id}", response_model=PromptVersion)
def update_prompt_version(
    version_id: int,
    version_data: PromptVersionUpdate,
    session: SessionDep,
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


@router.delete("/prompt-versions/{version_id}", status_code=204)
def delete_prompt_version(
    version_id: int, session: SessionDep
):
    version = session.get(PromptVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Prompt version not found")

    session.delete(version)
    session.commit()
