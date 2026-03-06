// Session information display with modern styling
import React, { useState } from 'react';
import type { ConnectionState, SessionState } from '../types';

interface SessionInfoProps {
  connectionState: ConnectionState;
  sessionState: SessionState;
  onConnect: () => void;
  onDisconnect: () => void;
}

// Status configuration for different connection states
const STATUS_CONFIG = {
  connected: {
    color: '#22c55e',
    label: 'Connected',
  },
  connecting: {
    color: '#f59e0b',
    label: 'Connecting...',
  },
  error: {
    color: '#ef4444',
    label: 'Error',
  },
  disconnected: {
    color: '#555',
    label: 'Disconnected',
  },
};

export const SessionInfo: React.FC<SessionInfoProps> = ({
  connectionState,
  sessionState,
  onConnect,
  onDisconnect,
}) => {
  const [copied, setCopied] = useState(false);
  const status = STATUS_CONFIG[connectionState] || STATUS_CONFIG.disconnected;

  // Copy session ID to clipboard
  const handleCopySessionId = async () => {
    if (sessionState.sessionId) {
      try {
        await navigator.clipboard.writeText(sessionState.sessionId);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      } catch (err) {
        console.error('Failed to copy session ID:', err);
      }
    }
  };

  return (
    <div className="session-info">
      <div className="connection-status">
        <span
          className="status-dot"
          style={{
            backgroundColor: status.color,
          }}
        />
        <span className="status-text" style={{ color: status.color }}>
          {status.label}
        </span>
        {connectionState === 'disconnected' && (
          <button className="btn btn-small" onClick={onConnect}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M5 12h14"/>
              <path d="m12 5 7 7-7 7"/>
            </svg>
            Connect
          </button>
        )}
        {connectionState === 'connected' && (
          <button className="btn btn-small btn-secondary" onClick={onDisconnect}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 6 6 18"/>
              <path d="m6 6 12 12"/>
            </svg>
            Disconnect
          </button>
        )}
      </div>

      {sessionState.sessionId && (
        <div className="session-details">
          <span className="label">Session:</span>
          <span
            className="value"
            style={{
              fontFamily: 'monospace',
              fontSize: '12px',
              wordBreak: 'break-all',
            }}
          >
            {sessionState.sessionId}
          </span>
          <button
            onClick={handleCopySessionId}
            title="Copy session ID"
            style={{
              background: 'transparent',
              border: '1px solid #222',
              borderRadius: '4px',
              padding: '4px 6px',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginLeft: '8px',
              color: '#e5e5e5',
              transition: 'background-color 0.15s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = '#222';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
            }}
          >
            {copied ? (
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#22c55e"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polyline points="20 6 9 17 4 12" />
              </svg>
            ) : (
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
              </svg>
            )}
          </button>
          {copied && (
            <span
              style={{
                marginLeft: '6px',
                fontSize: '11px',
                color: '#22c55e',
              }}
            >
              Copied!
            </span>
          )}
        </div>
      )}

      {sessionState.model && (
        <div className="session-details">
          <span className="label">Model:</span>
          <span className="value">{sessionState.model}</span>
        </div>
      )}
    </div>
  );
};

// Re-export types for convenience
export type { ConnectionState } from '../services/wsService';
