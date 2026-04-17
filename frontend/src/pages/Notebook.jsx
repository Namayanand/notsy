import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getNotebook } from '../api/notebooks';
import { getTopics, createTopic, deleteTopic } from '../api/topics';
import { createConversation, deleteConversation, getBranches } from '../api/conversations';
import { getMembers, inviteMember, removeMember, updateMemberRole } from '../api/collaboration';
import { useAuth } from '../context/AuthContext';
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
  { value: 'STUDY_GROUP', label: '👥 Study Group', desc: 'Collaborative learning' },
];

export default function Notebook() {
  const { id, topicId: activeTopicId, convId: activeConvId, nbId: routeNbId } = useParams();
  // Support both :id and :nbId route params for notebook ID
  const notebookId = routeNbId || id;
  const navigate = useNavigate();
  const { user: authUser } = useAuth();

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
  const [showStudyPlanner, setShowStudyPlanner] = useState(false);
  const [showFlashcards, setShowFlashcards] = useState(false);
  const [showQuiz, setShowQuiz] = useState(false);
  const [showShareModal, setShowShareModal] = useState(false);
  const [members, setMembers] = useState([]);

  useEffect(() => {
    loadData();
  }, [notebookId]);

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
        getNotebook(notebookId),
        getTopics(notebookId),
      ]);
      setNotebook(nbRes.data.data);
      setTopics(topicsRes.data.data || []);
    } catch (err) {
      console.error('Failed to load notebook', err);
    } finally {
      setLoading(false);
    }
  };

  const loadMembers = async () => {
    try {
      const res = await getMembers(notebookId);
      setMembers(res.data.data || []);
    } catch (err) {
      console.error('Failed to load members', err);
    }
  };

  useEffect(() => {
    if (showShareModal) {
      loadMembers();
    }
  }, [showShareModal]);

  const handleCreateTopic = async (e) => {
    e.preventDefault();
    if (!newTopicTitle.trim()) return;
    try {
      const res = await createTopic(notebookId, { title: newTopicTitle });
      setTopics((prev) => [...prev, res.data.data]);
      setShowTopicModal(false);
      setNewTopicTitle('');
      navigate(`/notebooks/${notebookId}/topics/${res.data.data.id}`);
    } catch {
      alert('Failed to create topic');
    }
  };

  const handleDeleteTopic = async (topicId, e) => {
    e.stopPropagation();
    if (!confirm('Delete this topic and all its data?')) return;
    try {
      await deleteTopic(notebookId, topicId);
      setTopics((prev) => prev.filter((t) => t.id !== topicId));
      if (activeTopicId == topicId) {
        setActiveTopic(null);
        navigate(`/notebooks/${notebookId}`);
      }
    } catch (err) {
      const msg = err.response?.data?.message;
      if (msg) {
        alert(msg);
      } else {
        alert('Failed to delete topic');
      }
    }
  };

  const handleTopicClick = (topic) => {
    setActiveTopic(topic);
    navigate(`/notebooks/${notebookId}/topics/${topic.id}`);
  };

  const handleDeleteConversation = async (convId, e) => {
    e.stopPropagation();
    // First check for branches
    try {
      const res = await getBranches(activeTopic.id, convId);
      const branches = res.data.data || [];
      if (branches.length > 0) {
        const branchTitles = branches.map(b => b.title).join(', ');
        if (!confirm(`This conversation has ${branches.length} branch(es): "${branchTitles}".\n\nDelete anyway? This will also delete all branches.`)) return;
      } else {
        if (!confirm('Delete this conversation?')) return;
      }
    } catch {
      if (!confirm('Delete this conversation?')) return;
    }
    try {
      await deleteConversation(activeTopic.id, convId);
      // Refresh the active topic data
      const topicsRes = await getTopics(notebookId);
      setTopics(topicsRes.data.data || []);
      // Clear active conversation if it was deleted
      if (activeConvId == convId) {
        navigate(`/notebooks/${notebookId}/topics/${activeTopicId}`);
      }
    } catch (err) {
      const msg = err.response?.data?.message;
      if (msg) {
        alert(msg);
      } else {
        alert('Failed to delete conversation');
      }
    }
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
          <div className="sidebar-actions">
            <button className="btn-secondary btn-sm" onClick={() => setShowShareModal(true)} title="Share notebook">
              🔗 Share
            </button>
            <button className="btn-primary btn-sm" onClick={() => setShowTopicModal(true)}>
              + Topic
            </button>
          </div>
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
            onBack={() => navigate(`/notebooks/${notebookId}/topics/${activeTopicId}`)}
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
                        onClick={() => navigate(`/notebooks/${notebookId}/topics/${activeTopic.id}/conversations/${conv.id}`)}
                      >
                        <div className="conv-info">
                          <span className="conv-title">{conv.title}</span>
                          <span className="conv-meta">
                            {conv.learningMode?.replace('_', ' ')} • {conv.isBranch ? '🌿 Branch' : 'Main'}
                          </span>
                        </div>
                        <div className="conv-actions" onClick={(e) => e.stopPropagation()}>
                          <button
                            className="btn-ghost btn-sm"
                            onClick={(e) => handleDeleteConversation(conv.id, e)}
                            title="Delete conversation"
                          >
                            🗑️
                          </button>
                          <span className="conv-arrow">›</span>
                        </div>
                      </button>
                    ))
                  )}
                </div>
              </div>

              {/* Flashcards & Quiz shortcuts */}
              <div className="topic-section">
                <div className="section-header">
                  <h3 className="section-title">🎯 Study Tools</h3>
                </div>
                <div className="study-tools-grid">
                  <button className="tool-card" onClick={() => setShowFlashcards(true)}>
                    <span className="tool-icon">📇</span>
                    <span className="tool-label">Flashcards</span>
                    <span className="tool-desc">Spaced repetition</span>
                  </button>
                  <button className="tool-card" onClick={() => setShowQuiz(true)}>
                    <span className="tool-icon">📝</span>
                    <span className="tool-label">Quiz</span>
                    <span className="tool-desc">Test yourself</span>
                  </button>
                  <button className="tool-card" onClick={() => setShowStudyPlanner(true)}>
                    <span className="tool-icon">📅</span>
                    <span className="tool-label">Study Plan</span>
                    <span className="tool-desc">Exam countdown</span>
                  </button>
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
              navigate(`/notebooks/${notebookId}/topics/${activeTopic.id}/conversations/${res.data.data.id}`);
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

      {/* Study Planner Modal */}
      {showStudyPlanner && (
        <StudyPlannerModal
          topicId={activeTopic.id}
          topics={topics}
          onClose={() => setShowStudyPlanner(false)}
        />
      )}

      {/* Flashcards Modal */}
      {showFlashcards && (
        <FlashcardsModal
          topicId={activeTopic.id}
          onClose={() => setShowFlashcards(false)}
        />
      )}

      {/* Quiz Modal */}
      {showQuiz && (
        <QuizModal
          topicId={activeTopic.id}
          onClose={() => setShowQuiz(false)}
        />
      )}

      {/* Share Modal */}
      {showShareModal && (
        <ShareModal
          notebookId={notebookId}
          notebookTitle={notebook?.title}
          members={members}
          isOwner={authUser?.id === notebook?.owner?.id}
          onClose={() => setShowShareModal(false)}
          onMembersUpdate={loadMembers}
        />
      )}
    </div>
  );
}

// Study Planner Modal Component
function StudyPlannerModal({ topicId, topics, onClose }) {
  const [examDate, setExamDate] = useState('');
  const [daysAvailable, setDaysAvailable] = useState(7);
  const [hoursPerDay, setHoursPerDay] = useState(2);
  const [difficulty, setDifficulty] = useState('balanced');
  const [loading, setLoading] = useState(false);
  const [plan, setPlan] = useState(null);

  const handleCreate = async () => {
    if (!examDate) return alert('Please set an exam date');
    setLoading(true);
    try {
      const { createStudyPlan } = await import('../api/studyPlans');
      const res = await createStudyPlan({
        title: `Study Plan - ${topics.find(t => t.id === topicId)?.title || 'Topic'}`,
        goalDescription: `Cover topic ${topicId} before exam`,
        examDate,
        daysAvailable,
        topicIds: topics.map(t => t.id),
        hoursPerDay,
        difficultyPreference: difficulty,
      });
      setPlan(res.data.data);
    } catch (err) {
      console.error('Failed to create study plan', err);
      alert('Failed to create study plan');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-lg" onClick={e => e.stopPropagation()}>
        <h2 className="modal-title">📅 Study Planner</h2>
        {!plan ? (
          <div className="modal-form">
            <div className="form-group">
              <label>Exam Date</label>
              <input type="date" value={examDate} onChange={e => setExamDate(e.target.value)} required />
            </div>
            <div className="form-group">
              <label>Days Available: {daysAvailable}</label>
              <input type="range" min="1" max="30" value={daysAvailable}
                onChange={e => setDaysAvailable(Number(e.target.value))} />
            </div>
            <div className="form-group">
              <label>Hours per Day: {hoursPerDay}</label>
              <input type="range" min="0.5" max="6" step="0.5" value={hoursPerDay}
                onChange={e => setHoursPerDay(Number(e.target.value))} />
            </div>
            <div className="form-group">
              <label>Difficulty</label>
              <div className="mode-options">
                {['easy', 'balanced', 'hard'].map(d => (
                  <button key={d} type="button"
                    className={`mode-btn ${difficulty === d ? 'active' : ''}`}
                    onClick={() => setDifficulty(d)}>
                    {d.charAt(0).toUpperCase() + d.slice(1)}
                  </button>
                ))}
              </div>
            </div>
            <div className="modal-actions">
              <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
              <button type="button" className="btn-primary" onClick={handleCreate} disabled={loading}>
                {loading ? 'Creating...' : 'Create Plan'}
              </button>
            </div>
          </div>
        ) : (
          <div className="study-plan-result">
            <p>Your AI-powered study plan has been generated!</p>
            <p className="text-muted">Check your notifications for the detailed schedule.</p>
            <div className="modal-actions">
              <button type="button" className="btn-primary" onClick={onClose}>Done</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Flashcards Modal Component
function FlashcardsModal({ topicId, onClose }) {
  const [cards, setCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showAnswer, setShowAnswer] = useState(false);
  const [reviewMode, setReviewMode] = useState(false);

  useEffect(() => {
    loadCards();
  }, [topicId]);

  const loadCards = async () => {
    setLoading(true);
    try {
      const { getDueCards } = await import('../api/flashcards');
      const res = await getDueCards(topicId);
      setCards(res.data.data || []);
    } catch (err) {
      console.error('Failed to load cards', err);
    } finally {
      setLoading(false);
    }
  };

  const handleReview = async (quality) => {
    if (cards.length === 0) return;
    const card = cards[currentIndex];
    try {
      const { reviewFlashcard } = await import('../api/flashcards');
      await reviewFlashcard(card.id, { quality });
      if (currentIndex < cards.length - 1) {
        setCurrentIndex(i => i + 1);
        setShowAnswer(false);
      } else {
        loadCards();
        setCurrentIndex(0);
        setShowAnswer(false);
      }
    } catch (err) {
      console.error('Failed to review card', err);
    }
  };

  if (loading) return <div className="modal-overlay" onClick={onClose}><div className="modal-content"><p>Loading...</p></div></div>;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-lg" onClick={e => e.stopPropagation()}>
        <h2 className="modal-title">📇 Flashcards</h2>
        {cards.length === 0 ? (
          <div className="empty-section">
            <p>No flashcards due for review!</p>
            <p className="text-muted">Start a conversation to generate cards automatically.</p>
          </div>
        ) : (
          <div className="flashcard-review">
            <p className="review-progress">{currentIndex + 1} / {cards.length}</p>
            <div className="flashcard" onClick={() => setShowAnswer(!showAnswer)}>
              <div className="flashcard-front">
                <h3>{cards[currentIndex].front}</h3>
                <p className="flashcard-hint">Tap to reveal</p>
              </div>
              {showAnswer && (
                <div className="flashcard-back">
                  <h3>{cards[currentIndex].back}</h3>
                </div>
              )}
            </div>
            {showAnswer && (
              <div className="review-buttons">
                <p>How well did you know this?</p>
                <div className="review-ratings">
                  <button className="review-btn fail" onClick={() => handleReview(1)}>Again</button>
                  <button className="review-btn hard" onClick={() => handleReview(3)}>Hard</button>
                  <button className="review-btn good" onClick={() => handleReview(4)}>Good</button>
                  <button className="review-btn easy" onClick={() => handleReview(5)}>Easy</button>
                </div>
              </div>
            )}
          </div>
        )}
        <div className="modal-actions">
          <button type="button" className="btn-secondary" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}

// Quiz Modal Component
function QuizModal({ topicId, onClose }) {
  const [quiz, setQuiz] = useState(null);
  const [currentQ, setCurrentQ] = useState(0);
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(false);
  const [completed, setCompleted] = useState(false);

  const startQuiz = async () => {
    setLoading(true);
    try {
      const { generateQuiz } = await import('../api/quizzes');
      const res = await generateQuiz({
        topicId,
        title: 'Quick Quiz',
        quizType: 'MIXED',
        questionCount: 5,
      });
      setQuiz(res.data.data);
    } catch (err) {
      console.error('Failed to start quiz', err);
      alert('Failed to generate quiz');
    } finally {
      setLoading(false);
    }
  };

  const submitAnswer = async () => {
    if (!quiz) return;
    try {
      const { submitQuizAnswer } = await import('../api/quizzes');
      await submitQuizAnswer(quiz.id, {
        questionId: quiz.questions[currentQ].id,
        answer,
      });
      if (currentQ < quiz.questions.length - 1) {
        setCurrentQ(i => i + 1);
        setAnswer('');
      } else {
        const { completeQuiz } = await import('../api/quizzes');
        await completeQuiz(quiz.id);
        setCompleted(true);
      }
    } catch (err) {
      console.error('Failed to submit answer', err);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-lg" onClick={e => e.stopPropagation()}>
        <h2 className="modal-title">📝 Quiz Mode</h2>
        {!quiz && !completed && (
          <div className="modal-form">
            <p>Test your knowledge with an AI-generated quiz!</p>
            <div className="modal-actions">
              <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
              <button type="button" className="btn-primary" onClick={startQuiz} disabled={loading}>
                {loading ? 'Generating...' : 'Start Quiz'}
              </button>
            </div>
          </div>
        )}
        {quiz && !completed && (
          <div className="quiz-active">
            <p className="quiz-progress">Question {currentQ + 1} of {quiz.questions.length}</p>
            <div className="quiz-question">
              <h3>{quiz.questions[currentQ].question}</h3>
              {quiz.questions[currentQ].options && (
                <div className="quiz-options">
                  {JSON.parse(quiz.questions[currentQ].options).map((opt, i) => (
                    <label key={i} className="quiz-option">
                      <input type="radio" name="answer" value={opt} checked={answer === opt}
                        onChange={() => setAnswer(opt)} />
                      {opt}
                    </label>
                  ))}
                </div>
              )}
              {!quiz.questions[currentQ].options && (
                <textarea value={answer} onChange={e => setAnswer(e.target.value)}
                  placeholder="Type your answer..." rows={3} />
              )}
            </div>
            <div className="modal-actions">
              <button type="button" className="btn-primary" onClick={submitAnswer} disabled={!answer}>
                {currentQ < quiz.questions.length - 1 ? 'Next' : 'Finish'}
              </button>
            </div>
          </div>
        )}
        {completed && (
          <div className="quiz-completed">
            <h3>Quiz Complete!</h3>
            <p>Great job! Check your performance in the quiz history.</p>
            <div className="modal-actions">
              <button type="button" className="btn-primary" onClick={onClose}>Done</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Share Modal Component
function ShareModal({ notebookId, notebookTitle, members, isOwner, onClose, onMembersUpdate }) {
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('EDITOR');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleInvite = async (e) => {
    e.preventDefault();
    if (!email.trim()) return;
    setLoading(true);
    setError('');
    try {
      await inviteMember(notebookId, { email, role });
      setEmail('');
      onMembersUpdate();
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to invite member');
    } finally {
      setLoading(false);
    }
  };

  const handleRemove = async (memberId) => {
    if (!confirm('Remove this member from the notebook?')) return;
    try {
      await removeMember(notebookId, memberId);
      onMembersUpdate();
    } catch (err) {
      alert('Failed to remove member');
    }
  };

  const handleRoleChange = async (memberId, newRole) => {
    try {
      await updateMemberRole(notebookId, memberId, newRole);
      onMembersUpdate();
    } catch (err) {
      alert('Failed to update role');
    }
  };

  const getRoleBadge = (r) => {
    const colors = { OWNER: 'badge-owner', EDITOR: 'badge-editor', VIEWER: 'badge-viewer' };
    return <span className={`badge ${colors[r] || 'badge-viewer'}`}>{r}</span>;
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <h2 className="modal-title">🔗 Share "{notebookTitle}"</h2>

        {isOwner && (
          <form onSubmit={handleInvite} className="modal-form">
            <div className="form-group">
              <label>Invite by email</label>
              <div className="invite-row">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="user@example.com"
                  required
                />
                <select value={role} onChange={(e) => setRole(e.target.value)}>
                  <option value="EDITOR">Editor</option>
                  <option value="VIEWER">Viewer</option>
                </select>
                <button type="submit" className="btn-primary" disabled={loading}>
                  {loading ? '...' : 'Invite'}
                </button>
              </div>
              {error && <p className="text-error">{error}</p>}
            </div>
          </form>
        )}

        <div className="members-list">
          <h3>Members</h3>
          {members.length === 0 ? (
            <p className="text-muted">No collaborators yet</p>
          ) : (
            <div className="members-grid">
              {members.map((m) => (
                <div key={m.id} className="member-item">
                  <div className="member-info">
                    <span className="member-name">{m.user?.name || m.user?.email || 'Unknown'}</span>
                    <span className="member-email">{m.user?.email}</span>
                  </div>
                  <div className="member-actions">
                    {getRoleBadge(m.role)}
                    {isOwner && m.role !== 'OWNER' && (
                      <>
                        <select
                          value={m.role}
                          onChange={(e) => handleRoleChange(m.id, e.target.value)}
                          className="role-select"
                        >
                          <option value="EDITOR">Editor</option>
                          <option value="VIEWER">Viewer</option>
                        </select>
                        <button
                          className="btn-ghost btn-sm"
                          onClick={() => handleRemove(m.id)}
                          title="Remove"
                        >
                          🗑️
                        </button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="modal-actions">
          <button type="button" className="btn-secondary" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}
