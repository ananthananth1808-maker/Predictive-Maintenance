import { useEffect, useState } from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area,
} from 'recharts';
import { dashboardApi, machinesApi, predictionsApi } from '../services/api';
import type { DashboardSummary, AlertItem, Prediction, Machine } from '../types';

const HEALTH_COLORS = ['#2dd4bf', '#f59e0b', '#f87171'];
const STATUS_CLASS: Record<string, string> = {
  NORMAL: 'status-normal',
  WARNING: 'status-warning',
  CRITICAL: 'status-critical',
};

interface TrendPoint {
  name: string;
  probability: number;
  count: number;
}

const DashboardHeader = ({
  onRefresh,
  isRefreshing,
  lastUpdated,
}: {
  onRefresh: () => void;
  isRefreshing: boolean;
  lastUpdated: string | null;
}) => (
  <div className="dashboard-header">
    <div className="dashboard-header-left">
      <h1>Predictive Maintenance Dashboard</h1>
      <p className="dashboard-subtitle">Real-time machine health monitoring and failure risk analysis</p>
    </div>
    <div className="dashboard-header-right">
      <div className="system-status">
        <span className="status-indicator online"></span>
        <span className="status-text">AI System Online</span>
      </div>
      <button
        className="refresh-button"
        onClick={onRefresh}
        disabled={isRefreshing}
        title="Refresh dashboard data"
      >
        {isRefreshing ? '⟳ Refreshing...' : '⟳ Refresh'}
      </button>
      {lastUpdated && (
        <div className="last-updated">
          Last updated: {lastUpdated}
        </div>
      )}
    </div>
  </div>
);

const KpiCard = ({
  icon,
  label,
  value,
  trend,
  color,
}: {
  icon: string;
  label: string;
  value: number | string;
  trend?: string;
  color: 'green' | 'blue' | 'orange' | 'red';
}) => {
  const colorMap = {
    green: '#2dd4bf',
    blue: '#4aa3ff',
    orange: '#f59e0b',
    red: '#f87171',
  };

  return (
    <div className="card kpi-card">
      <div className="kpi-header">
        <span className="kpi-icon">{icon}</span>
      </div>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value" style={{ color: colorMap[color] }}>
        {typeof value === 'number' ? value.toLocaleString() : value}
      </div>
      {trend && <div className="kpi-trend">{trend}</div>}
    </div>
  );
};

const EmptyState = ({ title, message }: { title: string; message: string }) => (
  <div className="empty-state">
    <div className="empty-state-icon">📊</div>
    <div className="empty-state-title">{title}</div>
    <div className="empty-state-message">{message}</div>
  </div>
);

const LoadingSkeleton = () => (
  <div className="skeleton-container">
    <div className="skeleton skeleton-card"></div>
    <div className="skeleton skeleton-card"></div>
    <div className="skeleton skeleton-card"></div>
    <div className="skeleton skeleton-card"></div>
  </div>
);

export function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [trend, setTrend] = useState<TrendPoint[]>([]);
  const [machines, setMachines] = useState<Machine[]>([]);
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const loadDashboard = async (isRefresh = false) => {
    try {
      if (isRefresh) setRefreshing(true);
      else setLoading(true);
      setError(null);

      const [summaryRes, trendRes, machinesRes, predictionsRes] = await Promise.all([
        dashboardApi.getSummary(),
        dashboardApi.getTrend(),
        machinesApi.getAll(),
        predictionsApi.getAll(),
      ]);

      setSummary(summaryRes.data as DashboardSummary);
      setTrend((trendRes.data as { trend: TrendPoint[] }).trend ?? []);
      setMachines(machinesRes.data as Machine[]);
      setPredictions(predictionsRes.data as Prediction[]);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      console.error('Dashboard load error:', err);
      setError('Failed to load dashboard data. Please ensure the backend is running and try again.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  const handleRefresh = () => {
    loadDashboard(true);
  };

  if (error) {
    return (
      <div className="page-shell">
        <DashboardHeader onRefresh={handleRefresh} isRefreshing={refreshing} lastUpdated={lastUpdated} />
        <div className="error-state">
          <div className="error-icon">⚠️</div>
          <div className="error-title">Unable to Load Dashboard</div>
          <div className="error-message">{error}</div>
          <button className="primary-button" onClick={handleRefresh} disabled={refreshing}>
            {refreshing ? 'Retrying...' : 'Retry'}
          </button>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="page-shell">
        <DashboardHeader onRefresh={handleRefresh} isRefreshing={refreshing} lastUpdated={lastUpdated} />
        <LoadingSkeleton />
      </div>
    );
  }

  const healthData = [
    { name: 'Healthy', value: summary?.healthy_machines ?? 0 },
    { name: 'Warning', value: summary?.warning_machines ?? 0 },
    { name: 'Critical', value: summary?.critical_machines ?? 0 },
  ];

  const topRiskData = (summary?.recent_predictions ?? [])
    .slice(0, 8)
    .map((p) => ({
      name: p.machine_id || 'Unknown',
      probability: Math.round(p.failure_probability * 100),
    }));

  const recentAlerts: AlertItem[] = summary?.recent_alerts ?? [];

  const criticalAlerts = recentAlerts.filter((a) => a.severity === 'CRITICAL' && !a.is_resolved);

  const recentPredictions = (predictions ?? []).slice(0, 10);

  return (
    <div className="page-shell">
      <DashboardHeader onRefresh={handleRefresh} isRefreshing={refreshing} lastUpdated={lastUpdated} />

      {/* KPI Summary Cards */}
      <div className="kpi-grid">
        <KpiCard
          icon="🏭"
          label="Total Machines"
          value={summary?.total_machines ?? 0}
          trend="Fleet size"
          color="blue"
        />
        <KpiCard
          icon="✓"
          label="Healthy Machines"
          value={summary?.healthy_machines ?? 0}
          trend="Normal operation"
          color="green"
        />
        <KpiCard
          icon="⚡"
          label="Machines at Risk"
          value={summary?.warning_machines ?? 0}
          trend="Monitoring required"
          color="orange"
        />
        <KpiCard
          icon="⛔"
          label="Critical Machines"
          value={summary?.critical_machines ?? 0}
          trend="Action required"
          color="red"
        />
      </div>

      {/* Charts Row 1 */}
      <div className="grid-2">
        {/* Machine Health Overview */}
        <div className="chart-card">
          <div className="section-header">
            <h3>Machine Health Overview</h3>
          </div>
          {healthData.every((h) => h.value === 0) ? (
            <EmptyState
              title="No Prediction Data"
              message="No machine predictions available yet. Submit a real-time prediction to populate this chart."
            />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={healthData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={90}
                  paddingAngle={2}
                  label={({ name, value }) => `${name}\n${value}`}
                  labelLine={false}
                >
                  {healthData.map((entry, index) => (
                    <Cell key={entry.name} fill={HEALTH_COLORS[index % HEALTH_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value) => `${value} machine${(value as number) !== 1 ? 's' : ''}`}
                  contentStyle={{ backgroundColor: '#0f1f2f', border: '1px solid #213b56' }}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Failure Risk Trend */}
        <div className="chart-card">
          <div className="section-header">
            <h3>Failure Risk Trend (30 Days)</h3>
          </div>
          {trend.length === 0 ? (
            <EmptyState
              title="No Historical Data"
              message="No prediction history available yet. Make predictions to see the trend."
            />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={trend}>
                <defs>
                  <linearGradient id="colorProbability" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4aa3ff" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#4aa3ff" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#213b56" />
                <XAxis dataKey="name" stroke="#8aa0bd" tick={{ fontSize: 11 }} />
                <YAxis
                  domain={[0, 1]}
                  stroke="#8aa0bd"
                  tickFormatter={(v) => `${Math.round((v as number) * 100)}%`}
                />
                <Tooltip
                  formatter={(value) => `${((value as number) * 100).toFixed(1)}%`}
                  labelFormatter={(label) => `${label}`}
                  contentStyle={{ backgroundColor: '#0f1f2f', border: '1px solid #213b56' }}
                />
                <Area
                  type="monotone"
                  dataKey="probability"
                  stroke="#4aa3ff"
                  fillOpacity={1}
                  fill="url(#colorProbability)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="grid-2">
        {/* Top Risk Machines */}
        <div className="chart-card">
          <div className="section-header">
            <h3>Top Risk Machines (Failure %)</h3>
          </div>
          {topRiskData.length === 0 ? (
            <EmptyState
              title="No Risk Data"
              message="No machines with predictions yet. Submit predictions to see risk rankings."
            />
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={topRiskData} layout="vertical" margin={{ left: 80 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#213b56" horizontal={false} />
                <XAxis type="number" domain={[0, 100]} stroke="#8aa0bd" tickFormatter={(v) => `${v}%`} />
                <YAxis
                  type="category"
                  dataKey="name"
                  stroke="#8aa0bd"
                  width={75}
                  tick={{ fontSize: 11 }}
                />
                <Tooltip
                  formatter={(value) => `${value}%`}
                  contentStyle={{ backgroundColor: '#0f1f2f', border: '1px solid #213b56' }}
                />
                <Bar dataKey="probability" fill="#f59e0b" radius={[0, 8, 8, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Critical Alerts */}
        <div className="chart-card">
          <div className="section-header">
            <h3>Critical Alerts</h3>
          </div>
          {criticalAlerts.length === 0 ? (
            <div style={{ padding: '60px 20px', textAlign: 'center' }}>
              <div style={{ fontSize: 28, marginBottom: 10 }}>✓</div>
              <div style={{ color: '#2dd4bf', fontSize: 14, fontWeight: 600 }}>No Critical Alerts</div>
              <div style={{ color: '#8aa0bd', fontSize: 12, marginTop: 4 }}>
                All machines operating normally
              </div>
            </div>
          ) : (
            <div className="alert-list">
              {criticalAlerts.slice(0, 5).map((alert) => (
                <div key={alert.id} className="alert-item">
                  <div className="alert-header">
                    <span className="alert-machine">{alert.machine_id}</span>
                    <span className="status-pill status-critical">CRITICAL</span>
                  </div>
                  <div className="alert-title">{alert.title}</div>
                  <div className="alert-time">{new Date(alert.created_at).toLocaleString()}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Recent Predictions Table */}
      <div className="section-card">
        <div className="section-header">
          <h3>Recent Predictions</h3>
          {recentPredictions.length > 0 && (
            <a href="/predictions" className="secondary-button">
              View All Predictions
            </a>
          )}
        </div>
        {recentPredictions.length === 0 ? (
          <EmptyState
            title="No Predictions Yet"
            message="No prediction history available. Use the Predictions page to submit real-time machine analysis."
          />
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Machine</th>
                <th>Type</th>
                <th>Failure Probability</th>
                <th>Health Status</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {recentPredictions.map((pred) => (
                <tr key={pred.id}>
                  <td className="machine-cell">{pred.machine_id || 'Realtime Input'}</td>
                  <td>{pred.machine_id ? '—' : 'Sensor'}</td>
                  <td className="probability-cell">{(pred.failure_probability * 100).toFixed(2)}%</td>
                  <td>
                    <span className={`status-pill ${STATUS_CLASS[pred.health_status] ?? 'status-normal'}`}>
                      {pred.health_status}
                    </span>
                  </td>
                  <td className="timestamp-cell">{new Date(pred.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Machine Status Table */}
      <div className="section-card">
        <div className="section-header">
          <h3>Machine Status</h3>
        </div>
        {machines.length === 0 ? (
          <EmptyState
            title="No Machines"
            message="No machines available. Add machines to the system to see their status here."
          />
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Machine ID</th>
                <th>Name</th>
                <th>Type</th>
                <th>Status</th>
                <th>Failure Probability</th>
                <th>Health</th>
                <th>Last Updated</th>
              </tr>
            </thead>
            <tbody>
              {machines.map((machine) => {
                const lastPred = predictions.find((p) => p.machine_id === machine.machine_id);
                return (
                  <tr key={machine.id}>
                    <td className="machine-cell">{machine.machine_id}</td>
                    <td>{machine.name}</td>
                    <td>{machine.type}</td>
                    <td>
                      <span
                        className={`status-pill ${
                          machine.status === 'ACTIVE' ? 'status-normal' : 'status-warning'
                        }`}
                      >
                        {machine.status}
                      </span>
                    </td>
                    <td className="probability-cell">
                      {lastPred ? `${(lastPred.failure_probability * 100).toFixed(2)}%` : '—'}
                    </td>
                    <td>
                      {lastPred ? (
                        <span className={`status-pill ${STATUS_CLASS[lastPred.health_status] ?? 'status-normal'}`}>
                          {lastPred.health_status}
                        </span>
                      ) : (
                        <span style={{ color: '#8aa0bd' }}>—</span>
                      )}
                    </td>
                    <td className="timestamp-cell">
                      {lastPred ? new Date(lastPred.created_at).toLocaleString() : '—'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

