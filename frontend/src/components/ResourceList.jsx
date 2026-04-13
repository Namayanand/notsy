import { useState, useEffect } from 'react';
import { getResources, deleteResource, reembedResource } from '../api/resources';
import './ResourceList.css';

const FILE_ICONS = {
  pdf: '📄',
  image: '🖼️',
  video: '🎬',
  link: '🔗',
  text: '📝',
};

export default function ResourceList({ topicId }) {
  const [resources, setResources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState(null);
  const [reembeddingId, setReembeddingId] = useState(null);

  useEffect(() => {
    loadResources();
  }, [topicId]);

  const loadResources = async () => {
    setLoading(true);
    try {
      const res = await getResources(topicId);
      setResources(res.data.data || []);
    } catch (err) {
      console.error('Failed to load resources', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (resourceId, e) => {
    e.stopPropagation();
    if (!confirm('Delete this resource?')) return;
    setDeletingId(resourceId);
    try {
      await deleteResource(topicId, resourceId);
      setResources((prev) => prev.filter((r) => r.id !== resourceId));
    } catch {
      alert('Failed to delete resource');
    } finally {
      setDeletingId(null);
    }
  };

  const handleReembed = async (resourceId, e) => {
    e.stopPropagation();
    setReembeddingId(resourceId);
    try {
      await reembedResource(topicId, resourceId);
      await loadResources();
    } catch {
      alert('Failed to re-embed resource');
    } finally {
      setReembeddingId(null);
    }
  };

  if (loading) {
    return (
      <div className="resources-loading">
        {[1, 2].map((i) => <div key={i} className="resource-skeleton" />)}
      </div>
    );
  }

  if (resources.length === 0) {
    return (
      <div className="resources-empty">
        <p>No resources yet. Upload files or add links.</p>
      </div>
    );
  }

  return (
    <div className="resources-list">
      {resources.map((r) => (
        <div key={r.id} className="resource-card">
          <div className="resource-icon">
            {FILE_ICONS[r.fileType] || '📄'}
          </div>
          <div className="resource-info">
            <span className="resource-name">{r.originalName || r.filename}</span>
            <div className="resource-meta">
              <span className={`badge badge-${(r.embeddingStatus || 'pending').toLowerCase()}`}>
                {r.embeddingStatus || 'PENDING'}
              </span>
              {r.chunkCount > 0 && (
                <span className="resource-chunks">{r.chunkCount} chunks</span>
              )}
              {r.fileSize && (
                <span className="resource-size">{formatBytes(r.fileSize)}</span>
              )}
            </div>
          </div>
          <div className="resource-actions">
            {(r.embeddingStatus === 'FAILED' || r.embeddingStatus === 'PENDING') && (
              <button
                className="btn-ghost btn-sm"
                onClick={(e) => handleReembed(r.id, e)}
                disabled={reembeddingId === r.id}
                title="Re-embed"
              >
                {reembeddingId === r.id ? <span className="spinner spinner-sm" /> : '🔄'}
              </button>
            )}
            <button
              className="btn-ghost btn-sm"
              onClick={(e) => handleDelete(r.id, e)}
              disabled={deletingId === r.id}
              title="Delete"
            >
              {deletingId === r.id ? <span className="spinner spinner-sm" /> : '🗑️'}
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

function formatBytes(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}
