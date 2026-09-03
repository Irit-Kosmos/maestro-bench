from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from db import get_session
from schemas.models import ModelCreate, ModelUpdate
from tables import Model as ModelTable

router = APIRouter(tags=["models"])


@router.get("/models", response_model=list[ModelTable])
def list_models(session: Annotated[Session, Depends(get_session)]):
    return session.exec(select(ModelTable)).all()


@router.post("/models", response_model=ModelTable, status_code=201)
def create_model(
    model_data: ModelCreate, session: Annotated[Session, Depends(get_session)]
):
    model = ModelTable(
        name=model_data.name,
        provider=model_data.provider,
        description=model_data.description,
        max_tokens=model_data.max_tokens,
        default_temperature=model_data.default_temperature,
        default_max_tokens=model_data.default_max_tokens,
        is_active=model_data.is_active,
    )
    session.add(model)
    session.commit()
    session.refresh(model)
    return model


@router.get("/models/{model_id}", response_model=ModelTable)
def get_model(model_id: int, session: Annotated[Session, Depends(get_session)]):
    model = session.get(ModelTable, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.put("/models/{model_id}", response_model=ModelTable)
def update_model(
    model_id: int,
    model_data: ModelUpdate,
    session: Annotated[Session, Depends(get_session)],
):
    model = session.get(ModelTable, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    for field, value in model_data.model_dump(exclude_unset=True).items():
        setattr(model, field, value)

    session.add(model)
    session.commit()
    session.refresh(model)
    return model


@router.delete("/models/{model_id}")
def delete_model(model_id: int, session: Annotated[Session, Depends(get_session)]):
    model = session.get(ModelTable, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    session.delete(model)
    session.commit()
    return {"message": "Model deleted successfully"}


@router.patch("/models/{model_id}/toggle-status", response_model=ModelTable)
def toggle_model_status(
    model_id: int, session: Annotated[Session, Depends(get_session)]
):
    model = session.get(ModelTable, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    model.is_active = not model.is_active
    session.add(model)
    session.commit()
    session.refresh(model)
    return model
