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
from sqlmodel import select

from db import SessionDep
from schemas.models import ModelCreate, ModelUpdate
from tables import Model as ModelTable

router = APIRouter(tags=["models"])


@router.get("/models", response_model=list[ModelTable])
def list_models(session: SessionDep):
    return session.exec(select(ModelTable)).all()


@router.post("/models", response_model=ModelTable, status_code=201)
def create_model(
    model_data: ModelCreate, session: SessionDep
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
def get_model(model_id: int, session: SessionDep):
    model = session.get(ModelTable, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.put("/models/{model_id}", response_model=ModelTable)
def update_model(
    model_id: int,
    model_data: ModelUpdate,
    session: SessionDep,
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


@router.delete("/models/{model_id}", status_code=204)
def delete_model(model_id: int, session: SessionDep):
    model = session.get(ModelTable, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    session.delete(model)
    session.commit()


@router.patch("/models/{model_id}/toggle-status", response_model=ModelTable)
def toggle_model_status(
    model_id: int, session: SessionDep
):
    model = session.get(ModelTable, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    model.is_active = not model.is_active
    session.add(model)
    session.commit()
    session.refresh(model)
    return model
