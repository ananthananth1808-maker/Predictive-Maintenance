import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { DashboardLayout } from './layouts/DashboardLayout';
import { DashboardPage } from './pages/DashboardPage';
import { MachinesPage } from './pages/MachinesPage';
import { MachineDetailsPage } from './pages/MachineDetailsPage';
import { PredictionsPage } from './pages/PredictionsPage';
import { AlertsPage } from './pages/AlertsPage';
import { MaintenancePage } from './pages/MaintenancePage';
import { AIAssistantPage } from './pages/AIAssistantPage';
import { SettingsPage } from './pages/SettingsPage';
import { LoginPage } from './pages/LoginPage';

function App() {
  const isAuthenticated = true;

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="*"
          element={
            isAuthenticated ? (
              <DashboardLayout>
                <Routes>
                  <Route index element={<DashboardPage />} />
                  <Route path="machines" element={<MachinesPage />} />
                  <Route path="machines/:machineId" element={<MachineDetailsPage />} />
                  <Route path="predictions" element={<PredictionsPage />} />
                  <Route path="alerts" element={<AlertsPage />} />
                  <Route path="maintenance" element={<MaintenancePage />} />
                  <Route path="ai" element={<AIAssistantPage />} />
                  <Route path="settings" element={<SettingsPage />} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </DashboardLayout>
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
