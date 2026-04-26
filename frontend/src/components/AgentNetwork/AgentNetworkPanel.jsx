import { useState, useEffect } from 'react';
import AgentGraph from './AgentGraph';
import TaskFeed from './TaskFeed';
import AgentCard from './AgentCard';
import './AgentNetworkPanel.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';

export default function AgentNetworkPanel() {
  const [agents, setAgents] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [polling, setPolling] = useState(false);
  const [health, setHealth] = useState(null);
  const [healthLoading, setHealthLoading] = useState(true);

  useEffect(() => {
    loadAgents();
    loadRecentTasks();
    loadHealth();

    // Poll for task updates every 3 seconds
    const taskInterval = setInterval(() => {
      loadRecentTasks();
    }, 3000);

    // Poll for health updates every 10 seconds
    const healthInterval = setInterval(() => {
      loadHealth();
    }, 10000);

    return () => {
      clearInterval(taskInterval);
      clearInterval(healthInterval);
    };
  }, []);

  const loadAgents = async () => {
    try {
      const res = await fetch(`${API_URL}/api/a2a/registry`);
      const data = await res.json();
      setAgents(data.agents || []);
    } catch (err) {
      console.error('Failed to load agents:', err);
    }
  };

  const loadRecentTasks = async () => {
    try {
      const res = await fetch(`${API_URL}/api/a2a/history/recent?limit=10`);
      if (res.ok) {
        const data = await res.json();
        setTasks(data);
      }
    } catch (err) {
      console.error('Failed to load tasks:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadHealth = async () => {
    try {
      const res = await fetch(`${API_URL}/api/a2a/health`);
      if (res.ok) {
        const data = await res.json();
        setHealth(data);
      }
    } catch (err) {
      console.error('Failed to load health:', err);
    } finally {
      setHealthLoading(false);
    }
  };

  const handleTestTask = async () => {
    setPolling(true);
    try {
      const res = await fetch(`${API_URL}/api/a2a/tasks/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          skill: 'auto',
          input: { content: 'Explain machine learning in simple terms' },
          sessionId: 'test-' + Date.now()
        })
      });
      const data = await res.json();
      if (data.id) {
        // Poll for completion
        let attempts = 0;
        const pollInterval = setInterval(async () => {
          attempts++;
          const statusRes = await fetch(`${API_URL}/api/a2a/tasks/${data.id}`);
          const statusData = await statusRes.json();
          if (statusData.status === 'completed' || statusData.status === 'failed' || attempts > 30) {
            clearInterval(pollInterval);
            setPolling(false);
            loadRecentTasks();
          }
        }, 1000);
      }
    } catch (err) {
      console.error('Test task failed:', err);
      setPolling(false);
    }
  };

  return (
    <div className="agent-network-panel">
      <div className="agent-network-header">
        <div className="health-bar-header">
          <div className="health-bar">
            <div className="health-status">
              <div className={`status-indicator ${healthLoading ? 'unknown' : (health?.system_status || 'unknown')}`}></div>
              <span>{healthLoading ? 'Loading...' : `System: ${(health?.system_status || 'unknown').toUpperCase()}`}</span>
            </div>
            {!healthLoading && health?.agents && (
              <div className="health-details">
                {Object.entries(health.agents).map(([name, agentHealth]) => (
                  <div key={name} className="health-metric">
                    <div className={`dot ${agentHealth.status}`}></div>
                    <span className="capitalize">{name}</span>
                  </div>
                ))}
                <div className="health-metric">
                  <span>Total Tasks: {health.total_tasks_processed || 0}</span>
                </div>
              </div>
            )}
          </div>
        </div>

        <button
          className="test-task-btn"
          onClick={handleTestTask}
          disabled={polling}
        >
          {polling ? (
            <span className="spinner spinner-sm" />
          ) : (
            <>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M12 3v6m0 0v6m0-6h6m-6 0H6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Trigger Test Task
            </>
          )}
        </button>
      </div>

      <div className="agent-network-content">
        <div className="agent-graph-section">
          <h3>Agent Graph</h3>
          <AgentGraph agents={agents} tasks={tasks} onAgentClick={setSelectedAgent} />
        </div>

        <div className="agent-sidebar">
          <div className="agent-cards-section">
            <h3>Discovered Agents</h3>
            <div className="agent-cards-list">
              {loading ? (
                <div className="loading-state">Loading agents...</div>
              ) : agents.length === 0 ? (
                <div className="empty-state">No agents discovered</div>
              ) : (
                agents.map(agent => (
                  <AgentCard
                    key={agent.name}
                    agent={agent}
                    isSelected={selectedAgent?.name === agent.name}
                    onClick={() => setSelectedAgent(agent)}
                  />
                ))
              )}
            </div>
          </div>

          <div className="task-feed-section">
            <h3>Recent Tasks</h3>
            <TaskFeed tasks={tasks} />
          </div>
        </div>
      </div>

      {selectedAgent && (
        <div className="agent-detail-modal" onClick={() => setSelectedAgent(null)}>
          <div className="agent-detail-content" onClick={e => e.stopPropagation()}>
            <button className="close-btn" onClick={() => setSelectedAgent(null)}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </button>
            <AgentCard agent={selectedAgent} expanded />
          </div>
        </div>
      )}
    </div>
  );
}