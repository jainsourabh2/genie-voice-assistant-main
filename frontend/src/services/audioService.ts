// Audio encoding/decoding service for Voice Chatbot
import { DEFAULT_AUDIO_CONFIG } from '../types';

// Convert ArrayBuffer to Base64
export function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

// Convert Base64 to ArrayBuffer
export function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes.buffer;
}

// Convert Float32 audio samples to 16-bit PCM
export function float32ToPcm16(samples: Float32Array): ArrayBuffer {
  const buffer = new ArrayBuffer(samples.length * 2);
  const view = new DataView(buffer);

  for (let i = 0; i < samples.length; i++) {
    // Clamp to [-1, 1]
    const sample = Math.max(-1, Math.min(1, samples[i]));
    // Convert to 16-bit signed integer
    const int16 = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
    view.setInt16(i * 2, int16, true); // Little-endian
  }

  return buffer;
}

// Convert 16-bit PCM to Float32 audio samples
export function pcm16ToFloat32(pcmData: ArrayBuffer): Float32Array {
  const view = new DataView(pcmData);
  const numSamples = pcmData.byteLength / 2;
  const samples = new Float32Array(numSamples);

  for (let i = 0; i < numSamples; i++) {
    const int16 = view.getInt16(i * 2, true); // Little-endian
    samples[i] = int16 / (int16 < 0 ? 0x8000 : 0x7fff);
  }

  return samples;
}

// Resample audio from one sample rate to another
export function resample(
  samples: Float32Array,
  fromRate: number,
  toRate: number
): Float32Array {
  if (fromRate === toRate) {
    return samples;
  }

  const ratio = fromRate / toRate;
  const newLength = Math.round(samples.length / ratio);
  const result = new Float32Array(newLength);

  for (let i = 0; i < newLength; i++) {
    const srcIndex = i * ratio;
    const srcIndexFloor = Math.floor(srcIndex);
    const srcIndexCeil = Math.min(srcIndexFloor + 1, samples.length - 1);
    const fraction = srcIndex - srcIndexFloor;

    // Linear interpolation
    result[i] =
      samples[srcIndexFloor] * (1 - fraction) + samples[srcIndexCeil] * fraction;
  }

  return result;
}

// Calculate chunk duration in milliseconds
export function getChunkDurationMs(
  byteLength: number,
  sampleRate: number = DEFAULT_AUDIO_CONFIG.inputSampleRate,
  bytesPerSample: number = 2
): number {
  const samples = byteLength / bytesPerSample;
  return (samples / sampleRate) * 1000;
}

// Calculate optimal chunk size for target duration
export function getOptimalChunkSize(
  targetMs: number,
  sampleRate: number = DEFAULT_AUDIO_CONFIG.inputSampleRate,
  bytesPerSample: number = 2
): number {
  const samples = Math.floor((sampleRate * targetMs) / 1000);
  return samples * bytesPerSample;
}

// Audio level meter (0-1 range)
export function calculateLevel(samples: Float32Array): number {
  if (samples.length === 0) return 0;
  let sum = 0;
  for (let i = 0; i < samples.length; i++) {
    sum += Math.abs(samples[i]);
  }
  return sum / samples.length;
}
