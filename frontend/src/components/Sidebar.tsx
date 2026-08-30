import { NavLink } from 'react-router-dom';

const navItems = [
  { label: 'Dashboard', path: '/' },
  { label: 'Machines', path: '/machines' },
  { label: 'Predictions', path: '/predictions' },
  { label: 'Alerts', path: '/alerts' },
  { label: 'Maintenance', path: '/maintenance' },
  { label: 'AI Assistant', path: '/ai' },
];

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand-block">
        <div className="brand-mark">M</div>
        <div>
          <div className="brand-name">MaintenAI</div>
          <div className="brand-subtitle">Operations</div>
        </div>
      </div>

      <nav className="nav-list">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
