import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import AgentPanel from '../components/AgentPanel';
import LearningFlow from '../components/LearningFlow';
import RoadmapView from '../components/RoadmapView';
import MemoryInsights from '../components/MemoryInsights';
import { startAgentSession, getAgentState, getRoadmap, getInsights, endSession, connectAgentStream } from '../api/agents';
import { useAuth } from '../context/AuthContext';
import './StudySession.css';

export default function StudySession() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [sessionId, setSessionId] = useState(null);
  const [activeAgent, setActiveAgent] = useState(null);
  const [flowSteps, setFlowSteps] = useState([]);
  const [roadmap, setRoadmap] = useState([]);
  const [currentTopicIndex, setCurrentTopicIndex] = useState(0);
  const [insights, setInsights] = useState({});
  const [timer, setTimer] = useState(0);
  const [showStartModal, setShowStartModal] = useState(true);
  const [goal, setGoal] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const wsRef = useRef(null);

  // Timer
  useEffect(() => {
    if (sessionId) {
      const interval = setInterval(() => setTimer(t => t + 1), 1000);
      return () => clearInterval(interval);
    }
  }, [sessionId]);

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  // Load insights
  useEffect(() => {
    if (user?.id) {
      getInsights(user.id)
        .then(res => setInsights(res.data.insights || {}))
        .catch(console.error);
    }
  }, [user]);

  // Start session
  const handleStartSession = async (e) => {
    e.preventDefault();
    if (!goal.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const res = await startAgentSession(goal);
      const newSessionId = res.data.session_id;
      setSessionId(newSessionId);
      setShowStartModal(false);

      // Connect WebSocket
      wsRef.current = connectAgentStream(newSessionId);
      wsRef.current.onopen = () => {
        console.log('WebSocket connected');
        // Send initial message to start the learning flow
        wsRef.current.send(JSON.stringify({
          message: goal,
          payload: { goal: goal }
        }));
      };
      wsRef.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleStreamEvent(data);
      };
      wsRef.current.onerror = (err) => console.error('WebSocket error:', err);
      wsRef.current.onclose = () => console.log('WebSocket closed');

    } catch (err) {
      setError('Failed to start session. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Handle WebSocket events
  const handleStreamEvent = useCallback((event) => {
    switch (event.type) {
      case 'agent_start':
        setActiveAgent(event.data.agent);
        setFlowSteps(prev => [...prev, { agent: event.data.agent, status: 'in_progress' }]);
        break;
      case 'agent_complete':
        setFlowSteps(prev => prev.map(s =>
          s.agent === event.data.agent
            ? { ...s, status: 'completed', result: event.data.result }
            : s
        ));

        // Update roadmap if planner completed
        if (event.data.agent === 'planner' && event.data.result?.roadmap) {
          setRoadmap(event.data.result.roadmap);
        }
        break;
      case 'flow_complete':
        console.log('Flow complete:', event.data);
        break;
      case 'error':
        setError(event.data.error);
        break;
      default:
        break;
    }
  }, []);

  // End session
  const handleEndSession = async () => {
    if (sessionId) {
      try {
        await endSession(sessionId);
      } catch (err) {
        console.error('Error ending session:', err);
      }
    }
    if (wsRef.current) {
      wsRef.current.close();
    }
    navigate('/');
  };

  // Handle agent selection
  const handleAgentSelect = (agentId) => {
    if (!sessionId) return;
    setActiveAgent(agentId);
  };

  // Handle topic selection
  const handleTopicSelect = (topic) => {
    console.log('Selected topic:', topic);
    // Could trigger tutor to explain this topic
  };

  return (
    <div className="study-session">
      {/* Start Session Modal */}
      {showStartModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h2>Start AI Study Session</h2>
            <p>What would you like to learn today?</p>
            <form onSubmit={handleStartSession}>
              <input
                type="text"
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                placeholder="e.g., Data Structures, Python, Machine Learning..."
                autoFocus
              />
              {error && <p className="error-text">{error}</p>}
              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => navigate('/')}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={loading || !goal.trim()}>
                  {loading ? 'Starting...' : 'Start Session'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Main Session UI */}
      {!showStartModal && (
        <>
          <div className="session-header">
            <div className="header-left">
              <h1>AI Study Session</h1>
              <span className="session-goal">Learning: {goal}</span>
            </div>
            <div className="header-right">
              <div className="session-timer">{formatTime(timer)}</div>
              <button className="btn-danger" onClick={handleEndSession}>
                End Session
              </button>
            </div>
          </div>

          <div className="session-layout">
            <aside className="left-sidebar">
              <AgentPanel
                activeAgent={activeAgent}
                onAgentSelect={handleAgentSelect}
                sessionActive={!!sessionId}
              />
              <RoadmapView
                roadmap={roadmap}
                currentTopic={activeAgent}
                currentTopicIndex={currentTopicIndex}
                onTopicSelect={handleTopicSelect}
              />
            </aside>

            <main className="main-panel">
              <LearningFlow
                steps={flowSteps}
              />
            </main>

            <aside className="right-sidebar">
              <MemoryInsights insights={insights} />
            </aside>
          </div>
        </>
      )}
    </div>
  );
}