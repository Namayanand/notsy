import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { AuthGuard, GuestGuard } from './components/AuthGuard';
import Layout from './components/Layout';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Notebook from './pages/Notebook';
import GraphPage from './pages/GraphPage';
import Profile from './pages/Profile';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<GuestGuard><Login /></GuestGuard>} />
          <Route path="/register" element={<GuestGuard><Register /></GuestGuard>} />
          <Route path="/" element={<AuthGuard><Layout><Dashboard /></Layout></AuthGuard>} />
          <Route path="/notebooks/:id" element={<AuthGuard><Layout><Notebook /></Layout></AuthGuard>} />
          <Route path="/notebooks/:nbId/topics/:topicId" element={<AuthGuard><Layout><Notebook /></Layout></AuthGuard>} />
          <Route path="/notebooks/:nbId/topics/:topicId/conversations/:convId" element={<AuthGuard><Layout><Notebook /></Layout></AuthGuard>} />
          <Route path="/notebooks/:id/graph" element={<AuthGuard><Layout><GraphPage /></Layout></AuthGuard>} />
          <Route path="/profile" element={<AuthGuard><Layout><Profile /></Layout></AuthGuard>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
