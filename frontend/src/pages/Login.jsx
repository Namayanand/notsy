import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Auth.css';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.message || 'Login failed. Check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      {/* Left Panel — Decorative */}
      <div className="auth-panel-left">
        <div className="auth-rings">
          <svg viewBox="0 0 200 200">
            <circle cx="100" cy="100" r="90" />
            <circle cx="100" cy="100" r="70" />
            <circle cx="100" cy="100" r="50" />
            <circle cx="100" cy="100" r="30" />
          </svg>
        </div>

        <div className="auth-quote">
          <blockquote>
            "Knowledge is not a vessel to be filled,<br />
            but a fire to be kindled."
          </blockquote>
          <cite>— Plutarch</cite>
        </div>

        <div className="auth-logo">
          <span className="auth-logo-text">NOTSY</span>
          <span className="auth-logo-tagline">knowledge universe</span>
        </div>
      </div>

      {/* Right Panel — Form */}
      <div className="auth-panel-right">
        <div className="auth-card">
          {/* Mobile logo */}
          <div className="auth-logo-mobile">
            <span className="auth-logo-text">NOTSY</span>
          </div>

          <h1 className="auth-title">Welcome back.</h1>
          <p className="auth-subtitle">Sign in to continue learning</p>

          <form onSubmit={handleSubmit} className="auth-form">
            {error && <div className="auth-error">{error}</div>}

            <div className="form-group">
              <label htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                autoComplete="email"
              />
            </div>

            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                autoComplete="current-password"
              />
            </div>

            <button type="submit" className="btn-primary btn-submit" disabled={loading}>
              {loading ? <span className="spinner spinner-sm" /> : 'Sign In'}
            </button>
          </form>

          <p className="auth-switch">
            Don't have an account? <Link to="/register">Create one</Link>
          </p>
        </div>
      </div>
    </div>
  );
}