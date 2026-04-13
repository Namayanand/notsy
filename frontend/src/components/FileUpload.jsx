import { useState } from 'react';
import { uploadFile, addLink, reembedResource } from '../api/resources';
import './FileUpload.css';

export default function FileUpload({ topicId, onClose, onUploaded }) {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [mode, setMode] = useState('file'); // 'file' | 'link'
  const [linkUrl, setLinkUrl] = useState('');
  const [linkTitle, setLinkTitle] = useState('');
  const [error, setError] = useState('');

  const handleDrop = async (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) await uploadResource(file);
  };

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (file) await uploadResource(file);
  };

  const uploadResource = async (file) => {
    setUploading(true);
    setError('');
    try {
      const formData = new FormData();
      formData.append('file', file);
      await uploadFile(topicId, formData);
      onUploaded();
    } catch (err) {
      setError('Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleLinkSubmit = async (e) => {
    e.preventDefault();
    if (!linkUrl.trim()) return;
    setUploading(true);
    setError('');
    try {
      await addLink(topicId, {
        sourceUrl: linkUrl,
        title: linkTitle || linkUrl,
      });
      onUploaded();
    } catch {
      setError('Failed to add link. Check the URL.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content upload-modal" onClick={(e) => e.stopPropagation()}>
        <div className="upload-header">
          <h2>Add Resource</h2>
          <button className="btn-ghost close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="upload-tabs">
          <button
            className={`upload-tab ${mode === 'file' ? 'active' : ''}`}
            onClick={() => setMode('file')}
          >
            📁 Upload File
          </button>
          <button
            className={`upload-tab ${mode === 'link' ? 'active' : ''}`}
            onClick={() => setMode('link')}
          >
            🔗 Add Link
          </button>
        </div>

        {error && <div className="upload-error">{error}</div>}

        {mode === 'file' ? (
          <div
            className={`drop-zone ${dragOver ? 'drag-over' : ''} ${uploading ? 'uploading' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
          >
            {uploading ? (
              <div className="drop-zone-uploading">
                <div className="spinner spinner-lg" />
                <p>Processing file...</p>
              </div>
            ) : (
              <>
                <div className="drop-zone-icon">📤</div>
                <h4>Drag & drop your file here</h4>
                <p>or</p>
                <label className="btn-secondary file-label">
                  Browse Files
                  <input type="file" className="sr-only" onChange={handleFileChange} accept=".pdf,.txt,.png,.jpg,.jpeg" />
                </label>
                <p className="drop-zone-hint">Supports PDF, TXT, PNG, JPG</p>
              </>
            )}
          </div>
        ) : (
          <form className="link-form" onSubmit={handleLinkSubmit}>
            <div className="form-group">
              <label>URL</label>
              <input
                type="url"
                value={linkUrl}
                onChange={(e) => setLinkUrl(e.target.value)}
                placeholder="https://..."
                required
                autoFocus
              />
            </div>
            <div className="form-group">
              <label>Title (optional)</label>
              <input
                type="text"
                value={linkTitle}
                onChange={(e) => setLinkTitle(e.target.value)}
                placeholder="Article title"
              />
            </div>
            <button type="submit" className="btn-primary w-full" disabled={uploading}>
              {uploading ? <span className="spinner spinner-sm" /> : 'Add Link'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
