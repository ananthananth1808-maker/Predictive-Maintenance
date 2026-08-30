import { useEffect, useState } from 'react';
import { maintenanceApi } from '../services/api';
import type { MaintenanceRecord } from '../types';

export function MaintenancePage() {
  const [records, setRecords] = useState<MaintenanceRecord[]>([]);

  useEffect(() => {
    maintenanceApi.getAll().then((res) => setRecords(res.data)).catch(console.error);
  }, []);

  return (
    <div className="page-shell">
      <div className="section-header"><h1>Maintenance History</h1><button className="primary-button">Add Record</button></div>
      <div className="table-card">
        <table className="table">
          <thead>
            <tr>
              <th>Machine</th>
              <th>Type</th>
              <th>Description</th>
              <th>Technician</th>
              <th>Date</th>
              <th>Cost</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {records.map((record) => (
              <tr key={record.id}>
                <td>{record.machine_id}</td>
                <td>{record.maintenance_type}</td>
                <td>{record.description}</td>
                <td>{record.technician}</td>
                <td>{new Date(record.maintenance_date).toLocaleDateString()}</td>
                <td>${record.cost.toFixed(2)}</td>
                <td>{record.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
