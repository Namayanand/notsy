import './LearningFlow.css';

const AGENT_ICONS = {
  planner: '🧠',
  tutor: '📚',
  evaluator: '📝',
  memory: '💾',
  motivator: '🔥',
  retriever: '🔍'
};

const AGENT_NAMES = {
  planner: 'Planner',
  tutor: 'Tutor',
  evaluator: 'Evaluator',
  memory: 'Memory',
  motivator: 'Motivator',
  retriever: 'Retriever'
};

export default function LearningFlow({ steps, onStepClick }) {
  if (!steps || steps.length === 0) {
    return (
      <div className="learning-flow empty">
        <div className="empty-state">
          <p>Start a study session to see the learning flow</p>
        </div>
      </div>
    );
  }

  return (
    <div className="learning-flow">
      {steps.map((step, index) => (
        <div
          key={index}
          className={`flow-step ${step.status || 'pending'}`}
          onClick={() => onStepClick && onStepClick(step)}
        >
          <span className="step-icon">
            {AGENT_ICONS[step.agent] || '🤖'}
          </span>
          <div className="step-content">
            <span className="step-agent">{AGENT_NAMES[step.agent] || step.agent}</span>
            <span className="step-action">{step.action || step.result?.message || 'Processing...'}</span>
            {step.status === 'completed' && step.result && (
              <span className="step-result">
                {step.result.roadmap?.length ? `${step.result.roadmap.length} topics planned` :
                 (step.result.explanation ? step.result.explanation.substring(0, 100) :
                 step.result.message || 'Done')}
              </span>
            )}
          </div>
          {step.status === 'in_progress' && (
            <span className="step-spinner" />
          )}
        </div>
      ))}
    </div>
  );
}