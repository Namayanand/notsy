import './AgentPanel.css';

const AGENTS = [
  { id: 'planner', icon: '🧠', name: 'Planner', description: 'Creates roadmaps' },
  { id: 'tutor', icon: '📚', name: 'Tutor', description: 'Explains concepts' },
  { id: 'evaluator', icon: '📝', name: 'Evaluator', description: 'Quizzes & evaluates' },
  { id: 'memory', icon: '💾', name: 'Memory', description: 'Tracks progress' },
  { id: 'motivator', icon: '🔥', name: 'Motivator', description: 'Keeps you motivated' },
  { id: 'retriever', icon: '🔍', name: 'Retriever', description: 'Search & RAG' },
];

export default function AgentPanel({ activeAgent, onAgentSelect, sessionActive }) {
  return (
    <div className="agent-panel">
      <h3>AI Agents</h3>
      <div className="agent-list">
        {AGENTS.map(agent => (
          <button
            key={agent.id}
            className={`agent-item ${activeAgent === agent.id ? 'active' : ''}`}
            onClick={() => onAgentSelect(agent.id)}
            disabled={!sessionActive}
          >
            <span className="agent-icon">{agent.icon}</span>
            <div className="agent-info">
              <span className="agent-name">{agent.name}</span>
              <span className="agent-desc">{agent.description}</span>
            </div>
            {activeAgent === agent.id && <span className="active-indicator">●</span>}
          </button>
        ))}
      </div>
    </div>
  );
}