from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from db import get_session
from models import PromptTemplate

router = APIRouter(tags=["prompts"])

@router.get("/prompts", response_model=list[PromptTemplate])
def list_prompts(session=Depends(get_session)):
    return session.exec(select(PromptTemplate)).all()

@router.post("/prompts", response_model=PromptTemplate, status_code=201)
def create_prompt(prompt: PromptTemplate, session=Depends(get_session)):
    session.add(prompt)
    session.commit()
    session.refresh(prompt)
    return prompt

@router.get("/prompts/{prompt_id}", response_model=PromptTemplate)
def get_prompt(prompt_id: int, session=Depends(get_session)):
    prompt = session.get(PromptTemplate, prompt_id)
    if not prompt:
        raise HTTPException(404, "Prompt not found")
    return prompt

@router.put("/prompts/{prompt_id}", response_model=PromptTemplate)
def update_prompt(prompt_id: int, prompt_data: PromptTemplate, session=Depends(get_session)):
    prompt = session.get(PromptTemplate, prompt_id)
    if not prompt:
        raise HTTPException(404, "Prompt not found")
    
    prompt.name = prompt_data.name
    prompt.type = prompt_data.type
    prompt.value = prompt_data.value
    prompt.description = prompt_data.description
    
    session.add(prompt)
    session.commit()
    session.refresh(prompt)
    return prompt

@router.delete("/prompts/{prompt_id}")
def delete_prompt(prompt_id: int, session=Depends(get_session)):
    prompt = session.get(PromptTemplate, prompt_id)
    if not prompt:
        raise HTTPException(404, "Prompt not found")
    
    session.delete(prompt)
    session.commit()
    
    return {"message": "Prompt deleted successfully"}

@router.get("/prompts/by-type/{prompt_type}", response_model=list[PromptTemplate])
def list_prompts_by_type(prompt_type: str, session=Depends(get_session)):
    """Get prompts filtered by type (content, language, system, user)"""
    return session.exec(
        select(PromptTemplate).where(PromptTemplate.type == prompt_type)
    ).all()
