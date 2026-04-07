import { useState, useRef, useEffect, useCallback } from 'react';
import MessageBubble from './MessageBubble';
import FollowUpSuggestions from './FollowUpSuggestions';
import SmartSuggestions from './SmartSuggestions';
import ChartPanel from './ChartPanel';
import SpeechButton from './SpeechButton';

export default function ChatInterface({ messages = [], onSend, loading, followUps = [], dataset, chartConfig }) {
  const [input, setInput] = useState('');
  const [isListening, setIsListening] = useState(false);
  const messagesEndRef = useRef(null);

  // Custom drag logic
  const [leftWidth, setLeftWidth] = useState(60); // percentage
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleMouseDown = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleMouseUp = useCallback(() => {
    if (isDragging) setIsDragging(false);
  }, [isDragging]);

  const handleMouseMove = useCallback((e) => {
    if (!isDragging || !containerRef.current) return;
    const containerWidth = containerRef.current.getBoundingClientRect().width;
    let newWidthPercentage = (e.clientX / containerWidth) * 100;
    
    // Constraints (Left >= 40%, Right >= 30%)
    if (newWidthPercentage < 40) newWidthPercentage = 40;
    if (newWidthPercentage > 70) newWidthPercentage = 70;
    
    setLeftWidth(newWidthPercentage);
  }, [isDragging]);

  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    } else {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isDragging, handleMouseMove, handleMouseUp]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;
    onSend(input.trim());
    setInput('');
  };

  const handleFollowUp = (text) => {
    if (loading) return;
    onSend(text);
  };

  const handleTranscript = (transcript) => {
    if (!transcript) return;
    setInput(transcript);
    // Optional: Auto-send if desired
    // if (transcript.length > 5) onSend(transcript);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="chat-layout" ref={containerRef} style={{ display: 'flex', flex: 1, minHeight: 0, overflow: 'hidden' }}>
      {/* Left: conversation */}
      <div 
        className="chat-main" 
        style={{ width: `${leftWidth}%`, display: 'flex', flexDirection: 'column', minHeight: 0 }}
      >
        <div className="chat-messages" style={{ flex: 1, overflowY: 'auto' }}>
          {messages?.length === 0 && dataset && (
            <SmartSuggestions dataset={dataset} onSend={handleFollowUp} />
          )}

          {messages?.map((msg, i) => (
            <MessageBubble key={i} message={msg} />
          ))}

          {loading && (
            <div className="message message-ai">
              <div className="message-avatar">🤖</div>
              <div className="message-content">
                <div className="typing-indicator">
                  <div className="typing-dot"></div>
                  <div className="typing-dot"></div>
                  <div className="typing-dot"></div>
                </div>
              </div>
            </div>
          )}

          {!loading && followUps?.length > 0 && (
            <FollowUpSuggestions suggestions={followUps} onSelect={handleFollowUp} />
          )}

          <div ref={messagesEndRef} />
        </div>

        <form className="chat-input-area" onSubmit={handleSubmit}>
          <div className="chat-input-wrapper">
            <SpeechButton
              onTranscript={handleTranscript}
              onListeningChange={setIsListening}
              disabled={loading}
            />
            <input
              className="chat-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={isListening ? "🎙️ Listening..." : "Ask a question about your data..."}
              disabled={loading}
              id="chat-input"
              style={{
                borderColor: isListening ? 'var(--accent-cyan)' : 'var(--border-subtle)',
                boxShadow: isListening ? 'var(--shadow-glow-cyan)' : 'none',
              }}
            />
            <button
              className="chat-send-btn"
              type="submit"
              disabled={!input.trim() || loading}
              id="chat-send"
            >
              ➤
            </button>
          </div>
        </form>
      </div>

      <div 
        className="chat-resize-handle" 
        onMouseDown={handleMouseDown}
        onDoubleClick={() => setLeftWidth(60)}
        data-resize-handle-active={isDragging ? true : undefined}
      >
        <div className="chat-resize-handle-inner" />
      </div>

      {/* Right: chart (Interactive Builder) */}
      <div 
        className="chat-sidebar" 
        style={{ width: `calc(${100 - leftWidth}% - 8px)`, display: 'flex', flexDirection: 'column', minHeight: 0, overflowY: 'auto', minWidth: '380px' }}
      >
        <ChartPanel dataset={dataset} />
      </div>
    </div>
  );
}
