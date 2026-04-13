import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export const AuthGuard = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="spinner spinner-lg" />
      </div>
    );
  }

  if (!user) return <Navigate to="/login" replace />;
  return children;
};

export const GuestGuard = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="spinner spinner-lg" />
      </div>
    );
  }

  if (user) return <Navigate to="/" replace />;
  return children;
};
