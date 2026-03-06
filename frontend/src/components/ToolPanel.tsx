// Tool calls and responses panel with modern styling
import React from 'react';
import type { ToolCallEntry } from '../types';

interface ToolPanelProps {
  toolCalls: ToolCallEntry[];
}

// Icon components for tool states
const ToolIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
  </svg>
);

const CheckIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
);

const SpinnerIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ animation: 'spin 1s linear infinite' }}>
    <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
  </svg>
);

export const ToolPanel: React.FC<ToolPanelProps> = ({ toolCalls }) => {
  const formatTimestamp = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const formatJson = (obj: unknown) => {
    try {
      return JSON.stringify(obj, null, 2);
    } catch {
      return String(obj);
    }
  };

  if (toolCalls.length === 0) {
    return (
      <div className="tool-panel">
        <h3>
          <ToolIcon />
          Tool Calls
        </h3>
        <div className="empty-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.3, marginBottom: '1rem' }}>
            <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
          </svg>
          <p>No tool calls yet</p>
          <p style={{ fontSize: '0.75rem', marginTop: '0.5rem' }}>
            Tool invocations will appear here
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="tool-panel">
      <h3>
        <ToolIcon />
        Tool Calls ({toolCalls.length})
      </h3>
      <div className="tool-list">
        {toolCalls.map((tc) => (
          <div
            key={tc.id}
            className={`tool-item ${tc.isProcessing ? 'processing' : 'completed'}`}
          >
            <div className="tool-header">
              <span className="tool-name">{tc.name}</span>
              {tc.isProcessing ? (
                <span className="processing-badge">
                  <SpinnerIcon />
                  Processing
                </span>
              ) : (
                <span
                  className="completed-badge"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.25rem',
                    fontSize: '0.6875rem',
                    fontWeight: 600,
                    padding: '0.25rem 0.625rem',
                    background: 'rgba(16, 185, 129, 0.2)',
                    color: '#10b981',
                    borderRadius: '9999px',
                  }}
                >
                  <CheckIcon />
                  Completed
                </span>
              )}
              <span className="tool-time">{formatTimestamp(tc.timestamp)}</span>
            </div>

            <div className="tool-args">
              <span className="label">Arguments</span>
              <pre>{formatJson(tc.args)}</pre>
            </div>

            {tc.response !== undefined && (
              <div className="tool-response">
                <span className="label">
                  Response
                  {tc.responseTimestamp && (
                    <span style={{ marginLeft: '0.5rem', opacity: 0.7 }}>
                      ({formatTimestamp(tc.responseTimestamp)})
                    </span>
                  )}
                </span>
                <pre>{formatJson(tc.response)}</pre>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Add keyframe for spinner */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};
