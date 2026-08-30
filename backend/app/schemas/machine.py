from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MachineCreate(BaseModel):
    machine_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)
    location: str = Field(..., min_length=1)
    installation_date: datetime
    status: str = "ACTIVE"


class MachineRead(BaseModel):
    id: int
    machine_id: str
    name: str
    type: str
    location: str
    installation_date: datetime
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
