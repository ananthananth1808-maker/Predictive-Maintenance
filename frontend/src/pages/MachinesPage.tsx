import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { machinesApi } from '../services/api';
import type { Machine } from '../types';

export function MachinesPage() {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [search, setSearch] = useState('');

  useEffect(() => {
    machinesApi.getAll().then((res) => setMachines(res.data)).catch(console.error);
  }, []);

  const filtered = machines.filter((machine) => machine.machine_id.toLowerCase().includes(search.toLowerCase()) || machine.name.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="page-shell">
      <div className="section-header">
        <h1>Machine Fleet</h1>
        <button className="secondary-button">Add Machine</button>
      </div>

      <div className="card">
        <input className="input" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by machine ID or name" />
      </div>

      <div className="table-card">
        <table className="table">
          <thead>
            <tr>
              <th>Machine ID</th>
              <th>Name</th>
              <th>Type</th>
              <th>Status</th>
              <th>Last Updated</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((machine) => (
              <tr key={machine.machine_id}>
                <td>{machine.machine_id}</td>
                <td>{machine.name}</td>
                <td>{machine.type}</td>
                <td><span className={`status-pill ${machine.status === 'ACTIVE' ? 'status-normal' : 'status-warning'}`}>{machine.status}</span></td>
                <td>{new Date(machine.created_at).toLocaleDateString()}</td>
                <td><Link to={`/machines/${machine.machine_id}`} className="secondary-button">Open</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
