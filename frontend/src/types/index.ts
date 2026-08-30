export type MachineStatus = 'ACTIVE' | 'MAINTENANCE' | 'OFFLINE';
export type HealthStatus = 'NORMAL' | 'WARNING' | 'CRITICAL';
export type AlertSeverity = 'CRITICAL' | 'WARNING' | 'NORMAL';

export interface Machine {
  id: number;
  machine_id: string;
  name: string;
  type: string;
  location: string;
  installation_date: string;
  status: MachineStatus;
  created_at: string;
}

export interface SensorReading {
  id: number;
  machine_id: string;
  air_temperature: number;
  process_temperature: number;
  rotational_speed: number;
  torque: number;
  tool_wear: number;
  recorded_at: string;
}

export interface Prediction {
  id: number;
  machine_id: string;
  failure_probability: number;
  health_status: HealthStatus;
  model_version: string;
  created_at: string;
}

export interface AlertItem {
  id: number;
  machine_id: string;
  severity: AlertSeverity;
  title: string;
  message: string;
  is_resolved: boolean;
  created_at: string;
  resolved_at?: string | null;
}

export interface MaintenanceRecord {
  id: number;
  machine_id: string;
  maintenance_type: string;
  description: string;
  technician: string;
  maintenance_date: string;
  cost: number;
  status: string;
}

export interface DashboardSummary {
  total_machines: number;
  healthy_machines: number;
  warning_machines: number;
  critical_machines: number;
  active_alerts: number;
  recent_predictions: Prediction[];
  recent_alerts: AlertItem[];
  maintenance_count: number;
}

export interface AIAnalysis {
  summary: string;
  possible_causes: string[];
  recommended_actions: string[];
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
}
