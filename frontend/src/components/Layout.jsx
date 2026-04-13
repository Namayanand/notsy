import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Layout.css';

const NavItem = ({ to, icon, label, badge }) => (
  <Link to={to} className={`nav-item ${useLocation().pathname === to ? 'active' : ''}`}>
    <span className="nav-icon">{icon}</span>
    <span className="nav-label">{label}</span>
    {badge && <span className="nav-badge">{badge}</span>}
  </Link>
);

export default function Layout({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className={`layout ${sidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}>
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <Link to="/" className="sidebar-logo">
            <svg width="28" height="28" viewBox="0 0 40 40" fill="none">
              <rect width="40" height="40" rx="10" fill="url(#sidebarLogoGrad)" />
              <path d="M12 20L18 26L28 14" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
              <defs>
                <linearGradient id="sidebarLogoGrad" x1="0" y1="0" x2="40" y2="40">
                  <stop stopColor="#7c5bf5" />
                  <stop offset="1" stopColor="#5f3fd4" />
                </linearGradient>
              </defs>
            </svg>
            <span>NOTSY</span>
          </Link>
          <button className="sidebar-toggle btn-ghost" onClick={() => setSidebarOpen(!sidebarOpen)}>
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        <nav className="sidebar-nav">
          <span className="nav-section-label">Workspace</span>
          <NavItem to="/" icon="📚" label="Notebooks" />
          <NavItem to="/graph" icon="🕸️" label="Knowledge Graph" />
          <NavItem to="/profile" icon="👤" label="Profile" />
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-user">
            <div className="sidebar-avatar">
              {user?.name?.[0]?.toUpperCase() || 'U'}
            </div>
            <div className="sidebar-user-info">
              <span className="sidebar-user-name">{user?.name}</span>
              <span className="sidebar-user-email">{user?.email}</span>
            </div>
          </div>
          <button className="btn-ghost logout-btn" onClick={handleLogout} title="Sign out">
            <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
              <path d="M13 3l4 4-4 4M17 7H7M7 10l4-4-4-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" transform="translate(-2, 0)" />
            </svg>
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="main-content">
        <header className="topbar">
          <div className="topbar-left">
            <button className="mobile-menu-btn btn-ghost" onClick={() => setSidebarOpen(!sidebarOpen)}>
              <svg width="22" height="22" viewBox="0 0 20 20" fill="none">
                <path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </button>
          </div>
          <div className="topbar-right">
            <div className="topbar-status">
              <span className="status-dot" />
              <span className="status-text">AI Active</span>
            </div>
          </div>
        </header>

        <div className="content-area">
          {children}
        </div>
      </main>

      {/* Overlay for mobile */}
      {sidebarOpen && <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />}
    </div>
  );
}
