# Configuration for Voice Chatbot with Gemini Live API
import os
from pathlib import Path
from enum import Enum
from dotenv import load_dotenv

# Project root directory (parent of backend/)
PROJECT_ROOT = Path(__file__).parent.parent

# Load .env from project root
load_dotenv(PROJECT_ROOT / ".env", override=True)


# Endpoint mode for switching between Autopush (sandbox) and Production
class EndpointMode(str, Enum):
    """Endpoint mode for Vertex AI API access."""
    AUTOPUSH = "AUTOPUSH"  # Sandbox environment, uses bearer token from gcloud
    PROD = "PROD"          # Production environment, uses service account key


# Vertex AI API Endpoints
VERTEX_API_ENDPOINT_PROD = "us-central1-aiplatform.googleapis.com"
VERTEX_API_ENDPOINT_AUTOPUSH = "us-central1-autopush-aiplatform.sandbox.googleapis.com"

# Default endpoint mode (can be overridden via frontend)
DEFAULT_ENDPOINT_MODE = EndpointMode(os.getenv("ENDPOINT_MODE", "PROD"))

# Vertex AI Configuration
PROJECT_ID = "vital-octagon-19612"
LOCATION = "us-central1"
# MODEL_NAME = "gemini-live-2.5-flash-native-audio"
MODEL_NAME = "gemini-live-2.5-flash-preview-native-audio-09-2025"

# Audio Configuration
INPUT_SAMPLE_RATE = 16000  # 16kHz for input
OUTPUT_SAMPLE_RATE = 24000  # 24kHz for output
AUDIO_CHANNELS = 1
BITS_PER_SAMPLE = 16

# Chunk sizes (20-40ms optimal for low latency)
MIN_CHUNK_MS = 20
MAX_CHUNK_MS = 40
MIN_CHUNK_BYTES = int(INPUT_SAMPLE_RATE * (BITS_PER_SAMPLE // 8) * MIN_CHUNK_MS / 1000)  # 640 bytes
MAX_CHUNK_BYTES = int(INPUT_SAMPLE_RATE * (BITS_PER_SAMPLE // 8) * MAX_CHUNK_MS / 1000)  # 1280 bytes

# WebSocket Configuration
WS_HOST = os.getenv("WS_HOST", "0.0.0.0")
WS_PORT = int(os.getenv("WS_PORT", "8765"))

# Tool Configuration
TOOL_EXECUTION_DELAY = 8  # seconds
# Dedup cooldown: how long (seconds) after a tool completes before allowing
# the same tool+args to be called again. Must be long enough to catch model
# re-triggers (~0.1-1s) but short enough to allow legitimate user re-requests
# (~6s+ after completion). 5s is the sweet spot.
DEDUP_COOLDOWN_SECONDS = 5

# Activity Detection
ACTIVITY_END_THRESHOLD = 1.0  # seconds of silence before sending activity_end

# Logging
LOG_DIR = "log"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Service Account - resolve relative to project root
_svc_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "vital-octagon-svc.json")
SERVICE_ACCOUNT_FILE = str(PROJECT_ROOT / _svc_file) if not os.path.isabs(_svc_file) else _svc_file

# Set the environment variable to the absolute path
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = SERVICE_ACCOUNT_FILE
