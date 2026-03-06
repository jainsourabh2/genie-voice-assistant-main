// Conversation transcripts panel with modern styling
import React, { useEffect, useRef } from 'react';
import type { TranscriptEntry } from '../types';

interface TranscriptPanelProps {
  transcripts: TranscriptEntry[];
}

// Icon for conversation
const ChatIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
  </svg>
);

// User icon
const UserIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/>
    <circle cx="12" cy="7" r="4"/>
  </svg>
);

// Bot icon
const BotIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 8V4H8"/>
    <rect width="16" height="12" x="4" y="8" rx="2"/>
    <path d="M2 14h2"/>
    <path d="M20 14h2"/>
    <path d="M15 13v2"/>
    <path d="M9 13v2"/>
  </svg>
);

// Check icon for turn complete - prominent badge style
const TurnCompleteBadge = () => (
  <span className="turn-complete-badge" title="Turn complete">
    <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
      <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
    </svg>
    Done
  </span>
);

// Typing indicator for interim messages
const TypingIndicator = () => (
  <span className="typing-indicator" title="Speaking...">
    <span className="typing-dot"></span>
    <span className="typing-dot"></span>
    <span className="typing-dot"></span>
  </span>
);

export const TranscriptPanel: React.FC<TranscriptPanelProps> = ({ transcripts }) => {
  const listRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [transcripts]);

  const formatTimestamp = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  if (transcripts.length === 0) {
    return (
      <div className="transcript-panel">
        <h3>
          <ChatIcon />
          Conversation
        </h3>
        <div className="empty-state">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.2, marginBottom: '1rem' }}>
            <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
            <line x1="12" x2="12" y1="19" y2="22"/>
          </svg>
          <p>Start speaking to see transcriptions</p>
          <p style={{ fontSize: '0.75rem', marginTop: '0.5rem', maxWidth: '200px' }}>
            Your conversation will appear here in real-time
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="transcript-panel">
      <h3>
        <ChatIcon />
        Conversation ({transcripts.length})
      </h3>
      <div className="transcript-list" ref={listRef}>
        {transcripts.map((entry) => (
          <div
            key={entry.id}
            className={`transcript-item ${entry.role} ${entry.isFinal ? 'final' : 'interim'}`}
          >
            <div className="transcript-header">
              <span className="role">
                {entry.role === 'user' ? (
                  <>
                    <UserIcon />
                    You
                  </>
                ) : (
                  <>
                    <BotIcon />
                    Assistant
                  </>
                )}
              </span>
              <span className="timestamp">{formatTimestamp(entry.timestamp)}</span>
              {entry.ttfbMs != null && (
                <span className="ttfb" title="Time to first byte">
                  TTFB: {entry.ttfbMs.toFixed(0)}ms
                </span>
              )}
              {/* Show typing indicator for interim messages, turn complete badge for completed turns */}
              {!entry.isFinal && <TypingIndicator />}
              {entry.isFinal && entry.turnComplete && <TurnCompleteBadge />}
            </div>
            <div className="transcript-text">{entry.text}</div>
          </div>
        ))}
      </div>
    </div>
  );
};
