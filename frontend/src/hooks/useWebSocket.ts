// WebSocket hook for Voice Chatbot
import { useState, useCallback, useRef, useEffect } from 'react';
import type {
  ServerMessage,
  InitMessage,
  AudioMessage,
  VADSettings,
  EndpointMode,
  SessionState,
  TranscriptEntry,
  ToolCallEntry,
} from '../types';
import {
  WebSocketService,
  ConnectionState,
  getWebSocketUrl,
} from '../services/wsService';

interface UseWebSocketResult {
  // State
  connectionState: ConnectionState;
  sessionState: SessionState;
  transcripts: TranscriptEntry[];
  toolCalls: ToolCallEntry[];
  error: string | null;
  initConfig: Record<string, unknown> | null;

  // Actions
  connect: () => void;
  disconnect: () => void;
  startSession: (systemInstruction?: string, vadSettings?: VADSettings, voiceName?: string, endpointMode?: EndpointMode) => void;
  stopSession: () => void;
  sendAudio: (audioBase64: string) => void;
  setOnAudioResponse: (callback: ((data: string, ttfbMs?: number) => void) | null) => void;
  // Callback for when model response is interrupted (user spoke during model speech)
  setOnInterrupted: (callback: (() => void) | null) => void;
}

export function useWebSocket(): UseWebSocketResult {
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [sessionState, setSessionState] = useState<SessionState>({
    sessionId: null,
    isConnected: false,
    isRecording: false,
    isMuted: false,
    model: null,
  });
  const [transcripts, setTranscripts] = useState<TranscriptEntry[]>([]);
  const [toolCalls, setToolCalls] = useState<ToolCallEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [initConfig, setInitConfig] = useState<Record<string, unknown> | null>(null);

  const wsRef = useRef<WebSocketService | null>(null);
  const transcriptIdRef = useRef(0);
  const audioCallbackRef = useRef<((data: string, ttfbMs?: number) => void) | null>(null);
  // Callback for when model response is interrupted
  const interruptedCallbackRef = useRef<(() => void) | null>(null);

  // Handle incoming messages
  const handleMessage = useCallback((message: ServerMessage) => {
    switch (message.type) {
      case 'session_started':
        setSessionState((prev) => ({
          ...prev,
          sessionId: message.session_id,
          isConnected: true,
          model: message.model,
        }));
        setInitConfig(message.config);
        setError(null);
        break;

      case 'transcript':
        setTranscripts((prev) => {
          const lastEntry = prev.length > 0 ? prev[prev.length - 1] : null;

          // Check if we should aggregate with the last entry:
          // - Same role as incoming message
          // - Last entry is not marked as final (turn not complete)
          // Note: We ignore message.is_final - aggregation is controlled by role changes and turn_complete
          const shouldAggregate =
            lastEntry &&
            lastEntry.role === message.role &&
            !lastEntry.turnComplete;

          if (shouldAggregate) {
            // Append text to the existing entry
            const updated = [...prev];
            updated[updated.length - 1] = {
              ...lastEntry,
              text: lastEntry.text + ' ' + message.text,
              // Keep isFinal as false until turn_complete or role change
              isFinal: false,
              // Keep the first TTFB measurement for the turn
              ttfbMs: lastEntry.ttfbMs ?? message.ttfb_ms,
            };
            return updated;
          } else {
            // Role changed - mark the previous entry as final
            let updated = [...prev];
            if (lastEntry && lastEntry.role !== message.role) {
              updated[updated.length - 1] = {
                ...lastEntry,
                isFinal: true,
              };
            }

            // Create new entry for the new role (not final until turn_complete or role change)
            const id = `transcript-${++transcriptIdRef.current}`;
            const entry: TranscriptEntry = {
              id,
              role: message.role,
              text: message.text,
              timestamp: new Date(message.timestamp),
              isFinal: false,
              ttfbMs: message.ttfb_ms,
            };
            return [...updated, entry];
          }
        });
        break;

      case 'tool_call':
        setToolCalls((prev) => [
          ...prev,
          {
            id: message.id,
            name: message.name,
            args: message.args,
            timestamp: new Date(message.timestamp),
            isProcessing: true,
          },
        ]);
        break;

      case 'tool_response':
        setToolCalls((prev) =>
          prev.map((tc) =>
            tc.id === message.id
              ? {
                  ...tc,
                  response: message.response,
                  responseTimestamp: new Date(message.timestamp),
                  isProcessing: false,
                }
              : tc
          )
        );
        break;

      case 'interim_response':
        // Add interim response as a transcript (aggregated with existing model entry if applicable)
        setTranscripts((prev) => {
          const lastEntry = prev.length > 0 ? prev[prev.length - 1] : null;

          // Check if we should aggregate with the last model entry
          const shouldAggregate =
            lastEntry &&
            lastEntry.role === 'model' &&
            !lastEntry.turnComplete;

          if (shouldAggregate) {
            const updated = [...prev];
            updated[updated.length - 1] = {
              ...lastEntry,
              text: lastEntry.text + ' ' + message.message,
              isFinal: false,
            };
            return updated;
          } else {
            // Mark previous entry as final if it's a user entry (role change)
            let updated = [...prev];
            if (lastEntry && lastEntry.role === 'user') {
              updated[updated.length - 1] = {
                ...lastEntry,
                isFinal: true,
              };
            }

            const id = `interim-${++transcriptIdRef.current}`;
            return [
              ...updated,
              {
                id,
                role: 'model' as const,
                text: message.message,
                timestamp: new Date(),
                isFinal: false,
              },
            ];
          }
        });
        break;

      case 'turn_complete':
        // Mark the last entry as complete (regardless of role - applies to whoever just finished)
        setTranscripts((prev) => {
          if (prev.length === 0) return prev;
          const updated = [...prev];
          const lastIndex = updated.length - 1;
          updated[lastIndex] = {
            ...updated[lastIndex],
            turnComplete: true,
            isFinal: true,
          };
          return updated;
        });
        break;

      case 'session_ended':
        setSessionState((prev) => ({
          ...prev,
          isConnected: false,
          isRecording: false,
        }));
        break;

      case 'error':
        setError(message.error);
        console.error('Server error:', message.error, message.details);
        break;

      case 'audio_response':
        // Handle audio response from model - emit event for jitter buffer
        console.log('Received audio response, TTFB:', message.ttfb_ms);
        // Audio will be handled by onAudioResponse callback
        if (audioCallbackRef.current) {
          audioCallbackRef.current(message.data, message.ttfb_ms);
        }
        break;

      case 'interrupted':
        // Signal that model was interrupted (for audio buffer management)
        // Invoke callback to clear audio buffer immediately
        console.log('Model response interrupted');
        if (interruptedCallbackRef.current) {
          interruptedCallbackRef.current();
        }
        break;
    }
  }, []);

  // Handle connection state changes - clear error on successful connection
  const handleStateChange = useCallback((state: ConnectionState) => {
    setConnectionState(state);
    // Clear error when successfully connected
    if (state === 'connected') {
      setError(null);
    }
  }, []);

  // Initialize WebSocket service
  useEffect(() => {
    wsRef.current = new WebSocketService({
      url: getWebSocketUrl(),
      onMessage: handleMessage,
      onStateChange: handleStateChange,
      onError: (err) => setError(err.message),
    });

    return () => {
      wsRef.current?.disconnect();
    };
  }, [handleMessage, handleStateChange]);

  // Connect to WebSocket server
  const connect = useCallback(() => {
    wsRef.current?.connect();
  }, []);

  // Disconnect from WebSocket server
  const disconnect = useCallback(() => {
    wsRef.current?.disconnect();
    setSessionState({
      sessionId: null,
      isConnected: false,
      isRecording: false,
      isMuted: false,
      model: null,
    });
    setTranscripts([]);
    setToolCalls([]);
    setInitConfig(null);
  }, []);

  // Start a new session
  const startSession = useCallback(
    (systemInstruction?: string, vadSettings?: VADSettings, voiceName?: string, endpointMode?: EndpointMode) => {
      const initMessage: InitMessage = {
        type: 'init',
        system_instruction: systemInstruction,
        vad_settings: vadSettings,
        voice_name: voiceName,
        endpoint_mode: endpointMode,
      };
      wsRef.current?.send(initMessage);
      setSessionState((prev) => ({ ...prev, isRecording: true }));
    },
    []
  );

  // Stop the current session
  const stopSession = useCallback(() => {
    wsRef.current?.send({ type: 'stop' });
    setSessionState((prev) => ({ ...prev, isRecording: false }));
  }, []);

  // Send audio data
  const sendAudio = useCallback((audioBase64: string) => {
    const audioMessage: AudioMessage = {
      type: 'audio',
      data: audioBase64,
    };
    wsRef.current?.send(audioMessage);
  }, []);

  // Set callback for audio responses
  const setOnAudioResponse = useCallback(
    (callback: ((data: string, ttfbMs?: number) => void) | null) => {
      audioCallbackRef.current = callback;
    },
    []
  );

  // Set callback for when model response is interrupted
  const setOnInterrupted = useCallback(
    (callback: (() => void) | null) => {
      interruptedCallbackRef.current = callback;
    },
    []
  );

  return {
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
  };
}
