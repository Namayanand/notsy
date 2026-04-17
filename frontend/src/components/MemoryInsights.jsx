import './MemoryInsights.css';

export default function MemoryInsights({ insights }) {
  const weakTopics = insights?.weak_topics || [];
  const improvementTrend = insights?.improvement_trend || [];
  const mistakeCount = insights?.mistake_count || 0;

  return (
    <div className="memory-insights">
      <h3>Memory Insights</h3>

      <div className="insight-section">
        <h4>Weak Topics ({weakTopics.length})</h4>
        {weakTopics.length > 0 ? (
          <ul className="weak-topics">
            {weakTopics.map((topic, i) => (
              <li key={i}>{topic}</li>
            ))}
          </ul>
        ) : (
          <p className="empty-text">No weak topics identified yet</p>
        )}
      </div>

      <div className="insight-section">
        <h4>Total Mistakes</h4>
        <div className="stat-value">{mistakeCount}</div>
      </div>

      <div className="insight-section">
        <h4>Improvement Trend</h4>
        {improvementTrend.length > 0 ? (
          <div className="trend-chart">
            {improvementTrend.map((score, i) => (
              <div key={i} className="trend-bar-container">
                <div
                  className="trend-bar"
                  style={{ height: `${score}%` }}
                  title={`${score}%`}
                />
              </div>
            ))}
          </div>
        ) : (
          <p className="empty-text">Not enough data yet</p>
        )}
      </div>
    </div>
  );
}