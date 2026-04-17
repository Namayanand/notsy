import './RoadmapView.css';

export default function RoadmapView({ roadmap, currentTopic, onTopicSelect, currentTopicIndex }) {
  const renderTopic = (topic, level = 0) => {
    const isActive = currentTopicIndex !== undefined &&
                     roadmap &&
                     roadmap[currentTopicIndex]?.id === topic.id;
    const isCompleted = topic.status === 'completed';
    const isWeak = topic.status === 'weak';
    const isInProgress = topic.status === 'in_progress';

    return (
      <div
        key={topic.id}
        className={`roadmap-topic level-${level} ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''} ${isWeak ? 'weak' : ''} ${isInProgress ? 'in_progress' : ''}`}
        style={{ marginLeft: `${level * 20}px` }}
        onClick={() => onTopicSelect && onTopicSelect(topic)}
      >
        <span className="topic-status">
          {isCompleted ? '✓' : isWeak ? '⚠' : isInProgress ? '▶' : '○'}
        </span>
        <span className="topic-name">{topic.name}</span>
        <span className="topic-duration">
          {topic.duration_hours ? `${topic.duration_hours}h` : ''}
        </span>
        <span className="topic-difficulty">
          {topic.difficulty ? '●'.repeat(topic.difficulty) : ''}
        </span>
      </div>
    );
  };

  if (!roadmap || roadmap.length === 0) {
    return (
      <div className="roadmap-view">
        <h3>Learning Roadmap</h3>
        <div className="empty-state">
          <p>No roadmap generated yet</p>
        </div>
      </div>
    );
  }

  return (
    <div className="roadmap-view">
      <h3>Learning Roadmap</h3>
      <div className="roadmap-tree">
        {roadmap.map((topic, index) => renderTopic(topic, 0))}
      </div>
    </div>
  );
}