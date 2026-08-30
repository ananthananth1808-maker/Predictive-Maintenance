from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MaintenanceCreate(BaseModel):
    machine_id: str = Field(..., min_length=1)
    maintenance_type: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    technician: str = Field(..., min_length=1)
    maintenance_date: datetime
    cost: float = 0.0
    status: str = "SCHEDULED"


class MaintenanceRead(BaseModel):
    id: int
    machine_id: str
    maintenance_type: str
    description: str
    technician: str
    maintenance_date: datetime
    cost: float
    status: str

    class Config:
        from_attributes = True
