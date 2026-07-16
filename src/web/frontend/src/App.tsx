import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import ChatPage from './pages/Chat';
import DebugPage from './pages/Debug';
import KnowledgePage from './pages/Knowledge';
import SchedulePage from './pages/Schedule';
import EventPage from './pages/Event';
import NPSPage from './pages/NPS';
import DatabasePage from './pages/Database';
import CreativePage from './pages/Creative';
import SettingsPage from './pages/Settings';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/chat" replace />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/debug" element={<DebugPage />} />
        <Route path="/knowledge" element={<KnowledgePage />} />
        <Route path="/schedule" element={<SchedulePage />} />
        <Route path="/event" element={<EventPage />} />
        <Route path="/nps" element={<NPSPage />} />
        <Route path="/database" element={<DatabasePage />} />
        <Route path="/creative" element={<CreativePage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/chat" replace />} />
      </Route>
    </Routes>
  );
}
