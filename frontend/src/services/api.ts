import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const machinesApi = {
  getAll: () => api.get('/machines'),
  getById: (machineId: string) => api.get(`/machines/${machineId}`),
  create: (payload: Record<string, unknown>) => api.post('/machines', payload),
  getSensors: (machineId: string, limit = 50) => api.get(`/machines/${machineId}/sensors`, { params: { limit } }),
  getPredictions: (machineId: string, limit = 50) => api.get(`/machines/${machineId}/predictions`, { params: { limit } }),
  getAlerts: (machineId: string, limit = 50) => api.get(`/machines/${machineId}/alerts`, { params: { limit } }),
  getMaintenance: (machineId: string, limit = 50) => api.get(`/machines/${machineId}/maintenance`, { params: { limit } }),
};

export const predictionsApi = {
  create: (payload: Record<string, unknown>) => api.post('/predict', payload),
  getAll: () => api.get('/predictions'),
};

export const alertsApi = {
  getAll: () => api.get('/alerts'),
  resolve: (id: number) => api.patch(`/alerts/${id}/resolve`),
};

export const maintenanceApi = {
  getAll: () => api.get('/maintenance'),
  create: (payload: Record<string, unknown>) => api.post('/maintenance', payload),
};

export const aiApi = {
  analyze: (machineId: string, question: string) => api.post('/ai/analyze', null, { params: { machine_id: machineId, question } }),
};

export const dashboardApi = {
  getSummary: () => api.get('/dashboard/summary'),
  getTrend: () => api.get('/dashboard/trend'),
};
