export default function Header({ dataset, activeTab, onTabChange, theme, toggleTheme, onNewDataset }) {
  const tabs = [
    { id: 'chat', label: '💬 Chat' },
    { id: 'dashboard', label: '📊 Dashboard' },
  ];

  return (
    <header className="header">
      <div className="header-brand">
        <div className="header-logo">TB</div>
        <div className="header-title">Talking BI</div>
      </div>

      {dataset && (
        <nav className="header-tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              className={`header-tab ${activeTab === tab.id ? 'header-tab-active' : ''}`}
              onClick={() => onTabChange(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      )}

      <div className="header-actions">
        {dataset && (
          <div className="header-dataset">
            <span className="dot"></span>
            <span>{dataset.filename}</span>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
              {dataset.row_count} rows
            </span>
          </div>
        )}
        <button className="theme-toggle" onClick={toggleTheme} title="Toggle theme">
          {theme === 'dark' ? '☀️' : '🌙'}
        </button>
        {dataset && (
          <button className="new-dataset-btn" onClick={onNewDataset}>+ New</button>
        )}
      </div>
    </header>
  );
}
