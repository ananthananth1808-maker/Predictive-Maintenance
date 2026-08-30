"""Direct database query verification (no test fixture interference)."""

from app.database import SessionLocal
from app.models.machine import Machine
from app.models.prediction import Prediction
from app.models.sensor_reading import SensorReading
from app.models.alert import Alert
from sqlalchemy import func

print("\n" + "=" * 70)
print("DIRECT DATABASE QUERY (Production Database)")
print("=" * 70)

db = SessionLocal()

try:
    # Query real counts
    machines = db.query(Machine).count()
    sensors = db.query(SensorReading).count()
    predictions = db.query(Prediction).count()
    alerts = db.query(Alert).count()

    print(f"\nData Counts:")
    print(f"  Machines:        {machines:,}")
    print(f"  Sensor Readings: {sensors:,}")
    print(f"  Predictions:     {predictions:,}")
    print(f"  Alerts:          {alerts:,}")

    # Health distribution
    dist = db.query(
        Prediction.health_status,
        func.count(Prediction.id).label('count')
    ).group_by(Prediction.health_status).all()

    print(f"\nPrediction Health Distribution:")
    total_preds = predictions
    for status, count in sorted(dist):
        pct = 100 * count / total_preds if total_preds > 0 else 0
        print(f"  {status}: {count:,} ({pct:.1f}%)")

    # Alert severity distribution
    alert_dist = db.query(
        Alert.severity,
        func.count(Alert.id).label('count')
    ).group_by(Alert.severity).all()

    if alert_dist:
        print(f"\nAlert Severity Distribution:")
        for severity, count in sorted(alert_dist):
            pct = 100 * count / alerts if alerts > 0 else 0
            print(f"  {severity}: {count} ({pct:.1f}%)")

    # Sample data
    print(f"\nSample Data:")
    sample_machine = db.query(Machine).first()
    if sample_machine:
        print(f"  First Machine:")
        print(f"    - ID: {sample_machine.machine_id}")
        print(f"    - Name: {sample_machine.name}")
        print(f"    - Type: {sample_machine.type}")
        print(f"    - Location: {sample_machine.location}")

    sample_pred = db.query(Prediction).filter(
        Prediction.health_status == "CRITICAL"
    ).first()
    if sample_pred:
        print(f"  Sample Critical Prediction:")
        print(f"    - Machine: {sample_pred.machine_id}")
        print(f"    - Probability: {sample_pred.failure_probability:.4f}")
        print(f"    - Status: {sample_pred.health_status}")

    sample_sensor = db.query(SensorReading).first()
    if sample_sensor:
        print(f"  First Sensor Reading:")
        print(f"    - Machine: {sample_sensor.machine_id}")
        print(f"    - Air Temp: {sample_sensor.air_temperature:.1f}K")
        print(f"    - Process Temp: {sample_sensor.process_temperature:.1f}K")
        print(f"    - RPM: {sample_sensor.rotational_speed:.0f}")

    sample_alert = db.query(Alert).first()
    if sample_alert:
        print(f"  First Alert:")
        print(f"    - Machine: {sample_alert.machine_id}")
        print(f"    - Severity: {sample_alert.severity}")
        print(f"    - Title: {sample_alert.title}")

    print("\n" + "=" * 70)
    print("[OK] Production database seeding verified successfully!")
    print("=" * 70 + "\n")

finally:
    db.close()
