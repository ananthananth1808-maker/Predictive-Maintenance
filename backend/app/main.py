from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import BACKEND_URL, FRONTEND_URL
from app.services.ai_service import AIService
from app.services.alert_service import AlertService
from app.database import Base, SessionLocal, engine, get_db
from app.models.alert import Alert
from app.models.machine import Machine
from app.models.maintenance_record import MaintenanceRecord
from app.models.prediction import Prediction
from app.models.sensor_reading import SensorReading
from app.schemas.alert import AlertRead
from app.schemas.machine import MachineCreate, MachineRead
from app.schemas.maintenance import MaintenanceCreate, MaintenanceRead
from app.schemas.prediction import PredictionInput, PredictionRead, PredictionResult
from app.schemas.sensor import SensorReadingCreate, SensorReadingRead
from app.services.ml_service import MLService

app = FastAPI(title="MaintenAI API", version="1.0.0", description="AI-powered predictive maintenance platform")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)
ml_service = MLService()
ai_service = AIService()


@app.get("/api/v1/health")
def health_check():
    return {"status": "ok", "service": "maintenai-api", "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/v1/machines", response_model=list[MachineRead])
def list_machines(db: Session = Depends(get_db)):
    return db.query(Machine).order_by(Machine.created_at.desc()).all()


@app.get("/api/v1/machines/{machine_id}", response_model=MachineRead)
def get_machine(machine_id: str, db: Session = Depends(get_db)):
    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    return machine


@app.post("/api/v1/machines", response_model=MachineRead, status_code=201)
def create_machine(machine: MachineCreate, db: Session = Depends(get_db)):
    existing = db.query(Machine).filter(Machine.machine_id == machine.machine_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Machine ID already exists")
    record = Machine(
        machine_id=machine.machine_id,
        name=machine.name,
        type=machine.type,
        location=machine.location,
        installation_date=machine.installation_date,
        status=machine.status,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.get("/api/v1/machines/{machine_id}/sensors", response_model=list[SensorReadingRead])
def get_sensor_history(machine_id: str, limit: int = Query(default=50, ge=1, le=500), db: Session = Depends(get_db)):
    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    return (
        db.query(SensorReading)
        .filter(SensorReading.machine_id == machine_id)
        .order_by(SensorReading.recorded_at.desc())
        .limit(limit)
        .all()
    )


@app.get("/api/v1/machines/{machine_id}/predictions", response_model=list[PredictionRead])
def get_machine_predictions(machine_id: str, limit: int = Query(default=50, ge=1, le=500), db: Session = Depends(get_db)):
    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    return (
        db.query(Prediction)
        .filter(Prediction.machine_id == machine_id)
        .order_by(Prediction.created_at.desc())
        .limit(limit)
        .all()
    )


@app.get("/api/v1/machines/{machine_id}/alerts", response_model=list[AlertRead])
def get_machine_alerts(machine_id: str, limit: int = Query(default=50, ge=1, le=500), db: Session = Depends(get_db)):
    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    return (
        db.query(Alert)
        .filter(Alert.machine_id == machine_id)
        .order_by(Alert.created_at.desc())
        .limit(limit)
        .all()
    )


@app.get("/api/v1/machines/{machine_id}/maintenance", response_model=list[MaintenanceRead])
def get_machine_maintenance(machine_id: str, limit: int = Query(default=50, ge=1, le=500), db: Session = Depends(get_db)):
    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    return (
        db.query(MaintenanceRecord)
        .filter(MaintenanceRecord.machine_id == machine_id)
        .order_by(MaintenanceRecord.maintenance_date.desc())
        .limit(limit)
        .all()
    )



@app.post("/api/v1/sensors", response_model=SensorReadingRead, status_code=201)
def create_sensor_reading(payload: SensorReadingCreate, db: Session = Depends(get_db)):
    machine = db.query(Machine).filter(Machine.machine_id == payload.machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    record = SensorReading(
        machine_id=payload.machine_id,
        air_temperature=payload.air_temperature,
        process_temperature=payload.process_temperature,
        rotational_speed=payload.rotational_speed,
        torque=payload.torque,
        tool_wear=payload.tool_wear,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.post("/api/v1/predict", response_model=PredictionResult)
def create_prediction(payload: PredictionInput, db: Session = Depends(get_db)):
    machine_id = payload.machine_id
    if machine_id:
        machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
        if machine is None:
            machine = Machine(
                machine_id=machine_id,
                name=f"Realtime-{machine_id}",
                type=payload.type,
                location="Realtime Input",
                installation_date=datetime.utcnow(),
                status="ACTIVE",
            )
            db.add(machine)
            db.commit()
            db.refresh(machine)

    result = ml_service.predict_machine_input(
        {
            "machine_id": machine_id,
            "type": payload.type,
            "air_temperature": payload.air_temperature,
            "process_temperature": payload.process_temperature,
            "rotational_speed": payload.rotational_speed,
            "torque": payload.torque,
            "tool_wear": payload.tool_wear,
        }
    )

    # Always persist the prediction, even if machine_id is null
    prediction = Prediction(
        machine_id=machine_id,
        failure_probability=result["failure_probability"],
        health_status=result["health_status"],
        model_version="v1",
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)

    # Create alert and sensor readings only if machine_id is provided
    if machine_id:
        alert = AlertService.create_alert(db, machine_id, result["failure_probability"], result["health_status"])

        sensor = SensorReading(
            machine_id=machine_id,
            air_temperature=payload.air_temperature,
            process_temperature=payload.process_temperature,
            rotational_speed=payload.rotational_speed,
            torque=payload.torque,
            tool_wear=payload.tool_wear,
        )
        db.add(sensor)
        db.commit()

    response = PredictionResult(
        machine_id=machine_id,
        failure_probability=result["failure_probability"],
        health_status=result["health_status"],
        risk_level=result["risk_level"],
        created_at=prediction.created_at,
    )
    return response


@app.get("/api/v1/predictions", response_model=list[PredictionRead])
def list_predictions(db: Session = Depends(get_db)):
    return db.query(Prediction).order_by(Prediction.created_at.desc()).all()


@app.get("/api/v1/alerts", response_model=list[AlertRead])
def list_alerts(db: Session = Depends(get_db)):
    return db.query(Alert).order_by(Alert.created_at.desc()).all()


@app.get("/api/v1/alerts/{alert_id}", response_model=AlertRead)
def get_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@app.patch("/api/v1/alerts/{alert_id}/resolve", response_model=AlertRead)
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = AlertService.resolve_alert(db, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@app.get("/api/v1/maintenance", response_model=list[MaintenanceRead])
def list_maintenance(db: Session = Depends(get_db)):
    return db.query(MaintenanceRecord).order_by(MaintenanceRecord.maintenance_date.desc()).all()


@app.post("/api/v1/maintenance", response_model=MaintenanceRead, status_code=201)
def create_maintenance(payload: MaintenanceCreate, db: Session = Depends(get_db)):
    machine = db.query(Machine).filter(Machine.machine_id == payload.machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    record = MaintenanceRecord(
        machine_id=payload.machine_id,
        maintenance_type=payload.maintenance_type,
        description=payload.description,
        technician=payload.technician,
        maintenance_date=payload.maintenance_date,
        cost=payload.cost,
        status=payload.status,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.get("/api/v1/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    total_machines = db.query(Machine).count()
    normal_count = db.query(Prediction).filter(Prediction.health_status == "NORMAL").count()
    warning_count = db.query(Prediction).filter(Prediction.health_status == "WARNING").count()
    critical_count = db.query(Prediction).filter(Prediction.health_status == "CRITICAL").count()
    active_alerts = db.query(Alert).filter(Alert.is_resolved == False).count()
    maintenance_count = db.query(MaintenanceRecord).count()
    recent_predictions = db.query(Prediction).order_by(Prediction.created_at.desc()).limit(10).all()
    recent_alerts = db.query(Alert).order_by(Alert.created_at.desc()).limit(8).all()

    return {
        "total_machines": total_machines,
        "healthy_machines": normal_count,
        "warning_machines": warning_count,
        "critical_machines": critical_count,
        "active_alerts": active_alerts,
        "maintenance_count": maintenance_count,
        "recent_predictions": recent_predictions,
        "recent_alerts": recent_alerts,
    }


@app.get("/api/v1/dashboard/trend")
def dashboard_trend(db: Session = Depends(get_db)):
    """
    Return aggregated failure probability trend data grouped into 10 equal time buckets
    spanning the last 30 days. Uses real prediction records from the database.
    """
    now = datetime.utcnow()
    window_start = now - timedelta(days=30)
    bucket_count = 10
    bucket_hours = (30 * 24) / bucket_count  # hours per bucket

    predictions = (
        db.query(Prediction.created_at, Prediction.failure_probability)
        .filter(Prediction.created_at >= window_start)
        .all()
    )

    buckets: dict = defaultdict(list)
    for created_at, prob in predictions:
        delta_hours = (created_at - window_start).total_seconds() / 3600
        bucket_idx = min(int(delta_hours // bucket_hours), bucket_count - 1)
        buckets[bucket_idx].append(prob)

    trend = []
    for i in range(bucket_count):
        bucket_start = window_start + timedelta(hours=i * bucket_hours)
        # Cross-platform: strip leading zero from day number manually
        label = f"{bucket_start.day} {bucket_start.strftime('%b')}"
        probs = buckets.get(i, [])
        avg_prob = round(sum(probs) / len(probs), 4) if probs else 0.0
        trend.append({"name": label, "probability": avg_prob, "count": len(probs)})

    return {"trend": trend, "window_days": 30, "buckets": bucket_count}


@app.post("/api/v1/ai/analyze")
def analyze_with_ai(machine_id: str, question: str = "Why is this machine at risk?", db: Session = Depends(get_db)):
    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")

    latest_prediction = db.query(Prediction).filter(Prediction.machine_id == machine_id).order_by(Prediction.created_at.desc()).first()
    latest_sensors = db.query(SensorReading).filter(SensorReading.machine_id == machine_id).order_by(SensorReading.recorded_at.desc()).first()
    recent_maintenance = db.query(MaintenanceRecord).filter(MaintenanceRecord.machine_id == machine_id).order_by(MaintenanceRecord.maintenance_date.desc()).limit(5).all()

    if latest_prediction is None or latest_sensors is None:
        raise HTTPException(status_code=400, detail="Machine has no prediction or sensor data for analysis")

    context = {
        "machine_id": machine_id,
        "question": question,
        "failure_probability": latest_prediction.failure_probability,
        "health_status": latest_prediction.health_status,
        "sensor_values": {
            "air_temperature": latest_sensors.air_temperature,
            "process_temperature": latest_sensors.process_temperature,
            "rotational_speed": latest_sensors.rotational_speed,
            "torque": latest_sensors.torque,
            "tool_wear": latest_sensors.tool_wear,
        },
        "recent_maintenance": [
            {"maintenance_type": item.maintenance_type, "status": item.status, "date": item.maintenance_date.isoformat()}
            for item in recent_maintenance
        ],
    }
    return ai_service.analyze(context)


@app.get("/")
def root():
    return {"message": "MaintenAI API is running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
