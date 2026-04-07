import { useState, useRef } from 'react';

export default function UploadPanel({ onUpload, theme, toggleTheme }) {
  const [dragover, setDragover] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const fileRef = useRef(null);

  const validExts = ['.csv', '.xlsx', '.xls'];

  const handleFile = async (file) => {
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!validExts.includes(ext)) {
      setError('Please upload a CSV or Excel file (.csv, .xlsx, .xls)');
      return;
    }

    setError('');
    setUploading(true);
    setStatus('Uploading file...');
    setProgress(30);

    try {
      setProgress(50);
      setStatus('Analyzing your data...');

      const result = await onUpload(file);

      setProgress(80);
      setStatus('Generating insights...');

      await new Promise(r => setTimeout(r, 500));
      setProgress(100);
      setStatus('Ready!');
    } catch (err) {
      setError(err.message || 'Upload failed. Please try again.');
      setUploading(false);
      setProgress(0);
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragover(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const onDragOver = (e) => {
    e.preventDefault();
    setDragover(true);
  };

  const onClickUpload = () => fileRef.current?.click();

  return (
    <div className="upload-overlay">
      {toggleTheme && (
        <button className="theme-toggle home-theme-toggle" onClick={toggleTheme} title="Toggle theme">
          {theme === 'dark' ? '☀️' : '🌙'}
        </button>
      )}
      <div className="upload-container animate-slide-up">
        <h1 className="upload-hero-title">Talking BI</h1>
        <p className="upload-hero-sub">
          Upload your data and start a conversation.<br />
          Ask questions, discover insights, and visualize trends — all in natural language.
        </p>

        <div
          className={`upload-zone ${dragover ? 'dragover' : ''}`}
          onDrop={onDrop}
          onDragOver={onDragOver}
          onDragLeave={() => setDragover(false)}
          onClick={onClickUpload}
        >
          <span className="upload-icon">📊</span>
          <div className="upload-text">
            {uploading ? status : 'Drop your CSV or Excel file here'}
          </div>
          <div className="upload-hint">
            {uploading ? '' : 'or click to browse · Supports .csv, .xlsx, .xls'}
          </div>

          {uploading && (
            <div className="upload-progress">
              <div className="upload-progress-bar">
                <div className="upload-progress-fill" style={{ width: `${progress}%` }}></div>
              </div>
            </div>
          )}

          {error && (
            <div style={{ color: 'var(--accent-red)', marginTop: 12, fontSize: '0.85rem' }}>
              {error}
            </div>
          )}

          <input
            ref={fileRef}
            type="file"
            accept=".csv,.xlsx,.xls"
            style={{ display: 'none' }}
            onChange={(e) => e.target.files[0] && handleFile(e.target.files[0])}
          />
        </div>
      </div>
    </div>
  );
}
