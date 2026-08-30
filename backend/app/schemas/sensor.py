from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SensorReadingCreate(BaseModel):
    machine_id: str = Field(..., min_length=1)
    air_temperature: float = Field(..., gt=0)
    process_temperature: float = Field(..., gt=0)
    rotational_speed: float = Field(..., gt=0)
    torque: float = Field(..., gt=0)
    tool_wear: float = Field(..., ge=0)


class SensorReadingRead(BaseModel):
    id: int
    machine_id: str
    air_temperature: float
    process_temperature: float
    rotational_speed: float
    torque: float
    tool_wear: float
    recorded_at: datetime

    class Config:
        from_attributes = True
