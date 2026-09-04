from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, ensure_sqlite_compatibility, get_db
from app.main import app
from app.models.machine import Machine

# Use an isolated in-memory SQLite database with StaticPool for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    db.add(
        Machine(
            machine_id='M-TEST-1',
            name='Test Mill',
            type='M',
            location='Floor 1',
            installation_date=datetime(2023, 1, 15, 0, 0, 0),
            status='ACTIVE',
        )
    )
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)


def test_sqlite_prediction_table_allows_null_machine_ids_for_realtime_predictions(tmp_path):
    db_path = tmp_path / 'legacy_predictions.db'
    legacy_engine = create_engine(f'sqlite:///{db_path}', connect_args={'check_same_thread': False})

    with legacy_engine.begin() as conn:
        conn.exec_driver_sql(
            '''
            CREATE TABLE predictions (
                id INTEGER PRIMARY KEY,
                machine_id VARCHAR(50) NOT NULL,
                failure_probability FLOAT NOT NULL,
                health_status VARCHAR(50) NOT NULL,
                model_version VARCHAR(50) DEFAULT 'v1',
                created_at DATETIME NOT NULL
            )
            '''
        )
        conn.exec_driver_sql(
            "INSERT INTO predictions (id, machine_id, failure_probability, health_status, model_version, created_at) VALUES (1, 'M-LEGACY', 0.42, 'WARNING', 'v1', '2024-01-01T00:00:00')"
        )

    ensure_sqlite_compatibility(legacy_engine)

    with legacy_engine.begin() as conn:
        columns = conn.exec_driver_sql('PRAGMA table_info(predictions)').fetchall()
        machine_id_column = next(col for col in columns if col[1] == 'machine_id')
        assert machine_id_column[3] == 0
        conn.exec_driver_sql(
            "INSERT INTO predictions (id, machine_id, failure_probability, health_status, model_version, created_at) VALUES (2, NULL, 0.11, 'NORMAL', 'v1', '2024-01-02T00:00:00')"
        )
        assert conn.exec_driver_sql('SELECT COUNT(*) FROM predictions WHERE machine_id IS NULL').fetchone()[0] == 1


def test_health_endpoint():
    response = client.get('/api/v1/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_machine_endpoints():
    response = client.post('/api/v1/machines', json={
        'machine_id': 'M-TEST-2',
        'name': 'Test Lathe',
        'type': 'H',
        'location': 'Floor 2',
        'installation_date': '2023-02-20T00:00:00',
        'status': 'ACTIVE',
    })
    assert response.status_code == 201

    list_response = client.get('/api/v1/machines')
    assert list_response.status_code == 200
    assert len(list_response.json()) >= 2


def test_prediction_endpoint():
    response = client.post('/api/v1/predict', json={
        'machine_id': 'M-TEST-1',
        'type': 'M',
        'air_temperature': 300.5,
        'process_temperature': 310.2,
        'rotational_speed': 1500,
        'torque': 42.5,
        'tool_wear': 120,
    })
    assert response.status_code == 200
    payload = response.json()
    assert 'failure_probability' in payload
    assert 'health_status' in payload
    assert payload['machine_id'] == 'M-TEST-1'


def test_prediction_endpoint_accepts_real_time_sensor_input_without_machine_record():
    response = client.post('/api/v1/predict', json={
        'type': 'M',
        'air_temperature': 300.0,
        'process_temperature': 310.0,
        'rotational_speed': 1500,
        'torque': 40.0,
        'tool_wear': 100.0,
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload['machine_id'] is None
    assert 0.0 <= payload['failure_probability'] <= 1.0
    assert payload['health_status'] in {'NORMAL', 'WARNING', 'CRITICAL'}
    assert payload['risk_level'] in {'LOW', 'MEDIUM', 'HIGH'}


def test_realtime_prediction_with_null_machine_id_is_persisted():
    """Regression test: verify that realtime predictions (machine_id=null) are persisted to DB."""
    # Submit a realtime prediction without machine_id
    predict_response = client.post('/api/v1/predict', json={
        'type': 'M',
        'air_temperature': 300.0,
        'process_temperature': 310.0,
        'rotational_speed': 1500,
        'torque': 40.0,
        'tool_wear': 100.0,
    })
    assert predict_response.status_code == 200
    predict_payload = predict_response.json()
    assert predict_payload['machine_id'] is None
    assert 0.0 <= predict_payload['failure_probability'] <= 1.0
    
    # Verify the prediction is persisted and returned by GET /api/v1/predictions
    predictions_response = client.get('/api/v1/predictions')
    assert predictions_response.status_code == 200
    predictions = predictions_response.json()
    
    # Should have at least one prediction (the one we just created)
    assert len(predictions) >= 1
    
    # Find the realtime prediction (machine_id=null)
    realtime_preds = [p for p in predictions if p['machine_id'] is None]
    assert len(realtime_preds) >= 1, "Realtime prediction with machine_id=null not found in prediction history"
    
    # Verify it has the correct data
    realtime_pred = realtime_preds[0]
    assert 0.0 <= realtime_pred['failure_probability'] <= 1.0
    assert realtime_pred['health_status'] in {'NORMAL', 'WARNING', 'CRITICAL'}
    assert realtime_pred['model_version'] == 'v1'
    
    # Verify it appears in the dashboard summary
    summary_response = client.get('/api/v1/dashboard/summary')
    assert summary_response.status_code == 200
    summary = summary_response.json()
    
    # Dashboard should show at least one recent prediction
    assert len(summary.get('recent_predictions', [])) >= 1


def test_alert_and_maintenance_endpoints():
    alert_response = client.get('/api/v1/alerts')
    assert alert_response.status_code == 200

    maintenance_response = client.post('/api/v1/maintenance', json={
        'machine_id': 'M-TEST-1',
        'maintenance_type': 'Inspection',
        'description': 'Review thermal behavior',
        'technician': 'T. Johnson',
        'maintenance_date': '2026-08-18T09:00:00',
        'cost': 1500.0,
        'status': 'COMPLETED',
    })
    assert maintenance_response.status_code == 201


def test_ai_analyze_endpoint():
    # First create a prediction + sensor reading so the AI endpoint has data to work with
    predict_response = client.post('/api/v1/predict', json={
        'machine_id': 'M-TEST-1',
        'type': 'M',
        'air_temperature': 302.0,
        'process_temperature': 312.0,
        'rotational_speed': 1450,
        'torque': 45.0,
        'tool_wear': 130,
    })
    assert predict_response.status_code == 200

    # Now call the AI analyze endpoint
    ai_response = client.post(
        '/api/v1/ai/analyze',
        params={'machine_id': 'M-TEST-1', 'question': 'Why is this machine at risk?'},
    )
    assert ai_response.status_code == 200
    payload = ai_response.json()
    assert 'summary' in payload
    assert 'possible_causes' in payload
    assert 'recommended_actions' in payload
    assert 'priority' in payload
    assert isinstance(payload['possible_causes'], list)
    assert isinstance(payload['recommended_actions'], list)
    assert payload['priority'] in ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')


def test_ai_analyze_machine_not_found():
    response = client.post(
        '/api/v1/ai/analyze',
        params={'machine_id': 'M-DOES-NOT-EXIST', 'question': 'test'},
    )
    assert response.status_code == 404
    assert 'not found' in response.json()['detail'].lower()


# ── Alert system tests ────────────────────────────────────────────────────────

def _seed_alert():
    """Create a high-risk prediction which triggers an alert via AlertService."""
    r = client.post('/api/v1/predict', json={
        'machine_id': 'M-TEST-1',
        'type': 'M',
        'air_temperature': 310.0,
        'process_temperature': 320.0,
        'rotational_speed': 1200,
        'torque': 65.0,
        'tool_wear': 220,
    })
    assert r.status_code == 200
    # Return the alert list so the caller can grab the alert id
    alerts_r = client.get('/api/v1/alerts')
    return alerts_r.json()


def test_alert_list():
    """GET /api/v1/alerts returns a list (may be empty initially)."""
    response = client.get('/api/v1/alerts')
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_resolve_existing_alert():
    """Resolve a real alert and verify status changes."""
    alerts = _seed_alert()
    # Find an unresolved alert
    active = [a for a in alerts if not a['is_resolved']]
    assert len(active) > 0, "Expected at least one active alert after high-risk prediction"
    alert_id = active[0]['id']

    resolve_r = client.patch(f'/api/v1/alerts/{alert_id}/resolve')
    assert resolve_r.status_code == 200
    payload = resolve_r.json()
    assert payload['is_resolved'] is True
    assert payload['id'] == alert_id


def test_resolve_nonexistent_alert_returns_404():
    """PATCH on a non-existent alert ID returns 404."""
    response = client.patch('/api/v1/alerts/999999/resolve')
    assert response.status_code == 404
    assert 'not found' in response.json()['detail'].lower()


def test_resolved_at_is_populated():
    """resolved_at field is set after resolving an alert."""
    alerts = _seed_alert()
    active = [a for a in alerts if not a['is_resolved']]
    assert len(active) > 0
    alert_id = active[0]['id']

    resolve_r = client.patch(f'/api/v1/alerts/{alert_id}/resolve')
    assert resolve_r.status_code == 200
    payload = resolve_r.json()
    assert payload['resolved_at'] is not None, "resolved_at must be populated after resolution"


def test_resolved_alert_remains_in_history():
    """Resolved alert still appears in GET /api/v1/alerts (not deleted)."""
    alerts = _seed_alert()
    active = [a for a in alerts if not a['is_resolved']]
    assert len(active) > 0
    alert_id = active[0]['id']

    client.patch(f'/api/v1/alerts/{alert_id}/resolve')

    all_alerts = client.get('/api/v1/alerts').json()
    ids = [a['id'] for a in all_alerts]
    assert alert_id in ids, "Resolved alert must still appear in the alert history"
    resolved = next(a for a in all_alerts if a['id'] == alert_id)
    assert resolved['is_resolved'] is True
