export default function DataPreview({ dataset }) {
  if (!dataset?.preview?.length) {
    return (
      <div className="data-preview-empty">
        <p>No preview data available.</p>
      </div>
    );
  }

  const columns = Object.keys(dataset.preview[0]);

  return (
    <div className="data-preview">
      <div className="data-preview-header">
        <h3>📋 Data Preview</h3>
        <span className="data-preview-meta">
          Showing {dataset.preview.length} of {dataset.row_count} rows · {dataset.column_count} columns
        </span>
      </div>

      <div className="data-preview-table-wrapper">
        <table className="data-preview-table">
          <thead>
            <tr>
              <th>#</th>
              {columns.map((col) => (
                <th key={col}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dataset.preview.map((row, i) => (
              <tr key={i}>
                <td className="row-num">{i + 1}</td>
                {columns.map((col) => (
                  <td key={col}>
                    {typeof row[col] === 'number' ? row[col].toLocaleString() : String(row[col] ?? '')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Column Info */}
      <div className="data-preview-columns">
        <h3>📊 Column Details</h3>
        <div className="column-cards">
          {dataset.columns?.map((col) => (
            <div key={col.name} className="column-card">
              <div className="column-card-name">{col.name}</div>
              <div className="column-card-type">{col.dtype}</div>
              <div className="column-card-stats">
                {col.unique_count} unique · {col.null_count} nulls
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
