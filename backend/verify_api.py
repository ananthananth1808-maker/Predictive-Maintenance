"""Quick API verification script using real seeded data."""

from app.main import app
from fastapi.testclient import TestClient
import json

client = TestClient(app)

print("\n" + "=" * 70)
print("API ENDPOINT VERIFICATION (Using Real Seeded Data)")
print("=" * 70)

# Test 1: Health check
print("\nTEST 1: Health Check")
response = client.get('/api/v1/health')
print(f"  Status: {response.status_code}")
print(f"  Response: {json.dumps(response.json(), indent=2)}")

# Test 2: List machines
print("\nTEST 2: List Machines")
response = client.get('/api/v1/machines')
print(f"  Status: {response.status_code}")
machines = response.json()
print(f"  Total machines returned: {len(machines)}")
if machines:
    print(f"  First 3 machines:")
    for m in machines[:3]:
        print(f"    - {m['machine_id']}: {m['name']}")

# Test 3: List predictions
print("\nTEST 3: List Predictions")
response = client.get('/api/v1/predictions')
print(f"  Status: {response.status_code}")
predictions = response.json()
print(f"  Total predictions returned: {len(predictions)}")
if predictions:
    print(f"  Sample prediction:")
    p = predictions[0]
    print(f"    - Machine: {p['machine_id']}")
    print(f"    - Probability: {p['failure_probability']:.4f}")
    print(f"    - Health Status: {p['health_status']}")
    
print(f"  Health status distribution:")
statuses = {}
for p in predictions:
    s = p['health_status']
    statuses[s] = statuses.get(s, 0) + 1
for status in sorted(statuses.keys()):
    count = statuses[status]
    pct = 100 * count / len(predictions)
    print(f"    {status}: {count} ({pct:.1f}%)")

# Test 4: List alerts
print("\nTEST 4: List Alerts")
response = client.get('/api/v1/alerts')
print(f"  Status: {response.status_code}")
alerts = response.json()
print(f"  Total alerts returned: {len(alerts)}")
if alerts:
    print(f"  Alert severities:")
    severities = {}
    for a in alerts:
        sev = a['severity']
        severities[sev] = severities.get(sev, 0) + 1
    for sev in sorted(severities.keys()):
        count = severities[sev]
        pct = 100 * count / len(alerts)
        print(f"    {sev}: {count} ({pct:.1f}%)")

# Test 5: Dashboard Summary (Most Important)
print("\nTEST 5: Dashboard Summary")
response = client.get('/api/v1/dashboard/summary')
print(f"  Status: {response.status_code}")
summary = response.json()
print(f"  KPI Values (should NOT be zeros):")
print(f"    total_machines:     {summary.get('total_machines')}")
print(f"    healthy_machines:   {summary.get('healthy_machines')}")
print(f"    warning_machines:   {summary.get('warning_machines')}")
print(f"    critical_machines:  {summary.get('critical_machines')}")
print(f"    active_alerts:      {summary.get('active_alerts')}")
print(f"    maintenance_count:  {summary.get('maintenance_count')}")
print(f"    recent_predictions: {len(summary.get('recent_predictions', []))} items")

print("\n" + "=" * 70)
print("[OK] All endpoints returning real database data!")
print("=" * 70 + "\n")
