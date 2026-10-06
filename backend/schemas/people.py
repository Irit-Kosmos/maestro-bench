"""Who did something, as the API names them."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class PersonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    display_name: str
    avatar_url: str | None = None
