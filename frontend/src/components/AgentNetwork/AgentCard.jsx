import './AgentCard.css';

const AGENT_ICONS = {
  orchestrator: '🎯',
  planner: '📋',
  tutor: '📖',
  evaluator: '✅',
  motivator: '💪',
  retriever: '🔍',
  memory: '🧠'
};

export default function AgentCard({ agent, isSelected, onClick, expanded }) {
  const icon = getAgentIcon(agent?.name);
  const skills = agent?.card?.skills || [];

  function getAgentIcon(name) {
    if (!name) return '🤖';
    const n = name.toLowerCase();
    for (const [key, icon] of Object.entries(AGENT_ICONS)) {
      if (n.includes(key)) return icon;
    }
    return '🤖';
  }

  return (
    <div
      className={`agent-card ${isSelected ? 'selected' : ''} ${expanded ? 'expanded' : ''}`}
      onClick={onClick}
    >
      <div className="agent-card-header">
        <span className="agent-icon">{icon}</span>
        <div className="agent-info">
          <h4 className="agent-name">{agent?.name || 'Unknown Agent'}</h4>
          <span className="agent-version">v{agent?.card?.version || '1.0.0'}</span>
        </div>
        <div className="agent-status-indicator" title="Status: idle">
          <span className="status-dot idle" />
        </div>
      </div>

      <p className="agent-description">
        {agent?.card?.description || 'No description available'}
      </p>

      {expanded && (
        <div className="agent-details">
          <div className="detail-row">
            <span className="detail-label">Endpoint:</span>
            <span className="detail-value">{agent?.url || 'N/A'}</span>
          </div>
        </div>
      )}

      <div className="agent-skills">
        {skills.length === 0 ? (
          <span className="no-skills">No skills</span>
        ) : (
          skills.slice(0, expanded ? skills.length : 3).map((skill, index) => (
            <span key={index} className="skill-badge">
              {skill.id}
            </span>
          ))
        )}
        {!expanded && skills.length > 3 && (
          <span className="more-skills">+{skills.length - 3} more</span>
        )}
      </div>
    </div>
  );
}