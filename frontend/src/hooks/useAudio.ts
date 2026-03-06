// Audio recording hook for Voice Chatbot
import { useState, useRef, useCallback, useEffect } from 'react';
import {
  float32ToPcm16,
  arrayBufferToBase64,
  getOptimalChunkSize,
} from '../services/audioService';
import { DEFAULT_AUDIO_CONFIG } from '../types';

interface UseAudioConfig {
  sampleRate: number;
  chunkMs: number; // Target chunk duration (20-40ms)
  onAudioChunk: (base64: string) => void;
}

interface UseAudioResult {
  isRecording: boolean;
  isMuted: boolean;
  audioLevel: number;
  startRecording: () => Promise<boolean>;
  stopRecording: () => void;
  toggleMute: () => void;
  error: string | null;
}

export function useAudio(
  config: UseAudioConfig = {
    sampleRate: DEFAULT_AUDIO_CONFIG.inputSampleRate,
    chunkMs: 25,
    onAudioChunk: () => {},
  }
): UseAudioResult {
  const [isRecording, setIsRecording] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const audioContextRef = useRef<AudioContext | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunkBufferRef = useRef<Float32Array[]>([]);

  // Calculate optimal chunk size for audio processing
  const _chunkSize = getOptimalChunkSize(config.chunkMs, config.sampleRate);
  void _chunkSize; // Used for reference, actual chunking done in processAudioChunks

  // Process accumulated audio chunks
  const processAudioChunks = useCallback(() => {
    const buffer = chunkBufferRef.current;
    if (buffer.length === 0) return;

    // Combine chunks
    const totalLength = buffer.reduce((sum, chunk) => sum + chunk.length, 0);
    const combined = new Float32Array(totalLength);
    let offset = 0;
    for (const chunk of buffer) {
      combined.set(chunk, offset);
      offset += chunk.length;
    }
    chunkBufferRef.current = [];

    // Convert to PCM and send
    const pcmBuffer = float32ToPcm16(combined);
    const base64 = arrayBufferToBase64(pcmBuffer);
    config.onAudioChunk(base64);

    // Calculate audio level
    let sum = 0;
    for (let i = 0; i < combined.length; i++) {
      sum += Math.abs(combined[i]);
    }
    setAudioLevel(sum / combined.length);
  }, [config]);

  // Start recording
  const startRecording = useCallback(async (): Promise<boolean> => {
    try {
      setError(null);

      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: config.sampleRate,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      streamRef.current = stream;

      // Create AudioContext
      const ctx = new AudioContext({ sampleRate: config.sampleRate });
      audioContextRef.current = ctx;

      // Create source from stream
      sourceNodeRef.current = ctx.createMediaStreamSource(stream);

      // Use ScriptProcessor for audio processing (AudioWorklet would be better but requires more setup)
      const bufferSize = 4096;
      const scriptProcessor = ctx.createScriptProcessor(bufferSize, 1, 1);

      let samplesCollected = 0;
      const targetSamples = Math.floor((config.sampleRate * config.chunkMs) / 1000);

      scriptProcessor.onaudioprocess = (event) => {
        if (isMuted) return;

        const inputData = event.inputBuffer.getChannelData(0);
        chunkBufferRef.current.push(new Float32Array(inputData));
        samplesCollected += inputData.length;

        // Send chunk when we have enough samples
        if (samplesCollected >= targetSamples) {
          processAudioChunks();
          samplesCollected = 0;
        }
      };

      sourceNodeRef.current.connect(scriptProcessor);
      scriptProcessor.connect(ctx.destination);

      setIsRecording(true);
      console.log('Recording started');
      return true;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to start recording';
      setError(message);
      console.error('Failed to start recording:', err);
      return false;
    }
  }, [config.sampleRate, config.chunkMs, isMuted, processAudioChunks]);

  // Stop recording
  const stopRecording = useCallback(() => {
    // Stop media stream tracks
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    // Close AudioContext
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    sourceNodeRef.current = null;
    workletNodeRef.current = null;
    chunkBufferRef.current = [];

    setIsRecording(false);
    setAudioLevel(0);
    console.log('Recording stopped');
  }, []);

  // Toggle mute
  const toggleMute = useCallback(() => {
    setIsMuted((prev) => !prev);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, []);

  return {
    isRecording,
    isMuted,
    audioLevel,
    startRecording,
    stopRecording,
    toggleMute,
    error,
  };
}
