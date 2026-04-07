export default function SmartSuggestions({ dataset, onSend }) {
  if (!dataset) return null;

  const cols = dataset.columns || [];
  const numCols = cols.filter((c) => ['int64', 'float64', 'int32', 'float32'].includes(c.dtype));
  const catCols = cols.filter((c) => ['object', 'category'].includes(c.dtype));

  // ── Data-driven query suggestions (use real column names) ──
  const queries = [];
  if (numCols.length > 0 && catCols.length > 0) {
    queries.push(`Which ${catCols[0].name} has the highest ${numCols[0].name}?`);
    queries.push(`Top 5 by ${numCols[0].name}`);
  }
  if (numCols.length > 0) {
    queries.push(`Show distribution of ${numCols[0].name}`);
  }
  if (numCols.length >= 2 && catCols.length > 0) {
    queries.push(`Compare ${numCols[0].name} vs ${numCols[1].name} by ${catCols[0].name}`);
  }
  if (queries.length < 4) {
    queries.push('Give me a summary of this dataset');
  }

  // ── Data-driven chart suggestions (NEVER generic labels) ──
  const charts = [];
  if (catCols.length > 0 && numCols.length > 0) {
    charts.push({
      icon: '📊',
      label: `${numCols[0].name} by ${catCols[0].name}`,
      query: `Show a bar chart of ${numCols[0].name} by ${catCols[0].name}`,
    });
  }
  if (catCols.length > 0 && numCols.length >= 2) {
    charts.push({
      icon: '📈',
      label: `${numCols[1].name} by ${catCols[0].name}`,
      query: `Show a chart of ${numCols[1].name} by ${catCols[0].name}`,
    });
  }
  if (numCols.length > 0) {
    charts.push({
      icon: '🏆',
      label: `Top orders by ${numCols[0].name}`,
      query: `Show me top 10 by ${numCols[0].name}`,
    });
  }
  if (catCols.length > 0) {
    charts.push({
      icon: '🍩',
      label: `${catCols[0].name} breakdown`,
      query: `Show ${catCols[0].name} distribution`,
    });
  }

  return (
    <div className="smart-suggestions animate-slide-up">
      <div className="smart-header">
        <span className="smart-emoji">✨</span>
        <div>
          <div className="smart-title">Your data is ready</div>
          <div className="smart-subtitle">
            <strong>{dataset.filename}</strong> · {dataset.row_count} rows · {dataset.column_count} columns
          </div>
        </div>
      </div>

      {/* Query suggestions */}
      <div className="smart-section">
        <div className="smart-label">💬 Ask a question</div>
        <div className="smart-grid">
          {queries.slice(0, 4).map((q, i) => (
            <button key={i} className="sg-card" onClick={() => onSend(q)}>
              <span className="sg-icon">🔍</span>
              <span className="sg-text">{q}</span>
            </button>
          ))}
        </div>
      </div>

    </div>
  );
}
