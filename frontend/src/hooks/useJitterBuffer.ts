// Jitter buffer for smooth audio playback
import { useState, useRef, useCallback, useEffect } from 'react';
import { base64ToArrayBuffer, pcm16ToFloat32 } from '../services/audioService';
import { DEFAULT_AUDIO_CONFIG } from '../types';

interface JitterBufferConfig {
  targetLatencyMs: number; // Target buffer size in ms (100-150ms recommended)
  sampleRate: number;
}

interface UseJitterBufferResult {
  // Add audio to buffer
  addAudio: (base64Data: string) => void;
  // Clear buffer (on interruption)
  clear: () => void;
  // Get buffer status
  bufferLengthMs: number;
  isPlaying: boolean;
}

export function useJitterBuffer(
  config: JitterBufferConfig = {
    targetLatencyMs: 120,
    sampleRate: DEFAULT_AUDIO_CONFIG.outputSampleRate,
  }
): UseJitterBufferResult {
  const [bufferLengthMs, setBufferLengthMs] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  const audioContextRef = useRef<AudioContext | null>(null);
  const bufferQueueRef = useRef<Float32Array[]>([]);
  const nextPlayTimeRef = useRef(0);
  const isSchedulingRef = useRef(false);

  // Initialize AudioContext lazily
  const getAudioContext = useCallback(() => {
    if (!audioContextRef.current) {
      audioContextRef.current = new AudioContext({
        sampleRate: config.sampleRate,
      });
    }
    return audioContextRef.current;
  }, [config.sampleRate]);

  // Schedule audio playback
  const schedulePlayback = useCallback(() => {
    if (isSchedulingRef.current) return;
    isSchedulingRef.current = true;

    const ctx = getAudioContext();
    const queue = bufferQueueRef.current;

    // Wait until we have enough buffer
    const totalSamples = queue.reduce((sum, chunk) => sum + chunk.length, 0);
    const bufferedMs = (totalSamples / config.sampleRate) * 1000;
    setBufferLengthMs(bufferedMs);

    if (bufferedMs < config.targetLatencyMs && queue.length < 3) {
      isSchedulingRef.current = false;
      return;
    }

    setIsPlaying(true);

    // Schedule chunks for playback
    while (queue.length > 0) {
      const chunk = queue.shift()!;
      const buffer = ctx.createBuffer(1, chunk.length, config.sampleRate);
      buffer.getChannelData(0).set(chunk);

      const source = ctx.createBufferSource();
      source.buffer = buffer;
      source.connect(ctx.destination);

      const playTime = Math.max(ctx.currentTime, nextPlayTimeRef.current);
      source.start(playTime);
      nextPlayTimeRef.current = playTime + buffer.duration;

      source.onended = () => {
        // Check if more audio to play
        if (queue.length === 0) {
          setIsPlaying(false);
        }
      };
    }

    isSchedulingRef.current = false;
  }, [config.sampleRate, config.targetLatencyMs, getAudioContext]);

  // Add audio chunk to buffer
  const addAudio = useCallback(
    (base64Data: string) => {
      const pcmBuffer = base64ToArrayBuffer(base64Data);
      const samples = pcm16ToFloat32(pcmBuffer);
      bufferQueueRef.current.push(samples);

      // Schedule playback
      schedulePlayback();
    },
    [schedulePlayback]
  );

  // Clear buffer (on interruption)
  const clear = useCallback(() => {
    bufferQueueRef.current = [];
    nextPlayTimeRef.current = 0;
    setBufferLengthMs(0);
    setIsPlaying(false);

    // Stop any scheduled audio
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, []);

  return {
    addAudio,
    clear,
    bufferLengthMs,
    isPlaying,
  };
}
