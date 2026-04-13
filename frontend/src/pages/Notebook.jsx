import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getNotebook } from '../api/notebooks';
import { getTopics, createTopic, deleteTopic } from '../api/topics';
import { createConversation } from '../api/conversations';
import ResourceList from '../components/ResourceList';
import FileUpload from '../components/FileUpload';
import ChatInterface from '../components/ChatInterface';
import './Notebook.css';

const LEARNING_MODES = [
  { value: 'MASTER_THIS', label: '📖 Master This', desc: 'Comprehensive guide' },
  { value: 'GO_CRAZY', label: '🧠 Go Crazy', desc: 'Creative exploration' },
  { value: 'DEV_MODE', label: '💻 Dev Mode', desc: 'Technical deep-dive' },
  { value: 'LAST_MINUTE', label: '⏰ Last Minute', desc: 'Exam prep' },
  { value: 'TEACH_ME_TECH', label: '🎓 Teach Me Tech', desc: 'Beginner-friendly' },
];

export default function Notebook() {
  const { id: nbId, topicId: activeTopicId, convId: activeConvId } = useParams();
  const navigate = useNavigate();

  const [notebook, setNotebook] = useState(null);
  const [topics, setTopics] = useState([]);
  const [activeTopic, setActiveTopic] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showTopicModal, setShowTopicModal] = useState(false);
  const [showCreateConv, setShowCreateConv] = useState(false);
  const [newTopicTitle, setNewTopicTitle] = useState('');
  const [newConvTitle, setNewConvTitle] = useState('');
  const [selectedMode, setSelectedMode] = useState('MASTER_THIS');
  const [showUpload, setShowUpload] = useState(false);

  useEffect(() => {
    loadData();
  }, [nbId]);

  useEffect(() => {
    if (activeTopicId) {
      const topic = findTopic(topics, Number(activeTopicId));
      setActiveTopic(topic);
    } else {
      setActiveTopic(null);
    }
  }, [activeTopicId, topics]);

  const findTopic = (list, tid) => {
    for (const t of list) {
      if (t.id === tid) return t;
      if (t.subtopics?.length) {
        const found = findTopic(t.subtopics, tid);
        if (found) return found;
      }
    }
    return null;
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const [nbRes, topicsRes] = await Promise.all([
        getNotebook(nbId),
        getTopics(nbId),
      ]);
      setNotebook(nbRes.data.data);
      setTopics(topicsRes.data.data || []);
    } catch (err) {
      console.error('Failed to load notebook', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTopic = async (e) => {
    e.preventDefault();
    if (!newTopicTitle.trim()) return;
    try {
      const res = await createTopic(nbId, { title: newTopicTitle });
      setTopics((prev) => [...prev, res.data.data]);
      setShowTopicModal(false);
      setNewTopicTitle('');
      navigate(`/notebooks/${nbId}/topics/${res.data.data.id}`);
    } catch {
      alert('Failed to create topic');
    }
  };

  const handleDeleteTopic = async (topicId, e) => {
    e.stopPropagation();
    if (!confirm('Delete this topic and all its data?')) return;
    try {
      await deleteTopic(nbId, topicId);
      setTopics((prev) => prev.filter((t) => t.id !== topicId));
      if (activeTopicId == topicId) {
        setActiveTopic(null);
        navigate(`/notebooks/${nbId}`);
      }
    } catch {
      alert('Failed to delete topic');
    }
  };

  const handleTopicClick = (topic) => {
    setActiveTopic(topic);
    navigate(`/notebooks/${nbId}/topics/${topic.id}`);
  };

  const renderTopicTree = (topics, depth = 0) => (
    topics.map((topic) => (
      <div key={topic.id} className="topic-tree-item">
        <button
          className={`topic-tree-btn ${activeTopicId == topic.id ? 'active' : ''}`}
          style={{ paddingLeft: `${12 + depth * 16}px` }}
          onClick={() => handleTopicClick(topic)}
        >
          <span className="topic-tree-icon">{topic.subtopics?.length ? '📁' : '📄'}</span>
          <span className="topic-tree-title">{topic.title}</span>
          {topic.embeddingStatus && topic.embeddingStatus !== 'DONE' && (
            <span className={`badge badge-${topic.embeddingStatus.toLowerCase()}`}>
              {topic.embeddingStatus}
            </span>
          )}
        </button>
        <button className="topic-delete btn-ghost" onClick={(e) => handleDeleteTopic(topic.id, e)} title="Delete topic">
          🗑️
        </button>
        {topic.subtopics?.length > 0 && renderTopicTree(topic.subtopics, depth + 1)}
      </div>
    ))
  );

  if (loading) {
    return (
      <div className="notebook-loading">
        <div className="spinner spinner-lg" />
      </div>
    );
  }

  return (
    <div className="notebook-layout">
      {/* Topic Tree Sidebar */}
      <aside className="notebook-sidebar">
        <div className="notebook-sidebar-header">
          <h2 className="notebook-name">{notebook?.title}</h2>
          <button className="btn-primary btn-sm" onClick={() => setShowTopicModal(true)}>
            + Topic
          </button>
        </div>

        <div className="topic-tree">
          {topics.length === 0 ? (
            <div className="topic-tree-empty">
              <p>No topics yet</p>
              <button className="btn-secondary btn-sm" onClick={() => setShowTopicModal(true)}>
                Create First Topic
              </button>
            </div>
          ) : (
            renderTopicTree(topics)
          )}
        </div>
      </aside>

      {/* Main Panel */}
      <div className="notebook-main">
        {!activeTopic ? (
          <div className="notebook-empty animate-fade-in">
            <div className="notebook-empty-visual">
              <div className="empty-nebula">
                <div className="nebula-orb" />
                <div className="nebula-orb" />
                <div className="nebula-orb" />
              </div>
              <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
                <circle cx="40" cy="40" r="30" stroke="var(--accent)" strokeWidth="2" strokeDasharray="6 4" opacity="0.5" />
                <circle cx="40" cy="40" r="18" stroke="var(--accent)" strokeWidth="2" opacity="0.7" />
                <circle cx="40" cy="40" r="6" fill="var(--accent)" opacity="0.9" />
              </svg>
            </div>
            <h3>Select a topic to begin</h3>
            <p>Choose a topic from the sidebar, or create a new one to start uploading resources and chatting with AI.</p>
          </div>
        ) : activeConvId ? (
          <ChatInterface
            topic={activeTopic}
            conversationId={Number(activeConvId)}
            onBack={() => navigate(`/notebooks/${nbId}/topics/${activeTopicId}`)}
          />
        ) : (
          <div className="topic-workspace animate-fade-in">
            <div className="topic-header">
              <div>
                <h2>{activeTopic.title}</h2>
                {activeTopic.description && (
                  <p className="topic-desc">{activeTopic.description}</p>
                )}
              </div>
              <div className="topic-header-actions">
                <button className="btn-primary btn-sm" onClick={() => setShowCreateConv(true)}>
                  💬 New Chat
                </button>
              </div>
            </div>

            {/* Mode selector */}
            <div className="mode-selector">
              <span className="mode-label">AI Mode:</span>
              <div className="mode-options">
                {LEARNING_MODES.map((m) => (
                  <button
                    key={m.value}
                    className={`mode-btn ${selectedMode === m.value ? 'active' : ''}`}
                    onClick={() => setSelectedMode(m.value)}
                    title={m.desc}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="topic-content-grid">
              {/* Resources */}
              <div className="topic-section">
                <div className="section-header">
                  <h3 className="section-title">📚 Resources</h3>
                  <button className="btn-secondary btn-sm" onClick={() => setShowUpload(true)}>
                    + Add
                  </button>
                </div>
                <ResourceList topicId={activeTopic.id} />
              </div>

              {/* Conversations */}
              <div className="topic-section">
                <div className="section-header">
                  <h3 className="section-title">💬 Conversations</h3>
                </div>
                <div className="conversations-list">
                  {(!activeTopic.conversations || activeTopic.conversations.length === 0) ? (
                    <div className="empty-section">
                      <p>No conversations yet</p>
                      <button className="btn-secondary btn-sm" onClick={() => setShowCreateConv(true)}>
                        Start First Chat
                      </button>
                    </div>
                  ) : (
                    activeTopic.conversations.map((conv) => (
                      <button
                        key={conv.id}
                        className="conversation-item"
                        onClick={() => navigate(`/notebooks/${nbId}/topics/${activeTopic.id}/conversations/${conv.id}`)}
                      >
                        <div className="conv-info">
                          <span className="conv-title">{conv.title}</span>
                          <span className="conv-meta">
                            {conv.learningMode?.replace('_', ' ')} • {conv.isBranch ? '🌿 Branch' : 'Main'}
                          </span>
                        </div>
                        <span className="conv-arrow">›</span>
                      </button>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Create Topic Modal */}
      {showTopicModal && (
        <div className="modal-overlay" onClick={() => setShowTopicModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2 className="modal-title">New Topic</h2>
            <form onSubmit={handleCreateTopic} className="modal-form">
              <div className="form-group">
                <label>Topic Title</label>
                <input
                  type="text"
                  value={newTopicTitle}
                  onChange={(e) => setNewTopicTitle(e.target.value)}
                  placeholder="e.g. Thermodynamics"
                  required
                  autoFocus
                />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowTopicModal(false)}>Cancel</button>
                <button type="submit" className="btn-primary">Create</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Create Conversation Modal */}
      {showCreateConv && (
        <div className="modal-overlay" onClick={() => setShowCreateConv(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2 className="modal-title">New Conversation</h2>
            <form onSubmit={async (e) => {
              e.preventDefault();
              if (!newConvTitle.trim()) return;
              const res = await createConversation(activeTopic.id, {
                title: newConvTitle,
                learningMode: selectedMode,
              });
              setShowCreateConv(false);
              setNewConvTitle('');
              navigate(`/notebooks/${nbId}/topics/${activeTopic.id}/conversations/${res.data.data.id}`);
            }} className="modal-form">
              <div className="form-group">
                <label>Conversation Title</label>
                <input
                  type="text"
                  value={newConvTitle}
                  onChange={(e) => setNewConvTitle(e.target.value)}
                  placeholder="e.g. Understanding Entropy"
                  required
                  autoFocus
                />
              </div>
              <div className="form-group">
                <label>Learning Mode</label>
                <div className="mode-options-modal">
                  {LEARNING_MODES.map((m) => (
                    <button
                      key={m.value}
                      type="button"
                      className={`mode-btn ${selectedMode === m.value ? 'active' : ''}`}
                      onClick={() => setSelectedMode(m.value)}
                    >
                      {m.label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowCreateConv(false)}>Cancel</button>
                <button type="submit" className="btn-primary">Start Chat</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* File Upload Modal */}
      {showUpload && (
        <FileUpload
          topicId={activeTopic.id}
          onClose={() => setShowUpload(false)}
          onUploaded={() => {
            setShowUpload(false);
            loadData();
          }}
        />
      )}
    </div>
  );
}
