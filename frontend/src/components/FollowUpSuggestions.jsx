export default function FollowUpSuggestions({ suggestions, onSelect }) {
  if (!suggestions || suggestions.length === 0) return null;

  return (
    <div className="follow-ups">
      {suggestions.map((text, i) => (
        <button key={i} className="follow-up-btn" onClick={() => onSelect(text)}>
          💡 {text}
        </button>
      ))}
    </div>
  );
}
