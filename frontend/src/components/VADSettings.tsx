// VAD (Voice Activity Detection) settings panel with full configuration options
import React from 'react';
import type { VADSettings as VADSettingsType, StartSensitivity, EndSensitivity } from '../types';

interface VADSettingsProps {
  settings: VADSettingsType;
  onChange: (settings: VADSettingsType) => void;
  disabled?: boolean;
}

// Microphone icon
const MicIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
    <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
    <line x1="12" x2="12" y1="19" y2="22"/>
  </svg>
);

// Lock icon for disabled state
const LockIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect width="18" height="11" x="3" y="11" rx="2" ry="2"/>
    <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
  </svg>
);

// Info icon
const InfoIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <path d="M12 16v-4"/>
    <path d="M12 8h.01"/>
  </svg>
);

export const VADSettings: React.FC<VADSettingsProps> = ({
  settings,
  onChange,
  disabled = false,
}) => {
  const handleNumberChange = (field: 'prefix_padding_ms' | 'silence_duration_ms', value: string) => {
    const numValue = value === '' ? undefined : parseInt(value, 10);
    onChange({
      ...settings,
      [field]: isNaN(numValue as number) ? undefined : numValue,
    });
  };

  return (
    <div className="vad-settings">
      <h3>
        <MicIcon />
        Voice Activity Detection
      </h3>

      {/* Disabled toggle */}
      <div className="setting-row checkbox-row">
        <label htmlFor="vad-disabled" className="checkbox-label">
          <input
            type="checkbox"
            id="vad-disabled"
            checked={settings.disabled || false}
            onChange={(e) =>
              onChange({
                ...settings,
                disabled: e.target.checked,
              })
            }
            disabled={disabled}
          />
          <span className="checkbox-text">
            Manual Activity Control
            <span className="setting-hint">
              (disable automatic detection)
            </span>
          </span>
        </label>
      </div>

      {/* Start Sensitivity */}
      <div className="setting-row">
        <label htmlFor="start-sensitivity">
          Start Sensitivity
          <span className="setting-hint">
            (voice detection threshold)
          </span>
        </label>
        <select
          id="start-sensitivity"
          value={settings.start_sensitivity}
          onChange={(e) =>
            onChange({
              ...settings,
              start_sensitivity: e.target.value as StartSensitivity,
            })
          }
          disabled={disabled || settings.disabled}
        >
          <option value="HIGH">High - More responsive</option>
          <option value="LOW">Low - Less sensitive</option>
          <option value="UNSPECIFIED">Default (auto)</option>
        </select>
      </div>

      {/* End Sensitivity */}
      <div className="setting-row">
        <label htmlFor="end-sensitivity">
          End Sensitivity
          <span className="setting-hint">
            (pause detection threshold)
          </span>
        </label>
        <select
          id="end-sensitivity"
          value={settings.end_sensitivity}
          onChange={(e) =>
            onChange({
              ...settings,
              end_sensitivity: e.target.value as EndSensitivity,
            })
          }
          disabled={disabled || settings.disabled}
        >
          <option value="HIGH">High - Quick response</option>
          <option value="LOW">Low - Longer pauses allowed</option>
          <option value="UNSPECIFIED">Default (auto)</option>
        </select>
      </div>

      {/* Advanced Settings Divider */}
      <div className="setting-divider">
        <span>Advanced Timing</span>
      </div>

      {/* Prefix Padding */}
      <div className="setting-row">
        <label htmlFor="prefix-padding">
          Speech Start Delay
          <span className="setting-hint">
            <InfoIcon /> ms before speech commits
          </span>
        </label>
        <div className="input-with-unit">
          <input
            type="number"
            id="prefix-padding"
            value={settings.prefix_padding_ms ?? ''}
            onChange={(e) => handleNumberChange('prefix_padding_ms', e.target.value)}
            placeholder="Auto"
            min={0}
            max={2000}
            step={50}
            disabled={disabled || settings.disabled}
          />
          <span className="unit">ms</span>
        </div>
        <p className="setting-description">
          Lower values = faster detection, but more false positives
        </p>
      </div>

      {/* Silence Duration */}
      <div className="setting-row">
        <label htmlFor="silence-duration">
          Silence Duration
          <span className="setting-hint">
            <InfoIcon /> ms before speech ends
          </span>
        </label>
        <div className="input-with-unit">
          <input
            type="number"
            id="silence-duration"
            value={settings.silence_duration_ms ?? ''}
            onChange={(e) => handleNumberChange('silence_duration_ms', e.target.value)}
            placeholder="Auto"
            min={0}
            max={5000}
            step={100}
            disabled={disabled || settings.disabled}
          />
          <span className="unit">ms</span>
        </div>
        <p className="setting-description">
          Higher values = longer pauses allowed, but more latency
        </p>
      </div>

      {disabled && (
        <p className="hint">
          <LockIcon />
          <span style={{ marginLeft: '0.375rem' }}>
            Settings locked during active session
          </span>
        </p>
      )}
    </div>
  );
};
