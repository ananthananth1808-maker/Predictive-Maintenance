"""
Idempotent database seed script for MaintenAI.
Loads the AI4I 2020 dataset into PostgreSQL/SQLite and generates predictions using the trained ML model.
Safe to run multiple times - checks for existing data and avoids duplicates.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

import pandas as pd
from sqlalchemy.orm import Session

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config import DATABASE_URL
from app.database import SessionLocal, engine, Base
from app.models.alert import Alert
from app.models.machine import Machine
from app.models.maintenance_record import MaintenanceRecord
from app.models.prediction import Prediction
from app.models.sensor_reading import SensorReading
from app.services.ml_service import MLService


def get_dataset_path() -> Path:
    """Get the path to the AI4I dataset."""
    dataset_path = Path(__file__).resolve().parent.parent / "data" / "ai4i2020.csv"
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found at {dataset_path}")
    return dataset_path


def load_dataset() -> pd.DataFrame:
    """Load and validate the CSV dataset."""
    df = pd.read_csv(get_dataset_path())
    print(f"[OK] Loaded dataset: {len(df)} rows")
    print(f"  Columns: {', '.join(df.columns.tolist())}")
    return df


def get_or_create_machines(db: Session, df: pd.DataFrame) -> Dict[str, str]:
    """
    Create machines from unique Product IDs in the dataset.
    Returns mapping of Product ID -> machine_id string.
    """
    unique_products = df["Product ID"].unique()
    
    existing_count = db.query(Machine).count()
    if existing_count > 0:
        print(f"[OK] Database already contains {existing_count} machines. Skipping machine creation.")
        machines = db.query(Machine).all()
        return {m.machine_id: m.machine_id for m in machines}
    
    machines = []
    product_to_machine_id = {}
    base_install_date = datetime(2023, 1, 1)
    
    for idx, product_id in enumerate(unique_products):
        machine_id = str(product_id)
        machine_type = str(product_id)[0]
        # Spread installation dates over 2022-2023
        install_date = base_install_date + timedelta(days=idx % 365)
        
        machine = Machine(
            machine_id=machine_id,
            name=f"Machine {product_id}",
            type=machine_type,
            location=f"Production Floor - Zone {machine_type}",
            installation_date=install_date,
            status="ACTIVE",
        )
        machines.append(machine)
        product_to_machine_id[product_id] = machine_id
    
    # Bulk insert in batches
    batch_size = 1000
    for i in range(0, len(machines), batch_size):
        db.add_all(machines[i:i + batch_size])
        db.commit()
    
    print(f"[OK] Created {len(machines):,} machines from {len(unique_products):,} unique Product IDs")
    return product_to_machine_id


def create_sensor_readings(db: Session, df: pd.DataFrame, product_to_machine_id: Dict[str, str]) -> int:
    """
    Create sensor reading records from the real dataset.
    Uses timestamps spread over the past 30 days to simulate historical telemetry.
    """
    existing_count = db.query(SensorReading).count()
    if existing_count > 0:
        print(f"[OK] Database already contains {existing_count} sensor readings. Skipping sensor creation.")
        return existing_count
    
    max_row = len(df)
    base_time = datetime.utcnow() - timedelta(days=30)
    batch_size = 1000
    sensor_records = []
    
    for idx, row in df.iterrows():
        machine_id = product_to_machine_id[row["Product ID"]]
        days_offset = (idx / max_row) * 30
        recorded_at = base_time + timedelta(days=days_offset)
        
        sensor = SensorReading(
            machine_id=machine_id,
            air_temperature=float(row["Air temperature [K]"]),
            process_temperature=float(row["Process temperature [K]"]),
            rotational_speed=float(row["Rotational speed [rpm]"]),
            torque=float(row["Torque [Nm]"]),
            tool_wear=float(row["Tool wear [min]"]),
            recorded_at=recorded_at,
        )
        sensor_records.append(sensor)
        
        if len(sensor_records) >= batch_size:
            db.add_all(sensor_records)
            db.commit()
            sensor_records = []
    
    if sensor_records:
        db.add_all(sensor_records)
        db.commit()
    
    total_created = db.query(SensorReading).count()
    print(f"[OK] Created {total_created:,} sensor readings from dataset")
    return total_created


def generate_predictions(db: Session, df: pd.DataFrame, product_to_machine_id: Dict[str, str]) -> int:
    """
    Generate predictions by running the existing trained ML model on sensor data.
    Uses the real XGBoost model and preprocessor (no fabricated probabilities).
    """
    existing_count = db.query(Prediction).count()
    if existing_count > 0:
        print(f"[OK] Database already contains {existing_count} predictions. Skipping prediction generation.")
        return existing_count
    
    try:
        ml_service = MLService()
        print("[OK] Loaded ML model and preprocessor successfully")
    except FileNotFoundError as e:
        print(f"[ERROR] Error loading ML model: {e}")
        return 0
    
    feature_columns = [
        "Type",
        "Air temperature [K]",
        "Process temperature [K]",
        "Rotational speed [rpm]",
        "Torque [Nm]",
        "Tool wear [min]",
    ]
    
    # Vectorized inference for maximum efficiency and exact accuracy
    print("  Running ML inference on all sensor records...")
    X = df[feature_columns]
    transformed = ml_service.preprocessor.transform(X)
    probabilities = ml_service.model.predict_proba(transformed)[:, 1]
    
    max_row = len(df)
    base_time = datetime.utcnow() - timedelta(days=30)
    batch_size = 1000
    prediction_records = []
    
    for idx, row in df.iterrows():
        machine_id = product_to_machine_id[row["Product ID"]]
        prob = float(probabilities[idx])
        health_status = ml_service._classify(prob)
        
        days_offset = (idx / max_row) * 30
        created_at = base_time + timedelta(days=days_offset)
        
        prediction = Prediction(
            machine_id=machine_id,
            failure_probability=prob,
            health_status=health_status,
            model_version="v1",
            created_at=created_at,
        )
        prediction_records.append(prediction)
        
        if len(prediction_records) >= batch_size:
            db.add_all(prediction_records)
            db.commit()
            prediction_records = []
    
    if prediction_records:
        db.add_all(prediction_records)
        db.commit()
    
    total_created = db.query(Prediction).count()
    print(f"[OK] Generated {total_created:,} predictions using trained ML model")
    return total_created


def create_alerts(db: Session) -> int:
    """
    Create alerts for predictions with WARNING or CRITICAL health status.
    Deduplicates by machine_id and severity.
    """
    existing_alert_count = db.query(Alert).count()
    if existing_alert_count > 0:
        print(f"[OK] Database already contains {existing_alert_count} alerts. Skipping alert generation.")
        return existing_alert_count
    
    concerning_predictions = db.query(Prediction).filter(
        Prediction.health_status.in_(["WARNING", "CRITICAL"])
    ).all()
    
    alerts = []
    for prediction in concerning_predictions:
        severity = "CRITICAL" if prediction.health_status == "CRITICAL" else "WARNING"
        title = "Critical failure risk" if severity == "CRITICAL" else "Warning: elevated failure risk"
        message = (
            f"Machine {prediction.machine_id} is currently in {prediction.health_status} status "
            f"with a failure probability of {prediction.failure_probability:.2f}. "
            "Review sensor readings and schedule maintenance."
        )
        
        alert = Alert(
            machine_id=prediction.machine_id,
            severity=severity,
            title=title,
            message=message,
            is_resolved=False,
            created_at=prediction.created_at,
        )
        alerts.append(alert)
    
    if alerts:
        db.add_all(alerts)
        db.commit()
        print(f"[OK] Created {len(alerts):,} alerts for WARNING/CRITICAL machines")
    
    return len(alerts)


def create_maintenance_records(db: Session) -> int:
    """
    Create initial maintenance records for machines with high failure probability.
    Provides operational history for the AI assistant and Maintenance page.
    """
    existing_count = db.query(MaintenanceRecord).count()
    if existing_count > 0:
        print(f"[OK] Database already contains {existing_count} maintenance records. Skipping creation.")
        return existing_count
    
    # Select sample critical and warning machines
    flagged = db.query(Prediction).filter(
        Prediction.health_status.in_(["WARNING", "CRITICAL"])
    ).limit(15).all()
    
    maintenance_types = [
        ("Tool Replacement", "Cutting tool wear exceeded safe threshold; replaced cutting insert and calibrated spindle.", "J. Vance", 450.0, "COMPLETED"),
        ("Thermal Inspection", "Elevated process temperature detected; inspected coolant lines and cleared debris.", "T. Johnson", 620.0, "COMPLETED"),
        ("Torque & Bearing Overhaul", "High mechanical resistance noted; inspected bearings, lubricated drive system.", "R. Patel", 1200.0, "COMPLETED"),
        ("Preventive Calibration", "Routine 1000-hour system recalibration and sensor alignment check.", "M. Zhang", 350.0, "COMPLETED"),
        ("Scheduled Maintenance", "Scheduled overhaul for hydraulic pressure regulators and drive motors.", "A. Davis", 850.0, "SCHEDULED"),
    ]
    
    records = []
    base_date = datetime.utcnow() - timedelta(days=20)
    
    for idx, pred in enumerate(flagged):
        m_type, desc, tech, cost, status = maintenance_types[idx % len(maintenance_types)]
        record = MaintenanceRecord(
            machine_id=pred.machine_id,
            maintenance_type=m_type,
            description=desc,
            technician=tech,
            maintenance_date=base_date + timedelta(days=idx),
            cost=cost,
            status=status,
        )
        records.append(record)
    
    if records:
        db.add_all(records)
        db.commit()
        print(f"[OK] Created {len(records)} initial maintenance records for monitored machines")
    
    return len(records)


def print_summary(db: Session):
    """Print a comprehensive summary of imported data."""
    machine_count = db.query(Machine).count()
    sensor_count = db.query(SensorReading).count()
    prediction_count = db.query(Prediction).count()
    alert_count = db.query(Alert).count()
    maintenance_count = db.query(MaintenanceRecord).count()
    
    warning_count = db.query(Prediction).filter(Prediction.health_status == "WARNING").count()
    critical_count = db.query(Prediction).filter(Prediction.health_status == "CRITICAL").count()
    normal_count = db.query(Prediction).filter(Prediction.health_status == "NORMAL").count()
    
    print("\n" + "=" * 60)
    print("SEED SUMMARY")
    print("=" * 60)
    print(f"Database URL: {DATABASE_URL}")
    print(f"\nImported Data Counts:")
    print(f"  Machines:            {machine_count:,}")
    print(f"  Sensor Readings:     {sensor_count:,}")
    print(f"  Predictions:         {prediction_count:,}")
    print(f"  Alerts:              {alert_count:,}")
    print(f"  Maintenance Records: {maintenance_count:,}")
    print(f"\nPrediction Health Distribution:")
    print(f"  NORMAL:    {normal_count:,} ({100*normal_count/max(1, prediction_count):.1f}%)")
    print(f"  WARNING:   {warning_count:,} ({100*warning_count/max(1, prediction_count):.1f}%)")
    print(f"  CRITICAL:  {critical_count:,} ({100*critical_count/max(1, prediction_count):.1f}%)")
    print("\n[OK] Seed completed successfully!")
    print("=" * 60 + "\n")


def main():
    """Main seed function."""
    print("\n" + "=" * 60)
    print("MAINTENAI DATABASE SEED")
    print("=" * 60)
    print(f"Database: {DATABASE_URL}")
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    print("[OK] Database tables ready")
    
    db = SessionLocal()
    try:
        # 1. Load dataset
        df = load_dataset()
        
        # 2. Create machines
        product_to_machine_id = get_or_create_machines(db, df)
        
        # 3. Create sensor readings from real dataset
        create_sensor_readings(db, df, product_to_machine_id)
        
        # 4. Generate predictions using trained ML model
        generate_predictions(db, df, product_to_machine_id)
        
        # 5. Create alerts for WARNING/CRITICAL predictions
        create_alerts(db)
        
        # 6. Create maintenance records
        create_maintenance_records(db)
        
        # 7. Print summary
        print_summary(db)
        
    except Exception as e:
        print(f"\n[ERROR] Error during seed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
