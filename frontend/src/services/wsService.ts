// WebSocket service for Voice Chatbot
import type { ClientMessage, ServerMessage } from '../types';

export type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error';

export interface WebSocketConfig {
  url: string;
  onMessage: (message: ServerMessage) => void;
  onStateChange: (state: ConnectionState) => void;
  onError: (error: Error) => void;
}

export class WebSocketService {
  private ws: WebSocket | null = null;
  private config: WebSocketConfig;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 3;
  private reconnectDelay = 1000;

  constructor(config: WebSocketConfig) {
    this.config = config;
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    this.config.onStateChange('connecting');

    try {
      this.ws = new WebSocket(this.config.url);
      this.ws.binaryType = 'arraybuffer';

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        this.config.onStateChange('connected');
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as ServerMessage;
          try {
            this.config.onMessage(message);
          } catch (handlerError) {
            console.error('Error in message handler:', handlerError, 'Message:', message);
          }
        } catch (parseError) {
          console.error('Failed to parse message:', parseError);
        }
      };

      this.ws.onerror = (event) => {
        console.error('WebSocket error:', event);
        // Only report error if not already connected
        if (this.ws?.readyState !== WebSocket.OPEN) {
          this.config.onError(new Error('WebSocket connection error'));
          this.config.onStateChange('error');
        }
      };

      this.ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        this.config.onStateChange('disconnected');
        this.ws = null;

        // Attempt reconnection if not a clean close
        if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++;
          console.log(`Reconnecting (attempt ${this.reconnectAttempts})...`);
          setTimeout(() => this.connect(), this.reconnectDelay * this.reconnectAttempts);
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      this.config.onError(error as Error);
      this.config.onStateChange('error');
    }
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
    this.config.onStateChange('disconnected');
  }

  send(message: ClientMessage): boolean {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.error('Cannot send: WebSocket not connected');
      return false;
    }

    try {
      this.ws.send(JSON.stringify(message));
      return true;
    } catch (error) {
      console.error('Failed to send message:', error);
      return false;
    }
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  get readyState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED;
  }
}

// Default WebSocket URL
export const getWebSocketUrl = (): string => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.hostname;
  // In development, connect directly to backend port
  const port = import.meta.env.DEV ? '8765' : window.location.port;
  // Backend accepts connections on root path
  return `${protocol}//${host}:${port}`;
};
