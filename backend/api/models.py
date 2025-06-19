from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from db import get_session
from models import ModelConfig

router = APIRouter(tags=["models"])

@router.get("/models", response_model=list[ModelConfig])
def list_model_configs(session=Depends(get_session)):
    return session.exec(select(ModelConfig)).all()

@router.post("/models", response_model=ModelConfig, status_code=201)
def create_model_config(model_config: ModelConfig, session=Depends(get_session)):
    session.add(model_config)
    session.commit()
    session.refresh(model_config)
    return model_config

@router.get("/models/{model_id}", response_model=ModelConfig)
def get_model_config(model_id: int, session=Depends(get_session)):
    model_config = session.get(ModelConfig, model_id)
    if not model_config:
        raise HTTPException(404, "Model configuration not found")
    return model_config

@router.put("/models/{model_id}", response_model=ModelConfig)
def update_model_config(model_id: int, model_data: ModelConfig, session=Depends(get_session)):
    model_config = session.get(ModelConfig, model_id)
    if not model_config:
        raise HTTPException(404, "Model configuration not found")
    
    model_config.name = model_data.name
    model_config.model = model_data.model
    model_config.temperature = model_data.temperature
    model_config.max_tokens = model_data.max_tokens
    model_config.top_p = model_data.top_p
    
    session.add(model_config)
    session.commit()
    session.refresh(model_config)
    return model_config

@router.delete("/models/{model_id}")
def delete_model_config(model_id: int, session=Depends(get_session)):
    model_config = session.get(ModelConfig, model_id)
    if not model_config:
        raise HTTPException(404, "Model configuration not found")
    
    session.delete(model_config)
    session.commit()
    
    return {"message": "Model configuration deleted successfully"}
