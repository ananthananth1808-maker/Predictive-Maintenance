export function SettingsPage() {
  return (
    <div className="page-shell">
      <div className="section-header"><h1>Settings</h1></div>
      <div className="card">
        <div className="form-grid">
          <label>
            API Base URL
            <input className="input" placeholder="API Base URL" />
          </label>
          <label>
            LLM Provider
            <input className="input" defaultValue="Configured via environment variables" />
          </label>
          <button className="primary-button">Save Settings</button>
        </div>
      </div>
    </div>
  );
}
