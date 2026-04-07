export default function InsightsPanel({ insights, onExplore }) {
  if (!insights || insights.length === 0) {
    return (
      <div className="insights-section">
        <div className="panel-header">
          <span>💡</span> Auto-Insights
        </div>
        <div style={{ padding: '30px 0', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          Insights will be generated when you upload data
        </div>
      </div>
    );
  }

  return (
    <div className="insights-section">
      <div className="panel-header">
        <span>💡</span> Auto-Insights ({insights.length})
      </div>
      <div className="insights-grid" style={{ marginTop: 12 }}>
        {insights.map((insight, i) => (
          <div
            key={i}
            className={`insight-card ${insight.category} animate-slide-up`}
            style={{ animationDelay: `${i * 0.1}s` }}
            onClick={() => onExplore?.(insight.text)}
          >
            <div className="insight-header">
              <span className="insight-category">{insight.category}</span>
              <span className="insight-score">
                Impact: {Math.round(insight.impact_score * 100)}%
              </span>
            </div>
            <div className="insight-text">{insight.text}</div>
            <div className="insight-explore">Click to explore →</div>
          </div>
        ))}
      </div>
    </div>
  );
}
