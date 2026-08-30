from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AlertCreate(BaseModel):
    machine_id: str = Field(..., min_length=1)
    severity: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class AlertRead(BaseModel):
    id: int
    machine_id: str
    severity: str
    title: str
    message: str
    is_resolved: bool
    created_at: datetime
    resolved_at: datetime | None = None

    class Config:
        from_attributes = True
