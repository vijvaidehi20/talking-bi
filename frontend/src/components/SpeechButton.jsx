import { useState, useEffect } from 'react';

export default function SpeechButton({ onTranscript, onListeningChange, disabled }) {
  const [isListening, setIsListening] = useState(false);
  const [recognition, setRecognition] = useState(null);

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const rec = new SpeechRecognition();
      rec.continuous = false; // Stop after speaking
      rec.interimResults = false; // Only final result
      rec.lang = 'en-US';

      rec.onstart = () => {
        setIsListening(true);
        onListeningChange?.(true);
      };

      rec.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        onTranscript?.(transcript);
      };

      rec.onend = () => {
        setIsListening(false);
        onListeningChange?.(false);
      };

      rec.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setIsListening(false);
        onListeningChange?.(false);
      };

      setRecognition(rec);
    }
  }, [onTranscript, onListeningChange]);

  const toggleListening = () => {
    if (isListening) {
      recognition?.stop();
    } else {
      recognition?.start();
    }
  };

  // If browser doesn't support SpeechRecognition, don't render anything
  if (!recognition) return null;

  return (
    <button
      type="button"
      className={`chat-speech-btn ${isListening ? 'listening' : ''}`}
      onClick={toggleListening}
      disabled={disabled}
      title={isListening ? "Stop listening" : "Start voice input"}
      style={{
        width: '46px',
        height: '46px',
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--border-subtle)',
        background: isListening ? 'var(--gradient-accent)' : 'var(--bg-tertiary)',
        color: isListening ? 'white' : 'var(--text-secondary)',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '18px',
        transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
        flexShrink: 0,
        position: 'relative',
        overflow: 'hidden'
      }}
    >
      {isListening ? '🎙️' : '🎤'}
      {isListening && <div className="listening-pulse"></div>}
    </button>
  );
}
