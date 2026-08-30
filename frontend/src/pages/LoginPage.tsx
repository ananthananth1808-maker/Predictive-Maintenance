export function LoginPage() {
  return (
    <div className="login-shell">
      <div className="login-card">
        <h1 style={{ marginTop: 0 }}>MaintenAI</h1>
        <p style={{ color: '#8aa0bd', marginBottom: 20 }}>Development authentication layer only.</p>
        <div className="form-grid">
          <input className="input" placeholder="Email or username" />
          <input className="input" type="password" placeholder="Password" />
          <button className="primary-button">Sign in</button>
        </div>
      </div>
    </div>
  );
}
