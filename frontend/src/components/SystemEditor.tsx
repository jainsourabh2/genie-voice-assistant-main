// System instructions editor with modern styling
import React from 'react';

interface SystemEditorProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

// Code/terminal icon
const CodeIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="16 18 22 12 16 6"/>
    <polyline points="8 6 2 12 8 18"/>
  </svg>
);

// Lock icon for disabled state
const LockIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect width="18" height="11" x="3" y="11" rx="2" ry="2"/>
    <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
  </svg>
);

export const SystemEditor: React.FC<SystemEditorProps> = ({
  value,
  onChange,
  disabled = false,
}) => {
  const charCount = value.length;
  const maxChars = 4000;

  return (
    <div className="system-editor">
      <h3>
        <CodeIcon />
        System Instructions
      </h3>
      <div style={{ position: 'relative' }}>
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          placeholder="Enter custom system instructions (optional)..."
          rows={6}
          maxLength={maxChars}
        />
        {!disabled && (
          <div style={{
            position: 'absolute',
            bottom: '0.5rem',
            right: '0.75rem',
            fontSize: '0.6875rem',
            color: charCount > maxChars * 0.9 ? '#f59e0b' : '#64748b',
            background: 'rgba(0, 0, 0, 0.5)',
            padding: '0.125rem 0.375rem',
            borderRadius: '4px',
          }}>
            {charCount} / {maxChars}
          </div>
        )}
      </div>
      {disabled && (
        <p className="hint">
          <LockIcon />
          <span style={{ marginLeft: '0.375rem' }}>
            Cannot be edited during active session
          </span>
        </p>
      )}
      {!disabled && !value && (
        <p style={{
          fontSize: '0.75rem',
          color: '#64748b',
          marginTop: '0.5rem',
        }}>
          Customize how the assistant behaves during the conversation
        </p>
      )}
    </div>
  );
};
