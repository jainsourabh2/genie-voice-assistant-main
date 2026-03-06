// TypeScript interfaces for Voice Chatbot

// Connection state type
export type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error';

export type MessageType =
  | 'init'
  | 'audio'
  | 'stop'
  | 'session_started'
  | 'transcript'
  | 'audio_response'
  | 'tool_call'
  | 'tool_response'
  | 'interim_response'
  | 'turn_complete'
  | 'error'
  | 'session_ended'
  | 'interrupted';

export type StartSensitivity = 'HIGH' | 'LOW' | 'UNSPECIFIED';
export type EndSensitivity = 'HIGH' | 'LOW' | 'UNSPECIFIED';

// Endpoint mode for switching between Autopush (sandbox) and Production
export type EndpointMode = 'AUTOPUSH' | 'PROD';

export interface VADSettings {
  /** If true, disables automatic activity detection - client must send activity signals */
  disabled?: boolean;
  /** Determines how likely speech is to be detected */
  start_sensitivity: StartSensitivity;
  /** Determines how likely detected speech is ended */
  end_sensitivity: EndSensitivity;
  /** Duration in ms of detected speech before start-of-speech is committed (lower = more sensitive, but more false positives) */
  prefix_padding_ms?: number;
  /** Duration in ms of silence before end-of-speech is committed (higher = longer gaps allowed, but more latency) */
  silence_duration_ms?: number;
}

export interface InitMessage {
  type: 'init';
  system_instruction?: string;
  vad_settings?: VADSettings;
  voice_name?: string;
  endpoint_mode?: EndpointMode;
}

export interface AudioMessage {
  type: 'audio';
  data: string; // Base64 encoded PCM
}

export interface StopMessage {
  type: 'stop';
}

export interface SessionStartedMessage {
  type: 'session_started';
  session_id: string;
  model: string;
  config: Record<string, unknown>;
}

export interface TranscriptMessage {
  type: 'transcript';
  role: 'user' | 'model';
  text: string;
  timestamp: string;
  is_final: boolean;
  ttfb_ms?: number;
}

export interface AudioResponseMessage {
  type: 'audio_response';
  data: string; // Base64 encoded PCM
  ttfb_ms?: number;
}

export interface ToolCallMessage {
  type: 'tool_call';
  id: string;
  name: string;
  args: Record<string, unknown>;
  timestamp: string;
}

export interface ToolResponseMessage {
  type: 'tool_response';
  id: string;
  name: string;
  response: unknown;
  timestamp: string;
}

export interface InterimResponseMessage {
  type: 'interim_response';
  message: string;
  tool_name: string;
}

export interface TurnCompleteMessage {
  type: 'turn_complete';
  timestamp: string;
}

export interface SessionEndedMessage {
  type: 'session_ended';
  session_id: string;
}

export interface ErrorMessage {
  type: 'error';
  error: string;
  details?: string;
}

export interface InterruptedMessage {
  type: 'interrupted';
  timestamp: string;
}

export type ServerMessage =
  | SessionStartedMessage
  | TranscriptMessage
  | AudioResponseMessage
  | ToolCallMessage
  | ToolResponseMessage
  | InterimResponseMessage
  | TurnCompleteMessage
  | SessionEndedMessage
  | ErrorMessage
  | InterruptedMessage;

export type ClientMessage = InitMessage | AudioMessage | StopMessage;

// Session state
export interface SessionState {
  sessionId: string | null;
  isConnected: boolean;
  isRecording: boolean;
  isMuted: boolean;
  model: string | null;
}

// Transcript entry for display
export interface TranscriptEntry {
  id: string;
  role: 'user' | 'model';
  text: string;
  timestamp: Date;
  isFinal: boolean;
  ttfbMs?: number;
  turnComplete?: boolean;
}

// Tool call entry for display
export interface ToolCallEntry {
  id: string;
  name: string;
  args: Record<string, unknown>;
  timestamp: Date;
  response?: unknown;
  responseTimestamp?: Date;
  isProcessing: boolean;
}

// Audio configuration
export interface AudioConfig {
  inputSampleRate: number;
  outputSampleRate: number;
  channels: number;
  bitsPerSample: number;
}

export const DEFAULT_AUDIO_CONFIG: AudioConfig = {
  inputSampleRate: 16000,
  outputSampleRate: 24000,
  channels: 1,
  bitsPerSample: 16,
};

export const DEFAULT_VAD_SETTINGS: VADSettings = {
  disabled: false,
  start_sensitivity: 'HIGH',
  end_sensitivity: 'HIGH',
  prefix_padding_ms: 300,
  silence_duration_ms: 800,
};

export const DEFAULT_ENDPOINT_MODE: EndpointMode = 'PROD';
