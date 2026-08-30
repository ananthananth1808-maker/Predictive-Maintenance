from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from app.models.maintenance_record import MaintenanceRecord


class MaintenanceService:
    @staticmethod
    def list_records(db: Session):
        return db.query(MaintenanceRecord).order_by(MaintenanceRecord.maintenance_date.desc()).all()

    @staticmethod
    def create_record(db: Session, payload: dict):
        record = MaintenanceRecord(
            machine_id=payload["machine_id"],
            maintenance_type=payload["maintenance_type"],
            description=payload["description"],
            technician=payload["technician"],
            maintenance_date=payload.get("maintenance_date", datetime.utcnow()),
            cost=payload.get("cost", 0.0),
            status=payload.get("status", "SCHEDULED"),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
