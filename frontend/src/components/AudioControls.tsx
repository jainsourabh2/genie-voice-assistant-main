// Audio control buttons with waveform visualization
import React, { useMemo } from 'react';

interface AudioControlsProps {
  isConnected: boolean;
  isRecording: boolean;
  isMuted: boolean;
  audioLevel: number;
  onStart: () => void;
  onStop: () => void;
  onToggleMute: () => void;
  disabled?: boolean;
}

// Generate waveform bar heights based on audio level
const generateWaveformHeights = (audioLevel: number, barCount: number): number[] => {
  const baseHeight = 8;
  const maxHeight = 40;
  const heights: number[] = [];

  for (let i = 0; i < barCount; i++) {
    // Create variation in heights with some randomness influenced by audio level
    const variation = Math.sin(i * 0.8 + Date.now() * 0.005) * 0.5 + 0.5;
    const levelFactor = audioLevel * variation;
    const height = baseHeight + (maxHeight - baseHeight) * levelFactor;
    heights.push(Math.max(baseHeight, Math.min(maxHeight, height)));
  }

  return heights;
};

export const AudioControls: React.FC<AudioControlsProps> = ({
  isConnected,
  isRecording,
  isMuted,
  audioLevel,
  onStart,
  onStop,
  onToggleMute,
  disabled = false,
}) => {
  // Generate waveform heights (10 bars)
  const waveformHeights = useMemo(
    () => generateWaveformHeights(audioLevel, 10),
    [audioLevel]
  );

  return (
    <div className="audio-controls">
      {/* Recording indicator */}
      {isRecording && (
        <div className="recording-indicator">
          <span className="recording-dot"></span>
          <span>Recording</span>
        </div>
      )}

      {/* Waveform visualization */}
      {isRecording && (
        <div className="audio-waveform">
          {waveformHeights.map((height, index) => (
            <div
              key={index}
              className={`waveform-bar ${!isMuted ? 'active' : ''}`}
              style={{
                height: isMuted ? '8px' : `${height}px`,
                opacity: isMuted ? 0.3 : 1,
              }}
            />
          ))}
        </div>
      )}

      {/* Control buttons */}
      <div className="control-buttons">
        {!isRecording ? (
          <button
            className="btn btn-start"
            onClick={onStart}
            disabled={disabled || !isConnected}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
              <line x1="12" x2="12" y1="19" y2="22"/>
            </svg>
            Start Session
          </button>
        ) : (
          <button className="btn btn-stop" onClick={onStop} disabled={disabled}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect width="14" height="14" x="5" y="5" rx="2"/>
            </svg>
            Stop Session
          </button>
        )}

        <button
          className={`btn btn-mute ${isMuted ? 'muted' : ''}`}
          onClick={onToggleMute}
          disabled={!isRecording || disabled}
        >
          {isMuted ? (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="2" x2="22" y1="2" y2="22"/>
              <path d="M18.89 13.23A7.12 7.12 0 0 0 19 12v-2"/>
              <path d="M5 10v2a7 7 0 0 0 12 5"/>
              <path d="M15 9.34V5a3 3 0 0 0-5.68-1.33"/>
              <path d="M9 9v3a3 3 0 0 0 5.12 2.12"/>
              <line x1="12" x2="12" y1="19" y2="22"/>
            </svg>
          ) : (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
              <line x1="12" x2="12" y1="19" y2="22"/>
            </svg>
          )}
          {isMuted ? 'Unmute' : 'Mute'}
        </button>
      </div>

      {/* Audio level bar */}
      {isRecording && (
        <div className="audio-level">
          <div
            className="level-bar"
            style={{
              width: `${Math.min(audioLevel * 100, 100)}%`,
              opacity: isMuted ? 0.3 : 1,
            }}
          />
        </div>
      )}
    </div>
  );
};
