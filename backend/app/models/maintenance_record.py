from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    machine_id: Mapped[str] = mapped_column(String(50), ForeignKey("machines.machine_id"), nullable=False, index=True)
    maintenance_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    technician: Mapped[str] = mapped_column(String(150), nullable=False)
    maintenance_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(50), default="SCHEDULED")
