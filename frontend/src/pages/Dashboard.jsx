import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { getNotebooks, createNotebook, deleteNotebook } from '../api/notebooks';
import { useAuth } from '../context/AuthContext';
import './Dashboard.css';

// Curated color palette for notebook cards
const NOTEBOOK_COLORS = [
  '#c4a5a5', // Dusty Rose
  '#7b95b0', // Slate Blue
  '#c4a55a', // Warm Amber
  '#6b8f62', // Forest
  '#9b7fa8', // Mauve
  '#c47a5a', // Terracotta
];

const COLOR_OPTIONS = [
  { label: 'Dusty Rose', value: '#c4a5a5' },
  { label: 'Slate Blue', value: '#7b95b0' },
  { label: 'Warm Amber', value: '#c4a55a' },
  { label: 'Forest', value: '#6b8f62' },
  { label: 'Mauve', value: '#9b7fa8' },
  { label: 'Terracotta', value: '#c47a5a' },
];

const QUICK_ACTIONS = [
  { icon: '💬', title: 'Continue last chat', desc: 'Resume your recent conversation', path: '/notebooks' },
  { icon: '🔥', title: 'Review flashcards', desc: 'Spaced repetition practice', path: '/study' },
  { icon: '⚡', title: 'Start study session', desc: 'AI-guided learning flow', path: '/study' },
];

export default function Dashboard() {
  const [notebooks, setNotebooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ title: '', description: '', colorTheme: '#c4a5a5' });
  const [creating, setCreating] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const { user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    loadNotebooks();
  }, []);

  const loadNotebooks = async () => {
    try {
      const res = await getNotebooks();
      setNotebooks(res.data.data || []);
    } catch (err) {
      console.error('Failed to load notebooks', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!form.title.trim()) return;
    setCreating(true);
    try {
      const res = await createNotebook(form);
      navigate(`/notebooks/${res.data.data.id}`);
    } catch (err) {
      alert('Failed to create notebook');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id, e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm('Delete this notebook and all its topics?')) return;
    setDeletingId(id);
    try {
      await deleteNotebook(id);
      setNotebooks((prev) => prev.filter((nb) => nb.id !== id));
    } catch {
      alert('Failed to delete');
    } finally {
      setDeletingId(null);
    }
  };

  // Get greeting based on time of day
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  };

  const totalTopics = notebooks.reduce((acc, nb) => acc + (nb.topics?.length || 0), 0);

  return (
    <div className="dashboard">
      {/* Hero Section */}
      <div className="dashboard-hero">
        <div className="hero-text">
          <h1>{getGreeting()}, {user?.name?.split(' ')[0] || 'there'}.</h1>
          <p>
            You have {notebooks.length} {notebooks.length === 1 ? 'notebook' : 'notebooks'} and {totalTopics} topics to explore.
          </p>
        </div>
        <div className="hero-decoration">
          <svg viewBox="0 0 120 120">
            <circle cx="60" cy="60" r="50" />
            <circle cx="60" cy="60" r="35" />
            <circle cx="60" cy="60" r="20" />
          </svg>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="stats-bar">
        <div className="stat-chip">
          <span className="stat-icon">📚</span>
          <span className="stat-number">{notebooks.length}</span>
          <span>Notebooks</span>
        </div>
        <div className="stats-divider" />
        <div className="stat-chip">
          <span className="stat-icon">💬</span>
          <span className="stat-number">{totalTopics}</span>
          <span>Topics</span>
        </div>
        <div className="stats-divider" />
        <div className="stat-chip">
          <span className="stat-icon">🔥</span>
          <span className="stat-number">5</span>
          <span>Day Streak</span>
        </div>
        <div className="stats-divider" />
        <div className="stat-chip">
          <span className="stat-icon">✅</span>
          <span className="stat-number">89%</span>
          <span>Quiz Score</span>
        </div>
      </div>

      {/* Notebooks Section */}
      <div className="notebooks-header">
        <h2>Your Notebooks</h2>
        <button className="btn-primary" onClick={() => setShowModal(true)}>
          <svg className="icon" viewBox="0 0 24 24" fill="none">
            <line x1="12" y1="5" x2="12" y2="19" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            <line x1="5" y1="12" x2="19" y2="12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
          New Notebook
        </button>
      </div>

      {loading ? (
        <div className="loading-grid">
          {[1, 2, 3].map((i) => (
            <div key={i} className="notebook-skeleton skeleton" />
          ))}
        </div>
      ) : notebooks.length === 0 ? (
        <div className="empty-state">
          <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
            <rect x="8" y="12" width="48" height="40" rx="8" stroke="currentColor" strokeWidth="2" />
            <path d="M20 24h24M20 32h24M20 40h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <h3>No notebooks yet</h3>
          <p>Create your first notebook to start building your knowledge universe</p>
          <button className="btn-primary" onClick={() => setShowModal(true)}>Create Notebook</button>
        </div>
      ) : (
        <div className="notebooks-grid">
          {notebooks.map((nb, i) => (
            <Link
              to={`/notebooks/${nb.id}`}
              key={nb.id}
              className="notebook-card animate-fade-in"
              style={{ animationDelay: `${i * 60}ms` }}
            >
              <div
                className="notebook-card-accent"
                style={{ background: nb.colorTheme || NOTEBOOK_COLORS[i % NOTEBOOK_COLORS.length] }}
              />
              <div className="notebook-card-body">
                <div className="notebook-card-header">
                  <h3 className="notebook-title">{nb.title}</h3>
                  <button
                    className="notebook-delete btn-ghost"
                    onClick={(e) => handleDelete(nb.id, e)}
                    disabled={deletingId === nb.id}
                    title="Delete notebook"
                  >
                    {deletingId === nb.id ? <span className="spinner spinner-sm" /> : '×'}
                  </button>
                </div>
                <p className="notebook-desc">{nb.description || 'No description'}</p>
                <div className="notebook-meta">
                  <span className="meta-item">📄 {nb.topics?.length || 0} topics</span>
                  <span className="meta-item" style={{ fontStyle: 'italic' }}>
                    {new Date(nb.updatedAt || nb.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  </span>
                </div>
              </div>
              <div className="notebook-footer">
                <div className="notebook-avatars">
                  {(nb.topics || []).slice(0, 3).map((topic, j) => (
                    <div
                      key={topic.id}
                      className="topic-dot"
                      style={{ background: topic.color || '#6b8f62' }}
                    />
                  ))}
                </div>
                <span className="notebook-open-text">Open →</span>
              </div>
            </Link>
          ))}

          {/* Create card */}
          <button className="notebook-create-card" onClick={() => setShowModal(true)}>
            <span className="notebook-create-icon">+</span>
            <span>New Notebook</span>
          </button>
        </div>
      )}

      {/* Quick Actions */}
      <div className="quick-actions">
        <h3>Jump back in</h3>
        <div className="actions-grid">
          {QUICK_ACTIONS.map((action) => (
            <div key={action.title} className="action-card" onClick={() => navigate(action.path || '/')}>
              <div className="action-icon">{action.icon}</div>
              <div className="action-content">
                <h4>{action.title}</h4>
                <p>{action.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Create Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2 className="modal-title">Create Notebook</h2>
            <form onSubmit={handleCreate} className="modal-form">
              <div className="input-group">
                <input
                  type="text"
                  id="title"
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  placeholder=" "
                  required
                  autoFocus
                />
                <label htmlFor="title" className="input-label">Title</label>
              </div>
              <div className="input-group">
                <input
                  type="text"
                  id="description"
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder=" "
                />
                <label htmlFor="description" className="input-label">Description (optional)</label>
              </div>
              <div className="form-group">
                <label className="input-label">Color Theme</label>
                <div className="color-picker">
                  {COLOR_OPTIONS.map((c) => (
                    <button
                      key={c.value}
                      type="button"
                      className={`color-swatch ${form.colorTheme === c.value ? 'selected' : ''}`}
                      style={{ background: c.value }}
                      onClick={() => setForm({ ...form, colorTheme: c.value })}
                      title={c.label}
                    />
                  ))}
                </div>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn-primary" disabled={creating}>
                  {creating ? <span className="spinner spinner-sm" /> : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}