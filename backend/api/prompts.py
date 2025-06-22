from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from db import get_session
from models import Prompt, PromptVersion
from schemas.prompts import PromptCreate, PromptUpdate, PromptVersionCreate, PromptVersionUpdate

router = APIRouter(tags=["prompts"])

# Prompt endpoints
@router.get("/prompts", response_model=list[Prompt])
def list_prompts(session=Depends(get_session)):
    return session.exec(select(Prompt)).all()

@router.post("/prompts", response_model=Prompt, status_code=201)
def create_prompt(prompt_data: PromptCreate, session=Depends(get_session)):
    prompt = Prompt(
        name=prompt_data.name,
        description=prompt_data.description,
        category=prompt_data.category
    )
    session.add(prompt)
    session.commit()
    session.refresh(prompt)
    return prompt

@router.get("/prompts/{prompt_id}", response_model=Prompt)
def get_prompt(prompt_id: int, session=Depends(get_session)):
    prompt = session.get(Prompt, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt

@router.put("/prompts/{prompt_id}", response_model=Prompt)
def update_prompt(prompt_id: int, prompt_data: PromptUpdate, session=Depends(get_session)):
    prompt = session.get(Prompt, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    for field, value in prompt_data.model_dump(exclude_unset=True).items():
        setattr(prompt, field, value)
    
    session.add(prompt)
    session.commit()
    session.refresh(prompt)
    return prompt

@router.delete("/prompts/{prompt_id}")
def delete_prompt(prompt_id: int, session=Depends(get_session)):
    prompt = session.get(Prompt, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    session.delete(prompt)
    session.commit()
    return {"message": "Prompt deleted successfully"}

# Prompt Version endpoints
@router.get("/prompt-versions", response_model=list[PromptVersion])
def list_all_prompt_versions(session=Depends(get_session)):
    """Get all prompt versions across all prompts for dropdown selections"""
    query = select(PromptVersion).where(PromptVersion.is_active == True)
    versions = session.exec(query).all()
    
    # Load prompt relationship manually if needed
    for version in versions:
        if version.prompt_id:
            version.prompt = session.get(Prompt, version.prompt_id)
    
    return versions

@router.get("/prompts/{prompt_id}/versions", response_model=list[PromptVersion])
def list_prompt_versions(prompt_id: int, session=Depends(get_session)):
    return session.exec(select(PromptVersion).where(PromptVersion.prompt_id == prompt_id)).all()

@router.post("/prompts/{prompt_id}/versions", response_model=PromptVersion, status_code=201)
def create_prompt_version(prompt_id: int, version_data: PromptVersionCreate, session=Depends(get_session)):
    # Check if prompt exists
    prompt = session.get(Prompt, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    # If this is marked as default, unset other defaults
    if version_data.is_default:
        existing_defaults = session.exec(
            select(PromptVersion).where(
                PromptVersion.prompt_id == prompt_id,
                PromptVersion.is_default == True
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
        notes=version_data.notes
    )
    session.add(version)
    session.commit()
    session.refresh(version)
    return version

@router.get("/prompt-versions/{version_id}", response_model=PromptVersion)
def get_prompt_version(version_id: int, session=Depends(get_session)):
    version = session.get(PromptVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Prompt version not found")
    return version

@router.put("/prompt-versions/{version_id}", response_model=PromptVersion)
def update_prompt_version(version_id: int, version_data: PromptVersionUpdate, session=Depends(get_session)):
    version = session.get(PromptVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Prompt version not found")
    
    # If setting as default, unset other defaults for the same prompt
    if version_data.is_default:
        existing_defaults = session.exec(
            select(PromptVersion).where(
                PromptVersion.prompt_id == version.prompt_id,
                PromptVersion.is_default == True,
                PromptVersion.id != version_id
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
def delete_prompt_version(version_id: int, session=Depends(get_session)):
    version = session.get(PromptVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Prompt version not found")
    
    session.delete(version)
    session.commit()
    return {"message": "Prompt version deleted successfully"}
