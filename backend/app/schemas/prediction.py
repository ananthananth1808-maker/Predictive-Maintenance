from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PredictionInput(BaseModel):
    machine_id: str | None = Field(default=None, min_length=1)
    type: str = Field(..., min_length=1)
    air_temperature: float = Field(..., gt=0)
    process_temperature: float = Field(..., gt=0)
    rotational_speed: float = Field(..., gt=0)
    torque: float = Field(..., gt=0)
    tool_wear: float = Field(..., ge=0)


class PredictionResult(BaseModel):
    machine_id: str | None
    failure_probability: float
    health_status: str
    risk_level: str
    created_at: datetime | None = None


class PredictionRead(BaseModel):
    id: int
    machine_id: str
    failure_probability: float
    health_status: str
    model_version: str
    created_at: datetime

    class Config:
        from_attributes = True
