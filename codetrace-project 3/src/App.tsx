import { Route, Routes } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import Overview from './pages/Overview';
import Ask from './pages/Ask';
import GraphPage from './pages/GraphPage';
import TimelinePage from './pages/TimelinePage';
import Explorer from './pages/Explorer';
import EvidenceLibrary from './pages/EvidenceLibrary';
import EvaluationLab from './pages/EvaluationLab';
import SettingsPage from './pages/SettingsPage';
import { EmptyState } from './components/ui';
import AuthPage from './pages/AuthPage';

export default function App() {
  return (
    <Routes>
      <Route path="login" element={<AuthPage />} />
      <Route element={<AppShell />}>
        <Route index element={<Overview />} />
        <Route path="ask" element={<Ask />} />
        <Route path="graph" element={<GraphPage />} />
        <Route path="timeline" element={<TimelinePage />} />
        <Route path="explorer" element={<Explorer />} />
        <Route path="evidence" element={<EvidenceLibrary />} />
        <Route path="evaluation" element={<EvaluationLab />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<EmptyState title="Page not found" desc="This route does not exist." />} />
      </Route>
    </Routes>
  );
}
