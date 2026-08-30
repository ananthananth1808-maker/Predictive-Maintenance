import { useEffect, useState } from 'react';
import { predictionsApi } from '../services/api';
import type { Prediction } from '../types';

type PredictionResult = {
  machine_id: string | null;
  failure_probability: number;
  health_status: 'NORMAL' | 'WARNING' | 'CRITICAL';
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  created_at?: string | null;
};

type PredictionFormState = {
  type: 'L' | 'M' | 'H';
  air_temperature: string;
  process_temperature: string;
  rotational_speed: string;
  torque: string;
  tool_wear: string;
};

const emptyForm: PredictionFormState = {
  type: 'M',
  air_temperature: '',
  process_temperature: '',
  rotational_speed: '',
  torque: '',
  tool_wear: '',
};

const healthClass: Record<string, string> = {
  NORMAL: 'status-normal',
  WARNING: 'status-warning',
  CRITICAL: 'status-critical',
};

const healthTint: Record<string, string> = {
  NORMAL: '#2dd4bf',
  WARNING: '#f59e0b',
  CRITICAL: '#f87171',
};

const riskClass: Record<string, string> = {
  LOW: 'status-normal',
  MEDIUM: 'status-warning',
  HIGH: 'status-critical',
};

export function PredictionsPage() {
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<PredictionFormState>(emptyForm);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [result, setResult] = useState<PredictionResult | null>(null);

  const fetchPredictions = async () => {
    try {
      const res = await predictionsApi.getAll();
      setPredictions(res.data as Prediction[]);
    } catch (error) {
      console.error('Failed to load prediction history', error);
    }
  };

  useEffect(() => {
    fetchPredictions();
  }, []);

  const validateForm = () => {
    const nextErrors: Record<string, string> = {};

    if (!['L', 'M', 'H'].includes(form.type)) {
      nextErrors.type = 'Machine Type must be L, M, or H.';
    }

    const numericFields: Array<{ key: keyof PredictionFormState; label: string; allowZero: boolean }> = [
      { key: 'air_temperature', label: 'Air Temperature', allowZero: false },
      { key: 'process_temperature', label: 'Process Temperature', allowZero: false },
      { key: 'rotational_speed', label: 'Rotational Speed', allowZero: false },
      { key: 'torque', label: 'Torque', allowZero: false },
      { key: 'tool_wear', label: 'Tool Wear', allowZero: true },
    ];

    numericFields.forEach(({ key, label, allowZero }) => {
      const raw = form[key];
      if (raw === '') {
        nextErrors[key] = `${label} is required.`;
        return;
      }

      const value = Number(raw);
      if (Number.isNaN(value) || !Number.isFinite(value)) {
        nextErrors[key] = `${label} must be a valid number.`;
        return;
      }

      if (allowZero ? value < 0 : value <= 0) {
        nextErrors[key] = `${label} must be a valid positive number.`;
      }
    });

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleInputChange = (field: keyof PredictionFormState, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => {
      if (!prev[field]) return prev;
      const next = { ...prev };
      delete next[field];
      return next;
    });
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitError(null);

    if (!validateForm()) return;

    setIsSubmitting(true);
    try {
      const payload = {
        type: form.type,
        air_temperature: Number(form.air_temperature),
        process_temperature: Number(form.process_temperature),
        rotational_speed: Number(form.rotational_speed),
        torque: Number(form.torque),
        tool_wear: Number(form.tool_wear),
      };

      const res = await predictionsApi.create(payload);
      const data = res.data as PredictionResult;
      setResult(data);
      await fetchPredictions();
    } catch (error: any) {
      const status = error?.response?.status;
      if (status === 400 || status === 422) {
        setSubmitError('The prediction request is invalid. Please check the sensor values and try again.');
      } else if (status === 500) {
        setSubmitError('Prediction failed due to a server error. Please try again in a moment.');
      } else if (!error?.response) {
        setSubmitError('Unable to connect to the prediction service. Please make sure the backend is running.');
      } else {
        setSubmitError('Prediction failed. Please check your inputs and try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReset = () => {
    setForm(emptyForm);
    setErrors({});
    setSubmitError(null);
    setResult(null);
  };

  const recommendation = result
    ? result.health_status === 'NORMAL'
      ? 'Machine is currently operating within the predicted safe range. Continue regular monitoring.'
      : result.health_status === 'WARNING'
        ? 'Elevated failure risk detected. Inspect the machine and continue monitoring.'
        : 'High failure risk detected. Schedule immediate inspection.'
    : null;

  return (
    <div className="page-shell">
      <div className="section-header">
        <h1>Predictions</h1>
        <button className="primary-button" type="button" onClick={() => setShowForm((prev) => !prev)}>
          + New Prediction
        </button>
      </div>

      {showForm && (
        <div className="card prediction-form-card">
          <div style={{ marginBottom: 18 }}>
            <h3 style={{ margin: 0, fontSize: '1.4rem' }}>Real-Time Machine Prediction</h3>
            <div style={{ color: '#8aa0bd', marginTop: 6, fontSize: 13 }}>
              Enter current machine sensor readings to predict failure risk using the trained AI model.
            </div>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="prediction-form-grid">
              <div className="prediction-field">
                <label htmlFor="prediction-type">Machine Type</label>
                <select
                  id="prediction-type"
                  className="input"
                  value={form.type}
                  onChange={(e) => handleInputChange('type', e.target.value as 'L' | 'M' | 'H')}
                >
                  <option value="L">L</option>
                  <option value="M">M</option>
                  <option value="H">H</option>
                </select>
                {errors.type && <span className="field-error">{errors.type}</span>}
              </div>

              <div className="prediction-field">
                <label htmlFor="air-temperature">Air Temperature (K)</label>
                <input
                  id="air-temperature"
                  className="input"
                  type="number"
                  step="0.1"
                  placeholder="300"
                  value={form.air_temperature}
                  onChange={(e) => handleInputChange('air_temperature', e.target.value)}
                />
                {errors.air_temperature && <span className="field-error">{errors.air_temperature}</span>}
              </div>

              <div className="prediction-field">
                <label htmlFor="process-temperature">Process Temperature (K)</label>
                <input
                  id="process-temperature"
                  className="input"
                  type="number"
                  step="0.1"
                  placeholder="310"
                  value={form.process_temperature}
                  onChange={(e) => handleInputChange('process_temperature', e.target.value)}
                />
                {errors.process_temperature && <span className="field-error">{errors.process_temperature}</span>}
              </div>

              <div className="prediction-field">
                <label htmlFor="rotational-speed">Rotational Speed (RPM)</label>
                <input
                  id="rotational-speed"
                  className="input"
                  type="number"
                  step="1"
                  placeholder="1500"
                  value={form.rotational_speed}
                  onChange={(e) => handleInputChange('rotational_speed', e.target.value)}
                />
                {errors.rotational_speed && <span className="field-error">{errors.rotational_speed}</span>}
              </div>

              <div className="prediction-field">
                <label htmlFor="torque">Torque (Nm)</label>
                <input
                  id="torque"
                  className="input"
                  type="number"
                  step="0.1"
                  placeholder="40"
                  value={form.torque}
                  onChange={(e) => handleInputChange('torque', e.target.value)}
                />
                {errors.torque && <span className="field-error">{errors.torque}</span>}
              </div>

              <div className="prediction-field">
                <label htmlFor="tool-wear">Tool Wear (min)</label>
                <input
                  id="tool-wear"
                  className="input"
                  type="number"
                  step="0.1"
                  placeholder="100"
                  value={form.tool_wear}
                  onChange={(e) => handleInputChange('tool_wear', e.target.value)}
                />
                {errors.tool_wear && <span className="field-error">{errors.tool_wear}</span>}
              </div>
            </div>

            {submitError && (
              <div className="form-alert" role="alert">
                {submitError}
              </div>
            )}

            <div className="prediction-form-actions">
              <button className="primary-button" type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Analyzing Machine...' : 'Predict Machine Health'}
              </button>
              <button className="secondary-button" type="button" onClick={handleReset}>
                Reset
              </button>
            </div>
          </form>
        </div>
      )}

      {result && (
        <div className="card result-card">
          <div className="section-header" style={{ marginBottom: 18 }}>
            <h3 style={{ margin: 0 }}>AI Prediction Result</h3>
            <span className={`status-pill ${healthClass[result.health_status] ?? 'status-normal'}`}>
              {result.health_status}
            </span>
          </div>

          <div className="result-grid">
            <div className="metric-block">
              <div className="metric-label">Failure Probability</div>
              <div className="metric-value">{(result.failure_probability * 100).toFixed(2)}%</div>
            </div>

            <div className="metric-block">
              <div className="metric-label">Health Status</div>
              <div className={`metric-value status-pill ${healthClass[result.health_status] ?? 'status-normal'}`}>
                {result.health_status}
              </div>
            </div>

            <div className="metric-block">
              <div className="metric-label">Risk Level</div>
              <div className={`metric-value status-pill ${riskClass[result.risk_level] ?? 'status-normal'}`}>
                {result.risk_level}
              </div>
            </div>
          </div>

          <div style={{ marginTop: 18 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span style={{ color: '#8aa0bd', fontSize: 13 }}>Failure Probability</span>
              <span style={{ color: '#e5eefb', fontWeight: 700 }}>{(result.failure_probability * 100).toFixed(2)}%</span>
            </div>
            <div className="probability-bar-track">
              <div
                className="probability-bar-fill"
                style={{
                  width: `${Math.min(Math.max(result.failure_probability * 100, 0), 100)}%`,
                  background: healthTint[result.health_status] ?? '#4aa3ff',
                }}
              />
            </div>
          </div>

          {recommendation && (
            <div className="recommendation-banner" style={{ marginTop: 20 }}>
              {recommendation}
            </div>
          )}
        </div>
      )}

      <div className="section-header">
        <h2 style={{ margin: 0, fontSize: '1.3rem' }}>Prediction History</h2>
      </div>

      <div className="table-card">
        {predictions.length === 0 ? (
          <div style={{ color: '#8aa0bd', padding: '18px 8px' }}>
            No prediction history yet. Make your first real-time prediction to see results here.
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Machine</th>
                <th>Health</th>
                <th>Failure Probability</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {predictions.map((item) => (
                <tr key={item.id}>
                  <td>{item.machine_id ?? 'Realtime Input'}</td>
                  <td>
                    <span className={`status-pill ${item.health_status === 'CRITICAL' ? 'status-critical' : item.health_status === 'WARNING' ? 'status-warning' : 'status-normal'}`}>
                      {item.health_status}
                    </span>
                  </td>
                  <td>{(item.failure_probability * 100).toFixed(2)}%</td>
                  <td>{new Date(item.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
