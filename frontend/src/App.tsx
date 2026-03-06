// Main application component with modern UI
import { useState, useCallback, useEffect, useRef } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { useAudio } from './hooks/useAudio';
import { useJitterBuffer } from './hooks/useJitterBuffer';
import { AudioControls } from './components/AudioControls';
import { SessionInfo } from './components/SessionInfo';
import { VADSettings } from './components/VADSettings';
import { SystemEditor } from './components/SystemEditor';
import { ToolPanel } from './components/ToolPanel';
import { TranscriptPanel } from './components/TranscriptPanel';
import { ConfigPanel } from './components/ConfigPanel';
import type { VADSettings as VADSettingsType, EndpointMode } from './types';
import { DEFAULT_VAD_SETTINGS, DEFAULT_ENDPOINT_MODE } from './types';
import './App.css';

function App() {
  // WebSocket state and actions
  const {
    connectionState,
    sessionState,
    transcripts,
    toolCalls,
    error,
    initConfig,
    connect,
    disconnect,
    startSession,
    stopSession,
    sendAudio,
    setOnAudioResponse,
    setOnInterrupted,
  } = useWebSocket();

  // Local state for settings (editable before session starts)
  const [vadSettings, setVadSettings] = useState<VADSettingsType>(DEFAULT_VAD_SETTINGS);
  const [systemInstruction, setSystemInstruction] = useState('');
  const [voiceName] = useState('Aoede');
  const [endpointMode, setEndpointMode] = useState<EndpointMode>(DEFAULT_ENDPOINT_MODE);
  const [dismissedError, setDismissedError] = useState(false);

  // Jitter buffer for smooth audio playback
  const jitterBuffer = useJitterBuffer();

  // Audio recording hook
  const audio = useAudio({
    sampleRate: 16000,
    chunkMs: 25,
    onAudioChunk: sendAudio,
  });

  // Settings are disabled during active session
  const settingsDisabled = sessionState.isConnected || sessionState.isRecording;

  // Connect audio responses to jitter buffer (use ref to avoid dependency issues)
  const jitterBufferRef = useRef(jitterBuffer);
  jitterBufferRef.current = jitterBuffer;

  useEffect(() => {
    setOnAudioResponse((data: string) => {
      jitterBufferRef.current.addAudio(data);
    });
    return () => setOnAudioResponse(null);
  }, [setOnAudioResponse]);

  // Clear jitter buffer when model response is interrupted (user spoke during playback)
  useEffect(() => {
    setOnInterrupted(() => {
      console.log('Interrupt received: clearing jitter buffer');
      jitterBufferRef.current.clear();
    });
    return () => setOnInterrupted(null);
  }, [setOnInterrupted]);

  // Handle start session
  const handleStart = useCallback(async () => {
    // Start audio recording first
    const started = await audio.startRecording();
    if (started) {
      // Then start the session with current settings
      startSession(
        systemInstruction || undefined,
        vadSettings,
        voiceName,
        endpointMode
      );
    }
  }, [audio, startSession, systemInstruction, vadSettings, voiceName, endpointMode]);

  // Handle stop session
  const handleStop = useCallback(() => {
    audio.stopRecording();
    stopSession();
    jitterBuffer.clear();
  }, [audio, stopSession, jitterBuffer]);

  // Handle error dismiss
  const handleDismissError = useCallback(() => {
    setDismissedError(true);
  }, []);

  // Reset dismissed error when new error occurs
  useEffect(() => {
    if (error) {
      setDismissedError(false);
    }
  }, [error]);

  // Auto-connect on mount
  useEffect(() => {
    connect();
  }, [connect]);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Lenskart Voice Assistant</h1>
        <SessionInfo
          connectionState={connectionState}
          sessionState={sessionState}
          onConnect={connect}
          onDisconnect={disconnect}
        />
      </header>

      {error && !dismissedError && (
        <div className="error-banner">
          <span>{error}</span>
          <button onClick={handleDismissError}>Dismiss</button>
        </div>
      )}

      <main className="app-main">
        <div className="left-panel">
          <AudioControls
            isConnected={connectionState === 'connected'}
            isRecording={sessionState.isRecording}
            isMuted={audio.isMuted}
            audioLevel={audio.audioLevel}
            onStart={handleStart}
            onStop={handleStop}
            onToggleMute={audio.toggleMute}
          />

          <div className="settings-section">
            {/* Endpoint Toggle */}
            <div className="endpoint-toggle">
              <label className="endpoint-label">Endpoint</label>
              <div className="endpoint-buttons">
                <button
                  className={`endpoint-btn ${endpointMode === 'PROD' ? 'active' : ''}`}
                  onClick={() => setEndpointMode('PROD')}
                  disabled={settingsDisabled}
                >
                  Prod
                </button>
                <button
                  className={`endpoint-btn ${endpointMode === 'AUTOPUSH' ? 'active' : ''}`}
                  onClick={() => setEndpointMode('AUTOPUSH')}
                  disabled={settingsDisabled}
                >
                  Autopush
                </button>
              </div>
              <span className="endpoint-hint">
                {endpointMode === 'PROD' ? 'Service Account' : 'Bearer Token'}
              </span>
            </div>

            <VADSettings
              settings={vadSettings}
              onChange={setVadSettings}
              disabled={settingsDisabled}
            />

            <SystemEditor
              value={systemInstruction}
              onChange={setSystemInstruction}
              disabled={settingsDisabled}
            />
          </div>

          <ConfigPanel config={initConfig} />
        </div>

        <div className="center-panel">
          <TranscriptPanel transcripts={transcripts} />
        </div>

        <div className="right-panel">
          <ToolPanel toolCalls={toolCalls} />
        </div>
      </main>

      <footer className="app-footer">
        <p>Powered by Gemini Live API on Vertex AI</p>
        {jitterBuffer.isPlaying && (
          <span className="playing-indicator">
            <span className="playing-dot"></span>
            Playing audio
          </span>
        )}
      </footer>
    </div>
  );
}

export default App;
