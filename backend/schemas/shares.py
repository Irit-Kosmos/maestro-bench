"""
Request and response models for the public links API
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

ShareKind = Literal["experiment", "batch", "analysis", "study"]


class ShareCreate(BaseModel):
    kind: ShareKind
    item_id: int


class ShareResponse(BaseModel):
    id: int
    kind: ShareKind
    item_id: int
    # The part of the link after /s/: whoever has it can read the item
    token: str
    created_at: datetime


class SharedRoot(BaseModel):
    """What a link points to, as its page needs to start."""

    kind: ShareKind
    item_id: int
    name: str
