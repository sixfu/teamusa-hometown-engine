import { useState, useRef, useEffect, useCallback } from 'react';
import { queryAgent } from '../services/api';

const SUGGESTED = [
  "Show me the top basketball hubs",
  "Which sports are growing fastest?",
  "Compare Olympic and Paralympic athlete distribution",
  "Which regions have the most athletes?",
  "How does elevation and climate affect athlete concentration?",
];

function fmtTime(d) {
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

export default function AgentQA({ athleteType }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(null);
  const bottomRef = useRef(null);
  const lastQuestionRef = useRef('');

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const send = useCallback(async (question) => {
    const q = question.trim();
    if (!q || loading) return;
    lastQuestionRef.current = q;

    // Build history from last 6 messages (3 exchanges) for short-term memory
    const history = messages.slice(-6).map(m => ({ role: m.role, content: m.content }));

    setMessages(prev => [...prev, { role: 'user', content: q, ts: new Date(), sources: [] }]);
    setInput('');
    setLoading(true);
    setError(null);
    try {
      const data = await queryAgent(q, true, history);
      setMessages(prev => [...prev, {
        role: 'agent',
        content: data.answer,
        ts: new Date(),
        sources: data.sources || [],
        dataUsed: data.data_used,
      }]);
    } catch (err) {
      console.error('Agent error:', err);
      setError('Unable to connect to agent. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [loading]);

  const handleSubmit = useCallback((e) => {
    e.preventDefault();
    send(input);
  }, [input, send]);

  const handleKey = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(input); }
  }, [input, send]);

  const copy = useCallback(async (text, idx) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(idx);
      setTimeout(() => setCopied(null), 2000);
    } catch {}
  }, []);

  const retry = useCallback(() => {
    setError(null);
    send(lastQuestionRef.current);
  }, [send]);

  const clearChat = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return (
    <div className="agent-qa">
      <div className="agent-header">
        <div className="agent-header-row">
          <div>
            <h2>🤖 Ask Agent</h2>
            <p className="agent-desc">
              Ask any question about Team USA Olympic and Paralympic athletes,
              geographic distribution, and trends.
            </p>
          </div>
          {messages.length > 0 && (
            <button className="agent-clear-btn" onClick={clearChat} aria-label="Clear chat">
              Clear chat
            </button>
          )}
        </div>
      </div>

      <div className="agent-body" role="log" aria-live="polite" aria-label="Conversation">
        {messages.length === 0 && !loading && (
          <div className="agent-suggestions">
            <p className="agent-suggestions-label">Try asking:</p>
            <div className="agent-suggestions-grid">
              {SUGGESTED.map((q, i) => (
                <button
                  key={i}
                  className="agent-suggestion-btn"
                  onClick={() => send(q)}
                  aria-label={`Suggested question: ${q}`}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`agent-msg agent-msg--${msg.role}`}>
            <div className="agent-bubble">
              <div className="agent-bubble-text">{msg.content}</div>
              {msg.role === 'agent' && (
                <div className="agent-bubble-footer">
                  {msg.sources?.length > 0 && (
                    <div className="agent-sources">
                      <span className="agent-sources-label">Sources:</span>{' '}
                      {msg.sources.join(' · ')}
                    </div>
                  )}
                  <button
                    className="agent-copy-btn"
                    onClick={() => copy(msg.content, i)}
                    aria-label="Copy response to clipboard"
                  >
                    {copied === i ? '✅ Copied' : '📋 Copy'}
                  </button>
                </div>
              )}
            </div>
            <div className="agent-ts" aria-label={`Sent at ${fmtTime(msg.ts)}`}>
              {fmtTime(msg.ts)}
            </div>
          </div>
        ))}

        {loading && (
          <div className="agent-msg agent-msg--agent" aria-label="Agent is analyzing">
            <div className="agent-bubble agent-bubble--loading">
              <span className="agent-spinner" aria-hidden="true" />
              Agent is analyzing…
            </div>
          </div>
        )}

        {error && (
          <div className="agent-error-row" role="alert">
            <span className="agent-error-text">{error}</span>
            <button className="agent-retry-btn" onClick={retry}>Retry</button>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <form className="agent-form" onSubmit={handleSubmit}>
        <input
          className="agent-input"
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Ask me anything about Team USA athletes..."
          disabled={loading}
          aria-label="Ask a question about Team USA athletes"
        />
        <button
          className="agent-send-btn"
          type="submit"
          disabled={loading || !input.trim()}
          aria-label="Send message"
        >
          {loading ? '…' : 'Send'}
        </button>
      </form>
    </div>
  );
}
