import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { getNotebooks, createNotebook, deleteNotebook } from '../api/notebooks';
import { useAuth } from '../context/AuthContext';
import './Dashboard.css';

const COLOR_OPTIONS = [
  { label: 'Purple', value: '#7c5bf5' },
  { label: 'Blue', value: '#60a5fa' },
  { label: 'Green', value: '#4ade80' },
  { label: 'Orange', value: '#fb923c' },
  { label: 'Pink', value: '#f472b6' },
  { label: 'Yellow', value: '#fbbf24' },
];

const NOTEBOOK_GRID = [
  { icon: '📐', title: 'Create Diagram', desc: 'Visualize connections' },
  { icon: '💡', title: 'Ask AI', desc: 'Get instant answers' },
  { icon: '🔗', title: 'Add Resources', desc: 'PDFs, links, images' },
];

export default function Dashboard() {
  const [notebooks, setNotebooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ title: '', description: '', colorTheme: '#7c5bf5' });
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

  return (
    <div className="dashboard">
      {/* Hero */}
      <div className="dashboard-hero animate-fade-in">
        <div className="hero-text">
          <h1>Welcome back, {user?.name?.split(' ')[0] || 'there'} 👋</h1>
          <p>Your personal knowledge universe awaits. Build a notebook for each subject and let AI help you master it.</p>
        </div>
        <button className="btn-primary" onClick={() => setShowModal(true)}>
          <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
            <path d="M10 4v12M4 10h12" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
          </svg>
          New Notebook
        </button>
      </div>

      {/* Notebooks grid */}
      <div className="section-title">Your Notebooks</div>

      {loading ? (
        <div className="loading-grid">
          {[1, 2, 3].map((i) => (
            <div key={i} className="notebook-skeleton" />
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
              <div className="notebook-card-accent" style={{ background: nb.colorTheme || '#7c5bf5' }} />
              <div className="notebook-card-body">
                <div className="notebook-card-header">
                  <h3 className="notebook-title">{nb.title}</h3>
                  <button
                    className="notebook-delete btn-ghost"
                    onClick={(e) => handleDelete(nb.id, e)}
                    disabled={deletingId === nb.id}
                    title="Delete notebook"
                  >
                    {deletingId === nb.id ? <span className="spinner spinner-sm" /> : '🗑️'}
                  </button>
                </div>
                <p className="notebook-desc">{nb.description || 'No description'}</p>
                <div className="notebook-meta">
                  <span className="meta-item">📄 {nb.topics?.length || 0} topics</span>
                  <span className="meta-item">🕐 {new Date(nb.updatedAt || nb.createdAt).toLocaleDateString()}</span>
                </div>
              </div>
            </Link>
          ))}

          {/* Create card */}
          <button className="notebook-create-card" onClick={() => setShowModal(true)}>
            <div className="notebook-create-icon">+</div>
            <span>New Notebook</span>
          </button>
        </div>
      )}

      {/* Feature hints */}
      <div className="feature-grid">
        {NOTEBOOK_GRID.map((f) => (
          <div key={f.title} className="feature-card">
            <span className="feature-icon">{f.icon}</span>
            <div>
              <h4>{f.title}</h4>
              <p>{f.desc}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Create Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2 className="modal-title">Create Notebook</h2>
            <form onSubmit={handleCreate} className="modal-form">
              <div className="form-group">
                <label>Title</label>
                <input
                  type="text"
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  placeholder="e.g. Organic Chemistry"
                  required
                  autoFocus
                />
              </div>
              <div className="form-group">
                <label>Description (optional)</label>
                <input
                  type="text"
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="Brief description..."
                />
              </div>
              <div className="form-group">
                <label>Color Theme</label>
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
