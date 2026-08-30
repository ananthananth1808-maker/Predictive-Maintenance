import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import { machinesApi } from '../services/api';
import type {
  Machine,
  SensorReading,
  Prediction,
  AlertItem,
  MaintenanceRecord,
} from '../types';

// ── helpers ────────────────────────────────────────────────────────────────

const HEALTH_COLOR: Record<string, string> = {
  NORMAL: 'status-normal',
  WARNING: 'status-warning',
  CRITICAL: 'status-critical',
};

const SEVERITY_COLOR: Record<string, string> = {
  NORMAL: 'status-normal',
  WARNING: 'status-warning',
  CRITICAL: 'status-critical',
};

function fmt(dt: string) {
  return new Date(dt).toLocaleString();
}

function fmtDate(dt: string) {
  return new Date(dt).toLocaleDateString();
}

// ── Sensor chart ────────────────────────────────────────────────────────────

interface SensorChartProps {
  title: string;
  data: { label: string; value: number }[];
  color: string;
  unit?: string;
}

function SensorChart({ title, data, color, unit = '' }: SensorChartProps) {
  return (
    <div className="chart-card">
      <div className="section-header" style={{ marginBottom: 10 }}>
        <h3 style={{ margin: 0, fontSize: '0.95rem' }}>{title}</h3>
        {data.length > 0 && (
          <span style={{ color: color, fontWeight: 700, fontSize: '1.1rem' }}>
            {data[data.length - 1]?.value?.toFixed(1)}{unit}
          </span>
        )}
      </div>
      {data.length === 0 ? (
        <div style={{ color: '#8aa0bd', padding: '20px 0', textAlign: 'center', fontSize: 13 }}>
          No sensor data
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={160}>
          <LineChart data={data} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e3a5f" />
            <XAxis
              dataKey="label"
              stroke="#8aa0bd"
              tick={{ fontSize: 10 }}
              interval="preserveStartEnd"
            />
            <YAxis stroke="#8aa0bd" tick={{ fontSize: 10 }} />
            <Tooltip
              contentStyle={{ background: '#0f1f2f', border: '1px solid #213b56', borderRadius: 8 }}
              labelStyle={{ color: '#8aa0bd', fontSize: 11 }}
              itemStyle={{ color: color }}
              formatter={(v: unknown) => [`${(v as number).toFixed(2)}${unit}`, title]}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

// ── Main page ───────────────────────────────────────────────────────────────

export function MachineDetailsPage() {
  const { machineId } = useParams<{ machineId: string }>();
  const navigate = useNavigate();

  const [machine, setMachine] = useState<Machine | null>(null);
  const [sensors, setSensors] = useState<SensorReading[]>([]);
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [maintenance, setMaintenance] = useState<MaintenanceRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!machineId) return;

    setLoading(true);
    setError(null);

    Promise.all([
      machinesApi.getById(machineId),
      machinesApi.getSensors(machineId, 50),
      machinesApi.getPredictions(machineId, 50),
      machinesApi.getAlerts(machineId, 50),
      machinesApi.getMaintenance(machineId, 50),
    ])
      .then(([machineRes, sensorsRes, predictionsRes, alertsRes, maintenanceRes]) => {
        setMachine(machineRes.data as Machine);
        // Sensors come newest-first from API; reverse for chronological chart display
        setSensors([...(sensorsRes.data as SensorReading[])].reverse());
        setPredictions(predictionsRes.data as Prediction[]);
        setAlerts(alertsRes.data as AlertItem[]);
        setMaintenance(maintenanceRes.data as MaintenanceRecord[]);
      })
      .catch((err) => {
        console.error('Machine details load error:', err);
        setError(
          err?.response?.status === 404
            ? `Machine "${machineId}" not found.`
            : 'Failed to load machine data. Is the backend running?'
        );
      })
      .finally(() => setLoading(false));
  }, [machineId]);

  // ── Loading / Error states ─────────────────────────────────────────────

  if (loading) {
    return (
      <div className="page-shell">
        <div className="card" style={{ padding: 40, textAlign: 'center', color: '#8aa0bd' }}>
          Loading machine data…
        </div>
      </div>
    );
  }

  if (error || !machine) {
    return (
      <div className="page-shell">
        <button
          className="secondary-button"
          onClick={() => navigate('/machines')}
          style={{ width: 'fit-content' }}
        >
          ← Back to Fleet
        </button>
        <div className="card" style={{ padding: 40, textAlign: 'center', color: '#f87171' }}>
          {error ?? 'Machine not found.'}
        </div>
      </div>
    );
  }

  // ── Derived values ─────────────────────────────────────────────────────

  const latestPrediction = predictions[0] ?? null;
  const latestSensor = sensors[sensors.length - 1] ?? null; // last in chronological order

  const failureProb = latestPrediction
    ? `${(latestPrediction.failure_probability * 100).toFixed(1)}%`
    : '—';

  const healthStatus = latestPrediction?.health_status ?? 'NORMAL';

  // Derive risk level from failure probability
  const failureRaw = latestPrediction?.failure_probability ?? 0;
  const riskLevel =
    failureRaw >= 0.7 ? 'HIGH' : failureRaw >= 0.4 ? 'MEDIUM' : 'LOW';

  const riskColor =
    riskLevel === 'HIGH' ? '#f87171' : riskLevel === 'MEDIUM' ? '#f59e0b' : '#2dd4bf';

  // Build chart data arrays from sensor history
  function buildChartData(key: keyof SensorReading) {
    return sensors.map((s) => ({
      label: new Date(s.recorded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      value: s[key] as number,
    }));
  }

  const airTempData = buildChartData('air_temperature');
  const procTempData = buildChartData('process_temperature');
  const rpmData = buildChartData('rotational_speed');
  const torqueData = buildChartData('torque');
  const toolWearData = buildChartData('tool_wear');

  // ── Render ─────────────────────────────────────────────────────────────

  return (
    <div className="page-shell">

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
        <button
          id="btn-back-to-fleet"
          className="secondary-button"
          onClick={() => navigate('/machines')}
          style={{ flexShrink: 0 }}
        >
          ← Fleet
        </button>
        <div style={{ flex: 1 }}>
          <h1 style={{ margin: 0, fontSize: '1.7rem' }}>{machine.name}</h1>
          <div style={{ color: '#8aa0bd', fontSize: 13, marginTop: 3 }}>
            {machine.machine_id} &nbsp;·&nbsp; {machine.type} &nbsp;·&nbsp; {machine.location}
          </div>
        </div>
        <button
          id="btn-analyze-ai"
          className="primary-button"
          onClick={() => navigate('/ai')}
        >
          Analyze with AI
        </button>
      </div>

      {/* KPI row */}
      <div className="kpi-grid">
        <div className="card kpi-card">
          <div className="label">Machine ID</div>
          <div className="value" style={{ fontSize: '1.2rem', wordBreak: 'break-all' }}>
            {machine.machine_id}
          </div>
        </div>
        <div className="card kpi-card">
          <div className="label">Health Status</div>
          <div className="value" style={{ marginTop: 10 }}>
            <span className={`status-pill ${HEALTH_COLOR[healthStatus] ?? 'status-normal'}`}>
              {healthStatus}
            </span>
          </div>
        </div>
        <div className="card kpi-card">
          <div className="label">Failure Probability</div>
          <div
            className="value"
            style={{
              color:
                failureRaw >= 0.7 ? '#f87171' : failureRaw >= 0.4 ? '#f59e0b' : '#2dd4bf',
            }}
          >
            {failureProb}
          </div>
        </div>
        <div className="card kpi-card">
          <div className="label">Risk Level</div>
          <div className="value" style={{ color: riskColor }}>
            {riskLevel}
          </div>
        </div>
        <div className="card kpi-card">
          <div className="label">Machine Status</div>
          <div className="value" style={{ marginTop: 10 }}>
            <span
              className={`status-pill ${
                machine.status === 'ACTIVE' ? 'status-normal' : 'status-warning'
              }`}
            >
              {machine.status}
            </span>
          </div>
        </div>
        <div className="card kpi-card">
          <div className="label">Installed</div>
          <div className="value" style={{ fontSize: '1rem' }}>
            {fmtDate(machine.installation_date)}
          </div>
        </div>
      </div>

      {/* Latest sensor snapshot */}
      {latestSensor && (
        <div className="chart-card">
          <div className="section-header" style={{ marginBottom: 12 }}>
            <h3 style={{ margin: 0 }}>Latest Sensor Snapshot</h3>
            <span style={{ color: '#8aa0bd', fontSize: 12 }}>
              {fmt(latestSensor.recorded_at)}
            </span>
          </div>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
              gap: 12,
            }}
          >
            {[
              { label: 'Air Temp', value: `${latestSensor.air_temperature.toFixed(1)} K`, color: '#4aa3ff' },
              { label: 'Process Temp', value: `${latestSensor.process_temperature.toFixed(1)} K`, color: '#66d9ef' },
              { label: 'Rotational Speed', value: `${latestSensor.rotational_speed.toFixed(0)} RPM`, color: '#2dd4bf' },
              { label: 'Torque', value: `${latestSensor.torque.toFixed(1)} Nm`, color: '#f59e0b' },
              { label: 'Tool Wear', value: `${latestSensor.tool_wear.toFixed(0)} min`, color: '#f87171' },
            ].map((item) => (
              <div
                key={item.label}
                style={{
                  background: 'rgba(7,17,31,0.6)',
                  border: '1px solid #213b56',
                  borderRadius: 12,
                  padding: '14px 16px',
                }}
              >
                <div style={{ color: '#8aa0bd', fontSize: 12 }}>{item.label}</div>
                <div style={{ color: item.color, fontWeight: 700, fontSize: '1.15rem', marginTop: 4 }}>
                  {item.value}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sensor charts row 1 */}
      <div className="grid-2">
        <SensorChart
          title="Air Temperature (K)"
          data={airTempData}
          color="#4aa3ff"
          unit=" K"
        />
        <SensorChart
          title="Process Temperature (K)"
          data={procTempData}
          color="#66d9ef"
          unit=" K"
        />
      </div>

      {/* Sensor charts row 2 */}
      <div className="grid-2">
        <SensorChart
          title="Rotational Speed (RPM)"
          data={rpmData}
          color="#2dd4bf"
          unit=" RPM"
        />
        <SensorChart
          title="Torque (Nm)"
          data={torqueData}
          color="#f59e0b"
          unit=" Nm"
        />
      </div>

      {/* Tool Wear — full width */}
      <SensorChart
        title="Tool Wear (min)"
        data={toolWearData}
        color="#f87171"
        unit=" min"
      />

      {/* Predictions + Alerts */}
      <div className="grid-2">

        {/* Prediction History */}
        <div className="section-card">
          <div className="section-header">
            <h3 style={{ margin: 0 }}>Prediction History</h3>
            <span style={{ color: '#8aa0bd', fontSize: 12 }}>{predictions.length} records</span>
          </div>
          {predictions.length === 0 ? (
            <div style={{ color: '#8aa0bd', fontSize: 13, padding: '12px 0' }}>
              No prediction records.
            </div>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Status</th>
                  <th>Probability</th>
                  <th>Model</th>
                </tr>
              </thead>
              <tbody>
                {predictions.slice(0, 10).map((p) => (
                  <tr key={p.id}>
                    <td style={{ fontSize: 12, color: '#8aa0bd' }}>{fmt(p.created_at)}</td>
                    <td>
                      <span className={`status-pill ${HEALTH_COLOR[p.health_status] ?? ''}`}>
                        {p.health_status}
                      </span>
                    </td>
                    <td style={{ fontWeight: 600 }}>
                      {(p.failure_probability * 100).toFixed(1)}%
                    </td>
                    <td style={{ color: '#8aa0bd', fontSize: 12 }}>{p.model_version}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Alert History */}
        <div className="section-card">
          <div className="section-header">
            <h3 style={{ margin: 0 }}>Alert History</h3>
            <span style={{ color: '#8aa0bd', fontSize: 12 }}>{alerts.length} records</span>
          </div>
          {alerts.length === 0 ? (
            <div style={{ color: '#8aa0bd', fontSize: 13, padding: '12px 0' }}>
              No alerts for this machine.
            </div>
          ) : (
            <div className="list-stack">
              {alerts.slice(0, 8).map((a) => (
                <div
                  key={a.id}
                  className="card"
                  style={{ padding: '10px 14px', borderRadius: 12 }}
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 10,
                      flexWrap: 'wrap',
                    }}
                  >
                    <span
                      className={`status-pill ${SEVERITY_COLOR[a.severity] ?? ''}`}
                    >
                      {a.severity}
                    </span>
                    <strong style={{ fontSize: 13, flex: 1 }}>{a.title}</strong>
                    {a.is_resolved ? (
                      <span
                        style={{
                          fontSize: 11,
                          color: '#2dd4bf',
                          background: 'rgba(45,212,191,0.1)',
                          padding: '2px 8px',
                          borderRadius: 999,
                        }}
                      >
                        Resolved
                      </span>
                    ) : (
                      <span
                        style={{
                          fontSize: 11,
                          color: '#f87171',
                          background: 'rgba(248,113,113,0.1)',
                          padding: '2px 8px',
                          borderRadius: 999,
                        }}
                      >
                        Active
                      </span>
                    )}
                  </div>
                  <div style={{ color: '#8aa0bd', fontSize: 12, marginTop: 6 }}>
                    {a.message}
                  </div>
                  <div style={{ color: '#6b7ea0', fontSize: 11, marginTop: 4 }}>
                    {fmt(a.created_at)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Maintenance History — full width */}
      <div className="section-card">
        <div className="section-header">
          <h3 style={{ margin: 0 }}>Maintenance History</h3>
          <span style={{ color: '#8aa0bd', fontSize: 12 }}>{maintenance.length} records</span>
        </div>
        {maintenance.length === 0 ? (
          <div style={{ color: '#8aa0bd', fontSize: 13, padding: '12px 0' }}>
            No maintenance records for this machine.
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Type</th>
                <th>Technician</th>
                <th>Description</th>
                <th>Cost</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {maintenance.map((m) => (
                <tr key={m.id}>
                  <td style={{ fontSize: 12, color: '#8aa0bd', whiteSpace: 'nowrap' }}>
                    {fmtDate(m.maintenance_date)}
                  </td>
                  <td style={{ fontWeight: 600 }}>{m.maintenance_type}</td>
                  <td style={{ color: '#8aa0bd', fontSize: 12 }}>{m.technician}</td>
                  <td style={{ fontSize: 12, maxWidth: 260 }}>{m.description}</td>
                  <td style={{ color: '#2dd4bf', fontWeight: 600 }}>
                    ${m.cost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </td>
                  <td>
                    <span
                      className={`status-pill ${
                        m.status === 'COMPLETED'
                          ? 'status-normal'
                          : m.status === 'IN_PROGRESS'
                          ? 'status-warning'
                          : 'status-warning'
                      }`}
                    >
                      {m.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

    </div>
  );
}


