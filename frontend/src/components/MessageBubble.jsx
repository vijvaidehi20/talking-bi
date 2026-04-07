import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';

export default function MessageBubble({ message }) {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const isUser = message.role === 'user';
  const responseType = message.response_type || 'analysis';
  const title = message.title || '';

  // Stop speaking if component unmounts
  useEffect(() => {
    return () => {
      if (isSpeaking) window.speechSynthesis.cancel();
    };
  }, [isSpeaking]);

  const cleanText = (text) => {
    return text
      .replace(/\*\*/g, '') // Remove bold markdown
      .replace(/[#_*`~]/g, '') // Remove other common markdown
      .replace(/[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu, '') // Basic emoji removal
      .replace(/\n+/g, ' ') // Replace line breaks with spaces
      .trim();
  };

  const toggleSpeech = () => {
    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    } else {
      // Cancel any ongoing speech first
      window.speechSynthesis.cancel();
      
      const utterance = new SpeechSynthesisUtterance(cleanText(message.content));
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);
      
      window.speechSynthesis.speak(utterance);
      setIsSpeaking(true);
    }
  };

  // Map response_type to icon + color accent
  const typeConfig = {
    summary: { icon: '📊', accent: 'var(--accent-cyan)' },
    chart: { icon: '📈', accent: 'var(--accent-violet)' },
    insight: { icon: '🔍', accent: 'var(--accent-amber)' },
    analysis: { icon: '🧠', accent: 'var(--accent-green)' },
    fallback: { icon: '💡', accent: 'var(--accent-pink)' },
  };
  const config = typeConfig[responseType] || typeConfig.analysis;

  return (
    <div className={`message ${isUser ? 'message-user' : 'message-ai'}`}>
      <div className="message-avatar">
        {isUser ? '👤' : '🤖'}
      </div>
      <div className="message-content" style={{ position: 'relative' }}>
        {/* TTS Toggle Button for AI Messages */}
        {!isUser && (
          <button
            onClick={toggleSpeech}
            style={{
              position: 'absolute',
              top: '8px',
              right: '8px',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontSize: '14px',
              opacity: isSpeaking ? 1 : 0.4,
              transition: 'opacity 0.2s',
              zIndex: 10,
              padding: '4px',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.opacity = 1)}
            onMouseLeave={(e) => (!isSpeaking && (e.currentTarget.style.opacity = 0.4))}
            title={isSpeaking ? "Stop Speaking" : "Listen to Response"}
          >
            {isSpeaking ? '⏹️' : '🔊'}
          </button>
        )}

        {/* Response title badge for AI messages */}
        {!isUser && title && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            marginBottom: '8px',
            paddingBottom: '8px',
            borderBottom: '1px solid var(--border-subtle)',
            marginRight: '24px', // Space for speaker button
          }}>
            <span style={{ fontSize: '14px' }}>{config.icon}</span>
            <span style={{
              fontSize: '0.72rem',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              color: config.accent,
            }}>
              {title}
            </span>
          </div>
        )}

        {/* Render markdown for AI, plain text for user */}
        {isUser ? (
          <div style={{ whiteSpace: 'pre-wrap' }}>{message.content}</div>
        ) : (
          <div className="markdown-content">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        )}

        {/* Data table */}
        {message.data_table && message.data_table.length > 0 && (
          <div className="message-table">
            <table>
              <thead>
                <tr>
                  {Object.keys(message.data_table[0]).map((key) => (
                    <th key={key}>{key}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {message.data_table.slice(0, 10).map((row, i) => (
                  <tr key={i}>
                    {Object.values(row).map((val, j) => (
                      <td key={j}>{typeof val === 'number' ? val.toLocaleString() : String(val)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {message.data_table.length > 10 && (
              <div style={{ padding: '8px 12px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Showing 10 of {message.data_table.length} rows
              </div>
            )}
          </div>
        )}

        {/* Fallback suggestions card */}
        {responseType === 'fallback' && !isUser && message.follow_ups?.length > 0 && (
          <div style={{
            marginTop: '12px',
            padding: '12px',
            background: 'var(--bg-tertiary)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-subtle)',
          }}>
            <div style={{
              fontSize: '0.72rem',
              fontWeight: 600,
              color: 'var(--text-muted)',
              marginBottom: '8px',
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
            }}>
              Suggested queries
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {message.follow_ups.map((text, i) => (
                <div
                  key={i}
                  style={{
                    padding: '8px 12px',
                    background: 'var(--bg-glass)',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-subtle)',
                    fontSize: '0.82rem',
                    color: 'var(--text-secondary)',
                    cursor: 'pointer',
                    transition: 'all 150ms ease',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = 'var(--accent-cyan)';
                    e.currentTarget.style.color = 'var(--text-accent)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = 'var(--border-subtle)';
                    e.currentTarget.style.color = 'var(--text-secondary)';
                  }}
                  onClick={() => {
                    window.dispatchEvent(new CustomEvent('followup-click', { detail: text }));
                  }}
                >
                  💡 {text}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
