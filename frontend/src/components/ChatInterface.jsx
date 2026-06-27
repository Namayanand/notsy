import { useState, useEffect, useRef } from 'react';
import { parseJsonField } from '../api/client';
import {
  getConversation, chat, branchConversation, branchFromMessage, mergeBranch, getBranches,
  getBranchesFromMessage, getBreadcrumb, navigateToParent,
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

// Render message content with highlighted branch texts
function renderMessageContentWithBranches(content, branches, onBranchClick) {
  if (!content) return null;
  if (!branches || branches.length === 0) {
    return renderMarkdown(content);
  }

  // Sort branches by selectionStart descending to process from end to beginning
  const sortedBranches = [...branches].sort((a, b) => b.selectionStart - a.selectionStart);

  const parts = [];
  let lastEnd = content.length;

  // Build parts array from end to start
  for (const branch of sortedBranches) {
    const { selectionStart, selectionEnd } = branch;
    if (selectionStart != null && selectionEnd != null && selectionStart < selectionEnd && selectionEnd <= content.length) {
      // Add the part after this branch
      if (lastEnd > selectionEnd) {
        parts.unshift({ type: 'text', content: content.substring(selectionEnd, lastEnd) });
      }
      // Add the branched part
      parts.unshift({
        type: 'branch',
        content: content.substring(selectionStart, selectionEnd),
        branch
      });
      lastEnd = selectionStart;
    }
  }

  // Add the remaining text at the beginning
  if (lastEnd > 0) {
    parts.unshift({ type: 'text', content: content.substring(0, lastEnd) });
  }

  // Render the parts
  const elements = [];
  parts.forEach((part, idx) => {
    if (part.type === 'branch') {
      const anchorText = part.branch.branchContext
        ? part.branch.branchContext.slice(0, 20)
        : (part.branch.title?.slice(0, 20) || 'branch');
      elements.push(
        <span
          key={`branch-${idx}`}
          className="branched-text-wrapper"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onBranchClick(part.branch);
          }}
        >
          <span
            className="branched-text"
            title={`Click to go to branch: ${part.branch.title}`}
          >
            {part.content}
          </span>
          <span className="branch-badge" title={`Click to go to branch: ${part.branch.title}`}>
            ⎇ {anchorText}
          </span>
        </span>
      );
    } else {
      // For text parts, render markdown
      const rendered = renderMarkdown(part.content);
      if (rendered) {
        rendered.forEach((el, i) => {
          elements.push(<span key={`text-${idx}-${i}`}>{el}</span>);
        });
      }
    }
  });

  return elements.length > 0 ? elements : renderMarkdown(content);
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
  const [useWebSearch, setUseWebSearch] = useState(false);
  const [explainDepth, setExplainDepth] = useState(null);
  const [showSettings, setShowSettings] = useState(false);

  // Message-level branching state
  const [selectedMessage, setSelectedMessage] = useState(null);
  const [selectionRange, setSelectionRange] = useState(null);
  const [breadcrumb, setBreadcrumb] = useState([]);
  const [messageBranches, setMessageBranches] = useState([]);

  // Parent reference for navigation
  const [parentConversationId, setParentConversationId] = useState(null);
  const [parentTitle, setParentTitle] = useState(null);

  // Selection popover state
  const [selectionPopover, setSelectionPopover] = useState(null);

  // Tab state for branch navigation
  const [activeTab, setActiveTab] = useState('main');
  const [openTabs, setOpenTabs] = useState([]);

  // Depth warning state
  const [showDepthWarning, setShowDepthWarning] = useState(false);

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

      // Load breadcrumb if this is a branch
      if (conv.branchOfId) {
        try {
          const breadcrumbRes = await getBreadcrumb(conv.branchOfId);
          setBreadcrumb(breadcrumbRes.data.data || []);
        } catch {}
      }
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

    // Build history for streaming
    const history = messages.map(m => ({ role: m.role, content: m.content }));

    try {
      // Try streaming endpoint first
      const streamUrl = `${import.meta.env.VITE_API_URL || ''}/api/chat/${conversationId}/stream`;

      const response = await fetch(streamUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: sentInput,
          history: history,
          learningMode: currentMode,
          useWebSearch: useWebSearch,
          explainDepth: explainDepth,
        }),
      });

      if (response.ok && response.body) {
        // Streaming response
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullContent = '';
        let sources = [];
        let tempMessageId = Date.now() + 1;

        // Add placeholder message
        setMessages(prev => [...prev, {
          id: tempMessageId,
          role: 'assistant',
          content: '',
          sources: [],
        }]);

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                if (data.type === 'token' && data.data?.token) {
                  fullContent += data.data.token;
                  setMessages(prev => prev.map(m =>
                    m.id === tempMessageId ? { ...m, content: fullContent } : m
                  ));
                } else if (data.type === 'sources' && data.data?.sources) {
                  sources = data.data.sources;
                } else if (data.type === 'done') {
                  setMessages(prev => prev.map(m =>
                    m.id === tempMessageId ? {
                      ...m,
                      sources: sources,
                      tokensUsed: data.data?.tokensUsed || 0,
                    } : m
                  ));
                }
              } catch {}
            }
          }
        }
      } else {
        // Fallback to non-streaming
        const res = await chat(topic.id, conversationId, sentInput, currentMode);
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
      }
    } catch (err) {
      console.error('Chat error:', err);
      setMessages((prev) => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        content: "Sorry, I couldn't process your message. Please try again.",
      }]);
    } finally {
      setSending(false);
      inputRef.current?.focus();
      // Mark that this tab has sent a message (for empty branch auto-discard)
      if (activeTab !== 'main') {
        setOpenTabs(prev => prev.map(tab =>
          tab.id === activeTab ? { ...tab, hasSentMessages: true } : tab
        ));
      }
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

  // Handle text selection for message branching - immediately create branch
  const handleTextSelect = async (msg, selection) => {
    const anchorText = selection?.text || msg.content.substring(0, 50);

    try {
      // Create branch immediately with anchor text
      const res = await branchFromMessage(topic.id, conversationId, {
        parentMessageId: msg.id,
        selectionStart: selection?.start,
        selectionEnd: selection?.end,
        anchorText: anchorText,
        learningMode: currentMode,
      });

      const branchData = res.data.data;

      // Store parent info for navigation
      setParentConversationId(conversationId);
      setParentTitle(branchData.parentConversation?.title || conversation?.title);

      // Check if this is a deep branch (depth >= 3) and show warning
      if (branchData.branchConversation?.branchDepth >= 3) {
        setShowDepthWarning(true);
        setTimeout(() => setShowDepthWarning(false), 5000);
      }

      // Navigate to the branch conversation
      setConversation(branchData.branchConversation);
      setMessages(branchData.branchConversation.messages || []);
      setBreadcrumb(branchData.ancestry || []);

      // Clear selection popover
      setSelectionPopover(null);
      setSelectedMessage(null);
      setSelectionRange(null);

      // Auto-send the first message with the anchor text
      const branchConversationId = branchData.branchConversation.id;
      const systemPrompt = branchData.systemPrompt;
      const parentContext = branchData.parentContextMessages;

      // Simulate user sending the anchor text as first message
      const firstMessage = { role: 'user', content: anchorText, id: Date.now() };
      setMessages([firstMessage]);
      setInput('');

      // Send the message automatically
      await sendAutoMessage(branchConversationId, anchorText, systemPrompt, parentContext);

    } catch (err) {
      console.error('Failed to create branch:', err);
      alert(err.response?.data?.message || 'Failed to create branch');
    }
  };

  // Send message automatically when branching
  const sendAutoMessage = async (convId, message, systemPrompt, parentContext) => {
    setSending(true);

    try {
      const streamUrl = `${import.meta.env.VITE_API_URL || ''}/api/chat/${convId}/stream`;

      const history = [];

      const response = await fetch(streamUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: message,
          history: history,
          learningMode: currentMode,
          useWebSearch: useWebSearch,
          explainDepth: explainDepth,
          systemPrompt: systemPrompt,
        }),
      });

      if (response.ok && response.body) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullContent = '';
        let sources = [];
        let tempMessageId = Date.now() + 1;

        setMessages(prev => [...prev, {
          id: tempMessageId,
          role: 'assistant',
          content: '',
          sources: [],
        }]);

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                if (data.type === 'token' && data.data?.token) {
                  fullContent += data.data.token;
                  setMessages(prev => prev.map(m =>
                    m.id === tempMessageId ? { ...m, content: fullContent } : m
                  ));
                } else if (data.type === 'sources' && data.data?.sources) {
                  sources = data.data.sources;
                } else if (data.type === 'done') {
                  setMessages(prev => prev.map(m =>
                    m.id === tempMessageId ? {
                      ...m,
                      sources: sources,
                      tokensUsed: data.data?.tokensUsed || 0,
                    } : m
                  ));
                }
              } catch {}
            }
          }
        }
      } else {
        // Fallback to non-streaming
        const res = await chat(topic.id, convId, message, currentMode);
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
      }
    } catch (err) {
      console.error('Auto-send error:', err);
      setMessages((prev) => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        content: "Sorry, I couldn't process your message. Please try again.",
      }]);
    } finally {
      setSending(false);
    }
  };

  // Navigate back to parent conversation
  const handleNavigateToParent = async () => {
    if (!conversation?.branchOfId) {
      // If no branchOfId but we have parent info, use that
      if (parentConversationId) {
        try {
          const res = await getConversation(topic.id, parentConversationId);
          const parentConv = res.data.data;

          setConversation(parentConv);
          setMessages(parentConv.messages || []);
          setBreadcrumb([]);
          setParentConversationId(null);
          setParentTitle(null);
        } catch (err) {
          console.error('Failed to navigate to parent:', err);
          alert('Failed to navigate to parent');
        }
      }
      return;
    }

    try {
      const res = await navigateToParent(conversation.branchOfId);
      const navData = res.data.data;

      setParentConversationId(conversation.id);
      setParentTitle(conversation.title);

      setConversation(navData.parentConversation);
      setMessages(navData.parentConversation.messages || []);
      setBreadcrumb(navData.ancestry || []);
    } catch (err) {
      console.error('Failed to navigate to parent:', err);
      alert('Failed to navigate to parent');
    }
  };

  // Navigate to a branch conversation
  const handleNavigateToBranch = async (branch) => {
    try {
      const branchId = branch.branchId || branch.branchConversationId;
      const res = await getConversation(topic.id, branch.branchConversationId || branchId);
      const branchConv = res.data.data;

      // Store parent info for navigation
      setParentConversationId(conversationId);
      setParentTitle(conversation?.title);

      setConversation(branchConv);
      setMessages(branchConv.messages || []);
      // Load breadcrumb for this branch
      try {
        const breadcrumbRes = await getBreadcrumb(branchId);
        setBreadcrumb(breadcrumbRes.data.data || []);
      } catch {}
    } catch (err) {
      console.error('Failed to navigate to branch:', err);
      alert('Failed to navigate to branch');
    }
  };

  // Close a branch tab - auto-discard if no messages sent
  const handleCloseTab = async (tab) => {
    const tabData = openTabs.find(t => t.id === tab.id);
    if (!tabData) return;

    if (!tabData.hasSentMessages) {
      // Auto-discard empty branch
      try {
        await mergeBranch(topic.id, conversationId, {
          branchConversationId: tab.conversationId,
          action: 'discard'
        });
      } catch (err) {
        console.error('Failed to discard empty branch:', err);
      }
    }

    // Remove tab from openTabs
    setOpenTabs(prev => prev.filter(t => t.id !== tab.id));

    // If closing active tab, switch to main
    if (activeTab === tab.id) {
      setActiveTab('main');
      if (conversation?.branchOfId) {
        handleNavigateToParent();
      }
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
          <button className="btn-ghost" onClick={() => setShowSettings(!showSettings)} title="Chat settings">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M12 15a3 3 0 100-6 3 3 0 000 6z" stroke="currentColor" strokeWidth="2" />
              <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 114 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" stroke="currentColor" strokeWidth="2" />
            </svg>
          </button>
        </div>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div className="settings-panel animate-slide-in-up">
          <div className="settings-header">
            <span>Chat Settings</span>
            <button className="btn-ghost" onClick={() => setShowSettings(false)}>
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </button>
          </div>
          <div className="settings-content">
            <div className="setting-item">
              <div className="setting-info">
                <span className="setting-label">Web Search</span>
                <span className="setting-desc">Search the web for live info</span>
              </div>
              <label className="toggle">
                <input
                  type="checkbox"
                  checked={useWebSearch}
                  onChange={(e) => setUseWebSearch(e.target.checked)}
                />
                <span className="toggle-slider"></span>
              </label>
            </div>
            <div className="setting-item">
              <div className="setting-info">
                <span className="setting-label">Explain Depth</span>
                <span className="setting-desc">Adjust explanation level</span>
              </div>
              <div className="depth-selector">
                <button
                  className={`depth-btn ${explainDepth === null ? 'active' : ''}`}
                  onClick={() => setExplainDepth(null)}
                >Normal</button>
                <button
                  className={`depth-btn ${explainDepth === 'eli5' ? 'active' : ''}`}
                  onClick={() => setExplainDepth('eli5')}
                >ELI5</button>
                <button
                  className={`depth-btn ${explainDepth === 'deep' ? 'active' : ''}`}
                  onClick={() => setExplainDepth('deep')}
                >Deep</button>
              </div>
            </div>
          </div>
        </div>
      )}

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

      {/* Back to Parent Toggle Pill (shown when in a branch) */}
      {(conversation?.isBranch || breadcrumb.length > 0) && (
        <div className="back-to-parent-pill animate-slide-in-up">
          <button className="back-to-parent-btn" onClick={handleNavigateToParent}>
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
              <path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Back to parent: {parentTitle || (breadcrumb.length > 0 ? breadcrumb[0]?.title : 'parent')}
          </button>
        </div>
      )}

      {/* Tab Bar (shown when there are branches) */}
      {(openTabs.length > 0 || conversation?.isBranch) && (
        <div className="chat-tab-bar animate-slide-in-up">
          <button
            className={`tab-item ${activeTab === 'main' ? 'active' : ''}`}
            onClick={() => {
              setActiveTab('main');
              if (conversation?.branchOfId) {
                handleNavigateToParent();
              }
            }}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
              <path d="M3 12h18M3 6h18M3 18h18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            {topic.title.length > 18 ? topic.title.slice(0, 18) + '...' : topic.title}
          </button>
          {openTabs.map((tab) => (
            <button
              key={tab.id}
              className={`tab-item ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => {
                setActiveTab(tab.id);
                handleNavigateToBranch({ branchConversationId: tab.conversationId, branchId: tab.id });
              }}
            >
              <button
                className="tab-close-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  handleCloseTab(tab);
                }}
              >
                <svg width="10" height="10" viewBox="0 0 16 16" fill="none">
                  <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </button>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                <path d="M6 3v12M18 3v12M6 9a3 3 0 100-6 3 3 0 000 6zM18 9a3 3 0 100-6 3 3 0 000 6zM6 15a3 3 0 100 6 3 3 0 000-6zM18 15a3 3 0 100 6 3 3 0 000-6z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
              {tab.title.length > 20 ? tab.title.slice(0, 20) + '...' : tab.title}
            </button>
          ))}
        </div>
      )}

      {/* Depth Warning */}
      {showDepthWarning && (
        <div className="depth-warning animate-slide-in-up">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path d="M12 9v4M12 17h.01M12 3l9 18H3L12 3z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span>You're branching deep (3+ levels). Consider returning to parent to keep context clear.</span>
          <button className="btn-ghost" onClick={() => setShowDepthWarning(false)}>
            Dismiss
          </button>
        </div>
      )}

      {/* Selection Popover - Single Button */}
      {selectionPopover && (
        <div
          className="selection-popover-wrapper"
          onClick={(e) => {
            if (e.target === e.currentTarget) setSelectionPopover(null);
          }}
        >
          <div
            className="selection-popover selection-popover-single animate-fade-in"
            style={{
              left: selectionPopover.position.x,
              top: selectionPopover.position.y,
            }}
          >
            <button
              className="branch-from-selection-btn"
              onClick={(e) => {
                e.stopPropagation();
                handleTextSelect(selectionPopover.message, selectionPopover.selection);
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path d="M6 3v12M18 3v12M6 9a3 3 0 100-6 3 3 0 000 6zM18 9a3 3 0 100-6 3 3 0 000 6zM6 15a3 3 0 100 6 3 3 0 000-6zM18 15a3 3 0 100 6 3 3 0 000-6z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
              ⎇ Branch from here
            </button>
          </div>
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
                  <div
                    className={`message-content ${msg.role === 'user' ? 'user-bubble' : 'ai-bubble'}`}
                    onMouseUp={(e) => {
                      // Clear any existing popover
                      setSelectionPopover(null);

                      const selection = window.getSelection();
                      const text = selection.toString().trim();
                      if (text && text.length > 2 && msg.role === 'assistant') {
                        const contentText = msg.content;
                        const start = contentText.indexOf(text);
                        if (start !== -1) {
                          // Show popover near the selection
                          const range = selection.getRangeAt(0);
                          const rect = range.getBoundingClientRect();
                          setSelectionPopover({
                            message: msg,
                            selection: { start, end: start + text.length, text },
                            position: {
                              x: rect.left + rect.width / 2,
                              y: rect.top - 10
                            }
                          });
                        }
                      }
                    }}
                  >
                    {msg.role === 'assistant'
                      ? renderMessageContentWithBranches(msg.content, msg.branches, handleNavigateToBranch)
                      : msg.content
                    }
                    {msg.role === 'assistant' && window.getSelection()?.toString()?.trim() && (
                      <button
                        className="branch-from-selection-btn"
                        onClick={() => handleTextSelect(msg, null)}
                        title="Branch from this message"
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                          <path d="M6 3v12M18 3v12M6 9a3 3 0 100-6 3 3 0 000 6zM18 9a3 3 0 100-6 3 3 0 000 6zM6 15a3 3 0 100 6 3 3 0 000-6zM18 15a3 3 0 100 6 3 3 0 000-6z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                        </svg>
                        Branch
                      </button>
                    )}
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
            placeholder={
              conversation?.isBranch
                ? `Dig deeper into ${conversation.title || 'this topic'}...`
                : `Ask about ${topic.title}...`
            }
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
