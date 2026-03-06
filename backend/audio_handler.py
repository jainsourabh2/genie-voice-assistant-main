# PCM audio processing utilities
import struct
from typing import Tuple, Optional

from config import (
    INPUT_SAMPLE_RATE,
    OUTPUT_SAMPLE_RATE,
    BITS_PER_SAMPLE,
    AUDIO_CHANNELS,
    MIN_CHUNK_BYTES,
    MAX_CHUNK_BYTES
)
from logger import get_logger

logger = get_logger("audio_handler")


class AudioHandler:
    """PCM audio processing for voice chatbot"""

    def __init__(self):
        self.input_sample_rate = INPUT_SAMPLE_RATE
        self.output_sample_rate = OUTPUT_SAMPLE_RATE
        self.bits_per_sample = BITS_PER_SAMPLE
        self.channels = AUDIO_CHANNELS
        self.bytes_per_sample = BITS_PER_SAMPLE // 8

        logger.info(
            f"AudioHandler initialized: input={INPUT_SAMPLE_RATE}Hz, "
            f"output={OUTPUT_SAMPLE_RATE}Hz, {BITS_PER_SAMPLE}-bit"
        )

    def validate_pcm_chunk(self, data: bytes) -> Tuple[bool, Optional[str]]:
        """
        Validate PCM audio chunk.
        Returns (is_valid, error_message)
        """
        if not data:
            return False, "Empty audio data"

        # Check if data length is valid (must be even for 16-bit audio)
        if len(data) % self.bytes_per_sample != 0:
            return False, f"Invalid data length: {len(data)} (must be even for 16-bit PCM)"

        # Warn if chunk size is outside optimal range
        if len(data) < MIN_CHUNK_BYTES:
            logger.debug(f"Chunk size {len(data)} bytes is below optimal ({MIN_CHUNK_BYTES})")
        elif len(data) > MAX_CHUNK_BYTES:
            logger.debug(f"Chunk size {len(data)} bytes exceeds optimal ({MAX_CHUNK_BYTES})")

        return True, None

    def calculate_chunk_duration_ms(self, chunk_bytes: int) -> float:
        """Calculate duration of audio chunk in milliseconds"""
        samples = chunk_bytes // self.bytes_per_sample
        duration_sec = samples / self.input_sample_rate
        return duration_sec * 1000

    def calculate_optimal_chunk_size(self, target_ms: int = 25) -> int:
        """Calculate optimal chunk size for target duration"""
        samples = int(self.input_sample_rate * target_ms / 1000)
        return samples * self.bytes_per_sample

    def get_audio_stats(self, data: bytes) -> dict:
        """Get statistics about audio chunk"""
        if not data:
            return {"error": "Empty data"}

        samples = len(data) // self.bytes_per_sample

        # Unpack samples to calculate levels
        try:
            format_str = f"<{samples}h"  # Little-endian 16-bit signed integers
            sample_values = struct.unpack(format_str, data)

            max_val = max(abs(s) for s in sample_values)
            avg_val = sum(abs(s) for s in sample_values) / len(sample_values)

            # Normalize to 0-1 range (max 16-bit value is 32767)
            peak_level = max_val / 32767
            avg_level = avg_val / 32767

            return {
                "samples": samples,
                "duration_ms": self.calculate_chunk_duration_ms(len(data)),
                "peak_level": round(peak_level, 4),
                "avg_level": round(avg_level, 4),
                "bytes": len(data)
            }
        except struct.error as e:
            return {"error": f"Failed to unpack audio: {e}"}

    def is_silence(self, data: bytes, threshold: float = 0.01) -> bool:
        """Check if audio chunk is silence (below threshold)"""
        stats = self.get_audio_stats(data)
        if "error" in stats:
            return True
        return stats["avg_level"] < threshold

    def split_into_chunks(self, data: bytes, chunk_ms: int = 25) -> list:
        """Split audio data into optimal-sized chunks"""
        chunk_size = self.calculate_optimal_chunk_size(chunk_ms)
        chunks = []

        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            if len(chunk) >= self.bytes_per_sample:  # At least one sample
                chunks.append(chunk)

        return chunks

    def get_input_mime_type(self) -> str:
        """Get MIME type for input audio"""
        return f"audio/pcm;rate={self.input_sample_rate}"

    def get_output_mime_type(self) -> str:
        """Get MIME type for output audio"""
        return f"audio/pcm;rate={self.output_sample_rate}"
