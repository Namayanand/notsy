import { useEffect, useRef } from 'react';
import './TaskFeed.css';

const STATUS_COLORS = {
  submitted: '#94a3b8',
  working: '#60a5ba',
  completed: '#4ade80',
  failed: '#f87171'
};

const AGENT_COLORS = {
  orchestrator: '#7c5bf5',
  planner: '#f472b6',
  tutor: '#60a5fa',
  evaluator: '#4ade80',
  motivator: '#fbbf24',
  retriever: '#a78bfa',
  memory: '#22d3d1'
};

export default function TaskFeed({ tasks }) {
  const feedRef = useRef(null);

  useEffect(() => {
    if (feedRef.current && tasks.length > 0) {
      feedRef.current.scrollTop = 0;
    }
  }, [tasks]);

  function getAgentColor(agentName) {
    if (!agentName) return '#94a3b8';
    const name = agentName.toLowerCase();
    for (const [key, color] of Object.entries(AGENT_COLORS)) {
      if (name.includes(key)) return color;
    }
    return '#94a3b8';
  }

  function formatTime(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }

  function parseAgentChain(chainStr) {
    if (!chainStr) return [];
    try {
      return JSON.parse(chainStr);
    } catch {
      return [];
    }
  }

  function formatDuration(seconds) {
    if (!seconds && seconds !== 0) return '';
    return `${seconds.toFixed(1)}s`;
  }

  return (
    <div className="task-feed" ref={feedRef}>
      {tasks.length === 0 ? (
        <div className="task-feed-empty">
          <span>No tasks yet</span>
          <p>Trigger a test task to see agent interactions</p>
        </div>
      ) : (
        tasks.map((task, index) => {
          const chain = parseAgentChain(task.agentChain);
          const input = task.inputPayload?.content || task.inputPayload?.message || '';
          const inputPreview = input.length > 50 ? input.slice(0, 47) + '...' : input;

          return (
            <div
              key={task.id}
              className="task-feed-item"
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <div className="task-header">
                <span
                  className="task-status-dot"
                  style={{ background: STATUS_COLORS[task.status] || '#94a3b8' }}
                />
                <span className="task-skill">{task.skill || 'auto'}</span>
                <span className="task-time">{formatTime(task.createdAt)}</span>
              </div>

              {inputPreview && (
                <div className="task-input">
                  <span className="input-label">Input:</span>
                  <span className="input-text">{inputPreview}</span>
                </div>
              )}

              {chain.length > 0 && (
                <div className="task-chain">
                  {chain.map((step, i) => (
                    <div key={i} className="chain-step">
                      <span
                        className="chain-agent"
                        style={{ color: getAgentColor(step.agent) }}
                      >
                        {step.agent}
                      </span>
                      <span className="chain-duration">
                        {formatDuration(step.duration)}
                      </span>
                      {i < chain.length - 1 && (
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" className="chain-arrow">
                          <path d="M5 12h14M14 6l6 6-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {task.outputPayload && (
                <div className="task-output">
                  <span className="output-label">Output:</span>
                  <span className="output-text">
                    {task.outputPayload.message?.slice(0, 100) || 'Completed'}
                  </span>
                </div>
              )}
            </div>
          );
        })
      )}
    </div>
  );
}