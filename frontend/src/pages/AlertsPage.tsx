import { useEffect, useState } from 'react';
import { alertsApi } from '../services/api';
import type { AlertItem } from '../types';

// ── helpers ─────────────────────────────────────────────────────────────────

type FilterTab = 'all' | 'active' | 'resolved' | 'critical' | 'warning';

const SEV_CLASS: Record<string, string> = {
  CRITICAL: 'status-critical',
  WARNING: 'status-warning',
  NORMAL: 'status-normal',
};

function fmt(dt: string) {
  return new Date(dt).toLocaleString();
}

// ── main page ────────────────────────────────────────────────────────────────

export function AlertsPage() {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterTab>('all');
  const [resolvingIds, setResolvingIds] = useState<Set<number>>(new Set());

  // Load all alerts
  const fetchAlerts = () => {
    setLoading(true);
    setError(null);
    alertsApi
      .getAll()
      .then((res) => setAlerts(res.data as AlertItem[]))
      .catch(() => setError('Failed to load alerts. Is the backend running?'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchAlerts();
  }, []);

  // Resolve a single alert
  const handleResolve = async (alertId: number) => {
    setResolvingIds((prev) => new Set(prev).add(alertId));
    try {
      const res = await alertsApi.resolve(alertId);
      const updated = res.data as AlertItem;
      // Optimistic update: replace the alert in state
      setAlerts((prev) =>
        prev.map((a) => (a.id === alertId ? updated : a))
      );
    } catch (err: unknown) {
      const axiosErr = err as { response?: { status: number } };
      if (axiosErr?.response?.status === 404) {
        alert('Alert not found. It may have already been removed.');
      } else {
        alert('Failed to resolve alert. Please try again.');
      }
    } finally {
      setResolvingIds((prev) => {
        const next = new Set(prev);
        next.delete(alertId);
        return next;
      });
    }
  };

  // Client-side filtering
  const filtered = alerts.filter((a) => {
    if (filter === 'active') return !a.is_resolved;
    if (filter === 'resolved') return a.is_resolved;
    if (filter === 'critical') return a.severity === 'CRITICAL';
    if (filter === 'warning') return a.severity === 'WARNING';
    return true;
  });

  const activeCount = alerts.filter((a) => !a.is_resolved).length;
  const criticalCount = alerts.filter((a) => a.severity === 'CRITICAL' && !a.is_resolved).length;

  // ── filter tab list ──────────────────────────────────────────────────────

  const TABS: { key: FilterTab; label: string }[] = [
    { key: 'all', label: `All (${alerts.length})` },
    { key: 'active', label: `Active (${activeCount})` },
    { key: 'resolved', label: `Resolved (${alerts.filter((a) => a.is_resolved).length})` },
    { key: 'critical', label: `Critical (${criticalCount})` },
    { key: 'warning', label: `Warning (${alerts.filter((a) => a.severity === 'WARNING').length})` },
  ];

  // ── render ───────────────────────────────────────────────────────────────

  return (
    <div className="page-shell">

      {/* Header */}
      <div className="section-header">
        <div>
          <h1 style={{ margin: 0 }}>Alerts</h1>
          {!loading && !error && (
            <div style={{ color: '#8aa0bd', fontSize: 13, marginTop: 3 }}>
              {activeCount} active alert{activeCount !== 1 ? 's' : ''}
              {criticalCount > 0 && (
                <span style={{ color: '#f87171', marginLeft: 10 }}>
                  {criticalCount} critical
                </span>
              )}
            </div>
          )}
        </div>
        <button
          id="btn-refresh-alerts"
          className="secondary-button"
          onClick={fetchAlerts}
          disabled={loading}
        >
          {loading ? 'Loading…' : '↻ Refresh'}
        </button>
      </div>

      {/* Filter tabs */}
      <div
        className="card"
        style={{ padding: '10px 14px', display: 'flex', gap: 8, flexWrap: 'wrap' }}
      >
        {TABS.map((tab) => (
          <button
            key={tab.key}
            id={`filter-${tab.key}`}
            onClick={() => setFilter(tab.key)}
            style={{
              background: filter === tab.key ? 'rgba(74,163,255,0.2)' : 'transparent',
              color: filter === tab.key ? '#4aa3ff' : '#8aa0bd',
              border: filter === tab.key ? '1px solid rgba(74,163,255,0.4)' : '1px solid transparent',
              borderRadius: 8,
              padding: '6px 14px',
              cursor: 'pointer',
              fontSize: 13,
              fontWeight: filter === tab.key ? 700 : 400,
              transition: '0.15s ease',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Loading state */}
      {loading && (
        <div className="card" style={{ textAlign: 'center', padding: 40, color: '#8aa0bd' }}>
          Loading alerts…
        </div>
      )}

      {/* Error state */}
      {!loading && error && (
        <div
          className="card"
          style={{ textAlign: 'center', padding: 40, color: '#f87171', fontSize: 14 }}
        >
          {error}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && filtered.length === 0 && (
        <div
          className="card"
          style={{ textAlign: 'center', padding: 40, color: '#8aa0bd', fontSize: 14 }}
        >
          {filter === 'all'
            ? 'No alerts in the database.'
            : `No ${filter} alerts found.`}
        </div>
      )}

      {/* Alerts table */}
      {!loading && !error && filtered.length > 0 && (
        <div className="table-card">
          <table className="table">
            <thead>
              <tr>
                <th>Severity</th>
                <th>Machine</th>
                <th>Title</th>
                <th>Message</th>
                <th>Created</th>
                <th>Status</th>
                <th>Resolved At</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((alert) => {
                const isResolving = resolvingIds.has(alert.id);
                return (
                  <tr key={alert.id}>
                    {/* Severity */}
                    <td>
                      <span className={`status-pill ${SEV_CLASS[alert.severity] ?? 'status-normal'}`}>
                        {alert.severity}
                      </span>
                    </td>

                    {/* Machine */}
                    <td style={{ fontWeight: 600, fontSize: 13 }}>
                      {alert.machine_id}
                    </td>

                    {/* Title */}
                    <td style={{ fontSize: 13 }}>
                      {alert.title}
                    </td>

                    {/* Message */}
                    <td style={{ fontSize: 12, color: '#8aa0bd', maxWidth: 280 }}>
                      {alert.message}
                    </td>

                    {/* Created at */}
                    <td style={{ fontSize: 12, color: '#8aa0bd', whiteSpace: 'nowrap' }}>
                      {fmt(alert.created_at)}
                    </td>

                    {/* Status badge */}
                    <td>
                      {alert.is_resolved ? (
                        <span className="status-pill status-normal">Resolved</span>
                      ) : (
                        <span className="status-pill status-warning">Active</span>
                      )}
                    </td>

                    {/* Resolved at */}
                    <td style={{ fontSize: 12, color: '#8aa0bd', whiteSpace: 'nowrap' }}>
                      {alert.resolved_at ? fmt(alert.resolved_at) : '—'}
                    </td>

                    {/* Action */}
                    <td>
                      {!alert.is_resolved && (
                        <button
                          id={`resolve-alert-${alert.id}`}
                          className="secondary-button"
                          style={{ fontSize: 12, padding: '6px 12px', opacity: isResolving ? 0.6 : 1 }}
                          onClick={() => handleResolve(alert.id)}
                          disabled={isResolving}
                        >
                          {isResolving ? 'Resolving…' : 'Resolve'}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {/* Footer count */}
          <div style={{ color: '#8aa0bd', fontSize: 12, marginTop: 12, textAlign: 'right' }}>
            Showing {filtered.length} of {alerts.length} alerts
          </div>
        </div>
      )}

    </div>
  );
}

