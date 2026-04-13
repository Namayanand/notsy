import { useState, useEffect, useRef } from 'react';
import { parseJsonField } from '../api/client';
import {
  getConversation, chat, branchConversation, mergeBranch, getBranches,
} from '../api/conversations';
import './ChatInterface.css';

const SOURCE_ICONS = {
  pdf: '📄',
  image: '🖼️',
  video: '🎬',
  link: '🔗',
  text: '📝',
};

const MODES = {
  MASTER_THIS: { icon: '📖', label: 'Master This', color: '#7c5bf5' },
  GO_CRAZY: { icon: '🧠', label: 'Go Crazy', color: '#f472b6' },
  DEV_MODE: { icon: '💻', label: 'Dev Mode', color: '#60a5fa' },
  LAST_MINUTE: { icon: '⏰', label: 'Last Minute', color: '#fbbf24' },
  TEACH_ME_TECH: { icon: '🎓', label: 'Teach Me Tech', color: '#4ade80' },
};

// Simple markdown-ish renderer for bold, italic, code, code blocks, lists
function renderMarkdown(text) {
  if (!text) return null;
  const lines = text.split('\n');
  const elements = [];
  let inCodeBlock = false;
  let codeBuffer = [];

  lines.forEach((line, i) => {
    // Code block
    if (line.trim().startsWith('```')) {
      if (inCodeBlock) {
        elements.push(
          <pre key={`code-${i}`} className="chat-code-block">
            <code>{codeBuffer.join('\n')}</code>
          </pre>
        );
        codeBuffer = [];
        inCodeBlock = false;
      } else {
        inCodeBlock = true;
      }
      return;
    }

    if (inCodeBlock) {
      codeBuffer.push(line);
      return;
    }

    // Inline code
    const inlineCode = (t) => {
      const parts = t.split(/(`[^`]+`)/g);
      return parts.map((p, idx) => {
        if (p.startsWith('`') && p.endsWith('`')) {
          return <code key={idx} className="chat-inline-code">{p.slice(1, -1)}</code>;
        }
        // Bold
        const boldParts = p.split(/(\*\*[^*]+\*\*)/g);
        return boldParts.map((bp, bi) => {
          if (bp.startsWith('**') && bp.endsWith('**')) {
            return <strong key={bi}>{bp.slice(2, -2)}</strong>;
          }
          // Italic
          const italicParts = bp.split(/(\*[^*]+\*)/g);
          return italicParts.map((ip, ci) => {
            if (ip.startsWith('*') && ip.endsWith('*') && !ip.startsWith('**')) {
              return <em key={ci}>{ip.slice(1, -1)}</em>;
            }
            return ip;
          });
        });
      });
    };

    // List items
    if (line.match(/^(\d+\.|-|\*)\s/)) {
      const listMatch = line.match(/^(\d+\.|-|\*)\s(.*)/);
      if (listMatch) {
        const [, marker, content] = listMatch;
        const isOrdered = marker.match(/\d+\./);
        elements.push(
          <div key={i} className="chat-list-item">
            <span className="chat-list-marker">{isOrdered ? marker : '•'}</span>
            <span>{inlineCode(content)}</span>
          </div>
        );
        return;
      }
    }

    // Headings
    if (line.startsWith('### ')) {
      elements.push(<h4 key={i} className="chat-heading">{inlineCode(line.slice(4))}</h4>);
      return;
    }
    if (line.startsWith('## ')) {
      elements.push(<h3 key={i} className="chat-heading">{inlineCode(line.slice(3))}</h3>);
      return;
    }
    if (line.startsWith('# ')) {
      elements.push(<h2 key={i} className="chat-heading">{inlineCode(line.slice(2))}</h2>);
      return;
    }

    // Regular paragraph
    if (line.trim()) {
      elements.push(<p key={i} className="chat-paragraph">{inlineCode(line)}</p>);
    } else {
      elements.push(<div key={i} className="chat-spacer" />);
    }
  });

  return elements;
}

export default function ChatInterface({ topic, conversationId, onBack }) {
  const [conversation, setConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [branches, setBranches] = useState([]);
  const [showBranches, setShowBranches] = useState(false);
  const [currentMode, setCurrentMode] = useState('MASTER_THIS');
  const [copiedId, setCopiedId] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    loadConversation();
    loadBranches();
  }, [conversationId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadConversation = async () => {
    setLoading(true);
    try {
      const res = await getConversation(topic.id, conversationId);
      const conv = res.data.data;
      setConversation(conv);
      setCurrentMode(conv.learningMode || 'MASTER_THIS');
      setMessages(conv.messages || []);
    } catch (err) {
      console.error('Failed to load conversation', err);
    } finally {
      setLoading(false);
    }
  };

  const loadBranches = async () => {
    try {
      const res = await getBranches(topic.id, conversationId);
      setBranches(res.data.data || []);
    } catch {}
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || sending) return;

    const userMsg = { role: 'user', content: input, id: Date.now() };
    setMessages((prev) => [...prev, userMsg]);
    const sentInput = input;
    setInput('');
    setSending(true);

    try {
      const res = await chat(topic.id, conversationId, sentInput);
      const aiMsg = res.data.data;
      if (aiMsg) {
        setMessages((prev) => [...prev, {
          id: aiMsg.id || Date.now() + 1,
          role: aiMsg.role || 'assistant',
          content: aiMsg.content,
          sources: parseJsonField(aiMsg.sources),
          tokensUsed: aiMsg.tokensUsed,
          createdAt: aiMsg.createdAt,
        }]);
      }
    } catch {
      setMessages((prev) => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        content: "Sorry, I couldn't process your message. Please try again.",
      }]);
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  };

  const handleBranch = async () => {
    const context = prompt('What is this branch about? (optional)');
    try {
      await branchConversation(topic.id, conversationId, {
        branchContext: context || '',
        learningMode: currentMode,
      });
      alert(`Branch created! Go to the conversation list to access it.`);
      loadBranches();
    } catch {
      alert('Failed to create branch');
    }
  };

  const handleMerge = async (branchConvId, action) => {
    if (!confirm(`Are you sure you want to ${action} this branch?`)) return;
    try {
      await mergeBranch(topic.id, conversationId, { branchConversationId: branchConvId, action });
      alert(`Branch ${action}ed successfully!`);
      loadConversation();
      loadBranches();
    } catch {
      alert('Failed to merge branch');
    }
  };

  const handleCopy = (text, msgId) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedId(msgId);
      setTimeout(() => setCopiedId(null), 2000);
    });
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend(e);
    }
  };

  const renderSources = (sources) => {
    if (!sources || (Array.isArray(sources) && sources.length === 0)) return null;
    const sourceList = Array.isArray(sources) ? sources : [sources];
    return (
      <div className="sources-panel">
        <div className="sources-header">
          <span>📚 Sources ({sourceList.length})</span>
          <span className="sources-hint">Grounded in your materials</span>
        </div>
        {sourceList.map((s, i) => (
          <div key={i} className="source-item">
            <div className="source-meta">
              <span className="source-file">{SOURCE_ICONS.pdf} {s.filename || 'Unknown'}</span>
              {s.score != null && (
                <span className="source-score">{Math.round(s.score * 100)}% match</span>
              )}
            </div>
            <p className="source-chunk">{s.chunk || s}</p>
          </div>
        ))}
      </div>
    );
  };

  const modeInfo = MODES[currentMode] || MODES.MASTER_THIS;

  return (
    <div className="chat-interface">
      {/* Chat Header */}
      <div className="chat-header">
        <button className="btn-ghost back-btn" onClick={onBack}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Back
        </button>
        <div className="chat-header-info">
          <h3>{conversation?.title || 'Chat'}</h3>
          <div className="chat-mode-badge" style={{ color: modeInfo.color }}>
            <span className="mode-badge-dot" style={{ background: modeInfo.color }} />
            {modeInfo.icon} {modeInfo.label}
          </div>
        </div>
        <div className="chat-header-actions">
          <button className="btn-ghost branch-toggle-btn" onClick={() => setShowBranches(!showBranches)} title="View branches">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M6 3v12M18 3v12M6 9a3 3 0 100-6 3 3 0 000 6zM18 9a3 3 0 100-6 3 3 0 000 6zM6 15a3 3 0 100 6 3 3 0 000-6zM18 15a3 3 0 100 6 3 3 0 000-6z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            {branches.length > 0 && <span className="branch-count">{branches.length}</span>}
          </button>
          <button className="btn-secondary btn-sm branch-btn" onClick={handleBranch}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path d="M12 3v6m0 0v6m0-6h6m-6 0H6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Branch
          </button>
        </div>
      </div>

      {/* Branches Panel */}
      {showBranches && (
        <div className="branches-panel animate-slide-in-up">
          <div className="branches-header">
            <span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style={{ marginRight: 6, verticalAlign: 'middle' }}>
                <path d="M6 3v12M18 3v12M6 9a3 3 0 100-6 3 3 0 000 6zM18 9a3 3 0 100-6 3 3 0 000 6zM6 15a3 3 0 100 6 3 3 0 000-6zM18 15a3 3 0 100 6 3 3 0 000-6z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
              Branches ({branches.length})
            </span>
            <button className="btn-ghost" onClick={() => setShowBranches(false)}>
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </button>
          </div>
          {branches.length === 0 ? (
            <p className="branches-empty">No branches yet — explore tangents without losing context</p>
          ) : (
            <div className="branches-list">
              {branches.map((b, i) => (
                <div key={b.id} className="branch-item animate-fade-in" style={{ animationDelay: `${i * 50}ms` }}>
                  <div className="branch-info">
                    <span className="branch-title">{b.title}</span>
                    {b.branchContext && <span className="branch-context">{b.branchContext}</span>}
                  </div>
                  <div className="branch-actions">
                    <button className="btn-ghost btn-sm merge-btn" onClick={() => handleMerge(b.id, 'merge')} title="Merge into main">
                      <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
                        <path d="M8 2v9M4 8l4 3 4-3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                      Merge
                    </button>
                    <button className="btn-ghost btn-sm discard-btn" onClick={() => handleMerge(b.id, 'discard')} title="Discard">
                      <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
                        <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                      </svg>
                      Discard
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Messages */}
      <div className="chat-messages">
        {loading ? (
          <div className="chat-loading">
            <div className="chat-loading-visual">
              <div className="loading-orbs">
                <div className="loading-orb" />
                <div className="loading-orb" />
                <div className="loading-orb" />
              </div>
            </div>
            <p className="loading-text">Loading conversation...</p>
          </div>
        ) : messages.length === 0 ? (
          <div className="chat-empty animate-fade-in">
            <div className="chat-empty-visual">
              <div className="ai-orbit">
                <div className="ai-orbit-ring" />
                <div className="ai-orbit-ring ai-orbit-ring-2" />
                <div className="ai-core">
                  <svg width="32" height="32" viewBox="0 0 40 40" fill="none">
                    <path d="M20 8L26 14L20 20L14 14L20 8Z" fill="var(--accent-light)" opacity="0.8" />
                    <path d="M20 20L26 26L20 32L14 26L20 20Z" fill="var(--accent)" opacity="0.6" />
                    <circle cx="20" cy="20" r="4" fill="white" />
                  </svg>
                </div>
              </div>
            </div>
            <h3>Start the conversation</h3>
            <p>Ask anything about <strong>{topic.title}</strong> — I'm grounded in your uploaded resources</p>
            <div className="chat-suggestions">
              {[
                `Explain ${topic.title} in simple terms`,
                `What are the key concepts in ${topic.title}?`,
                `How does ${topic.title} connect to other topics?`,
              ].map((s, i) => (
                <button
                  key={i}
                  className="suggestion-chip"
                  onClick={() => setInput(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg, i) => (
              <div
                key={msg.id || i}
                className={`message message-${msg.role} animate-fade-in`}
                style={{ animationDelay: '0ms' }}
              >
                <div className="message-avatar">
                  {msg.role === 'user' ? (
                    <div className="user-avatar-icon">👤</div>
                  ) : (
                    <div className="ai-avatar-icon">
                      <svg width="20" height="20" viewBox="0 0 40 40" fill="none">
                        <path d="M20 8L26 14L20 20L14 14L20 8Z" fill="white" opacity="0.9" />
                        <path d="M20 20L26 26L20 32L14 26L20 20Z" fill="white" opacity="0.6" />
                        <circle cx="20" cy="20" r="4" fill="white" />
                      </svg>
                    </div>
                  )}
                </div>
                <div className="message-body">
                  <div className={`message-content ${msg.role === 'user' ? 'user-bubble' : 'ai-bubble'}`}>
                    {msg.role === 'assistant'
                      ? renderMarkdown(msg.content)
                      : msg.content
                    }
                  </div>
                  <div className="message-footer">
                    {msg.sources && renderSources(msg.sources)}
                    {msg.tokensUsed > 0 && (
                      <span className="font-mono text-xs text-muted tokens-badge">
                        ⚡ {msg.tokensUsed} tokens
                      </span>
                    )}
                    {msg.role === 'assistant' && (
                      <button
                        className="copy-btn"
                        onClick={() => handleCopy(msg.content, msg.id || i)}
                        title="Copy response"
                      >
                        {copiedId === (msg.id || i) ? (
                          <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
                            <path d="M3 8l3 3 7-7" stroke="var(--success)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        ) : (
                          <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
                            <rect x="5" y="5" width="8" height="8" rx="2" stroke="currentColor" strokeWidth="1.5" />
                            <path d="M3 11V4a1 1 0 011-1h7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                          </svg>
                        )}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </>
        )}
        {sending && (
          <div className="message message-assistant animate-fade-in">
            <div className="message-avatar">
              <div className="ai-avatar-icon">
                <svg width="20" height="20" viewBox="0 0 40 40" fill="none">
                  <path d="M20 8L26 14L20 20L14 14L20 8Z" fill="white" opacity="0.9" />
                  <path d="M20 20L26 26L20 32L14 26L20 20Z" fill="white" opacity="0.6" />
                  <circle cx="20" cy="20" r="4" fill="white" />
                </svg>
              </div>
            </div>
            <div className="message-body">
              <div className="message-content ai-bubble">
                <div className="typing-container">
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                </div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form className="chat-input-bar" onSubmit={handleSend}>
        <div className="chat-input-wrapper">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Ask about ${topic.title}...`}
            disabled={sending}
            className="chat-input-field"
          />
          <div className="input-actions">
            <span className="input-hint">
              ⏎ send · ⇧+⏎ new line
            </span>
          </div>
        </div>
        <button
          type="submit"
          className={`send-btn ${input.trim() ? 'send-btn-active' : ''}`}
          disabled={!input.trim() || sending}
        >
          {sending ? (
            <div className="spinner spinner-sm" />
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M12 3l10 9-10 9V12H3V9h9V3z" fill="currentColor" />
            </svg>
          )}
        </button>
      </form>
    </div>
  );
}
