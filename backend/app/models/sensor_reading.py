from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    machine_id: Mapped[str] = mapped_column(String(50), ForeignKey("machines.machine_id"), nullable=False, index=True)
    air_temperature: Mapped[float] = mapped_column(Float, nullable=False)
    process_temperature: Mapped[float] = mapped_column(Float, nullable=False)
    rotational_speed: Mapped[float] = mapped_column(Float, nullable=False)
    torque: Mapped[float] = mapped_column(Float, nullable=False)
    tool_wear: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
