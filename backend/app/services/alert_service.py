from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.alert import Alert


class AlertService:
    @staticmethod
    def get_alert_severity(probability: float) -> str:
        if probability > 0.70:
            return "CRITICAL"
        if probability >= 0.30:
            return "WARNING"
        return "NORMAL"

    @staticmethod
    def dedupe_alerts(db: Session, machine_id: str, severity: str) -> Optional[Alert]:
        return (
            db.query(Alert)
            .filter(Alert.machine_id == machine_id)
            .filter(Alert.severity == severity)
            .filter(Alert.is_resolved == False)
            .order_by(Alert.created_at.desc())
            .first()
        )

    @staticmethod
    def create_alert(db: Session, machine_id: str, probability: float, health_status: str) -> Optional[Alert]:
        severity = AlertService.get_alert_severity(probability)
        if severity == "NORMAL":
            return None

        existing = AlertService.dedupe_alerts(db, machine_id, severity)
        if existing:
            return None

        title = "Critical failure risk" if severity == "CRITICAL" else "Warning: elevated failure risk"
        message = (
            f"Machine {machine_id} is currently in {health_status} status with a failure probability of {probability:.2f}. "
            "Inspect the machine, review recent readings, and schedule preventive maintenance."
        )

        alert = Alert(
            machine_id=machine_id,
            severity=severity,
            title=title,
            message=message,
            is_resolved=False,
            created_at=datetime.utcnow(),
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert

    @staticmethod
    def resolve_alert(db: Session, alert_id: int) -> Optional[Alert]:
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            return None
        alert.is_resolved = True
        alert.resolved_at = datetime.utcnow()
        db.commit()
        db.refresh(alert)
        return alert
