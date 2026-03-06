# Genie Voice Assistant

Voice-based AI assistant powered by Gemini Live API on Vertex AI.

## Features

- Real-time voice conversation with AI assistant
- Voice Activity Detection (VAD) with configurable sensitivity
- Tool integration for visual capture, search, meetings, and calls
- Native Google Search grounding for real search results
- Live transcription display
- Time-to-first-byte (TTFB) metrics
- Jitter buffer for smooth audio playback
- Endpoint toggle (Prod/Autopush)

## Technology Stack

- **Frontend**: React 18 + TypeScript + Vite
- **Backend**: Python 3.12 + websockets + google-genai
- **AI Model**: Gemini Live 2.5 Flash Native Audio
- **Platform**: Google Cloud Vertex AI

## Prerequisites

- Python 3.12+
- Node.js 18+
- uv (Python package manager)
- Google Cloud service account with Vertex AI access

## Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd genie-voice-assistant
   ```

2. **Add service account credentials**

   Place your Google Cloud service account JSON file in the project root.

3. **Configure environment**

   The `.env` file contains default configuration:
   ```
   WS_HOST=0.0.0.0
   WS_PORT=8765
   LOG_LEVEL=INFO
   GOOGLE_APPLICATION_CREDENTIALS=<your-service-account>.json
   ```

## Running the Application

### Using the run script (recommended)

```bash
chmod +x run.sh
./run.sh
```

This will start both the backend and frontend servers.

### Manual startup

**Backend:**
```bash
cd backend
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
python main.py
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Usage

1. Open http://localhost:5173 in your browser
2. Click "Connect" to establish WebSocket connection
3. Select endpoint mode (Prod or Autopush)
4. (Optional) Adjust VAD settings or system instructions
5. Click "Start Session" to begin the conversation
6. Speak into your microphone - the AI will respond via audio
7. View transcriptions and tool calls in real-time
8. Click "Stop Session" to end the conversation

## Configuration

### Endpoint Modes
- **Prod**: Uses service account key authentication
- **Autopush**: Uses bearer token from `gcloud auth print-access-token`

### VAD Settings
- **Start Sensitivity**: HIGH (more responsive) or LOW (less sensitive)
- **End Sensitivity**: HIGH (quick response) or LOW (longer pauses allowed)

### Voice Options
Default voice is "Aoede". Can be changed in the code if needed.

## Available Tools

The assistant can perform these actions:

1. **capture_frame** - Capture camera frame for visual analysis
2. **start_observe_mode** - Start live observation with continuous camera feed
3. **start_meeting_mode** - Start meeting recording and transcription
4. **stop_meeting_mode** - Stop meeting recording
5. **call_someone** - Look up a contact for calling
6. **confirm_call** - Confirm and place the call
7. **Google Search** - Native grounding for real-time web search

## Project Structure

```
genie-voice-assistant/
├── backend/
│   ├── main.py                 # WebSocket server
│   ├── config.py               # Configuration
│   ├── gemini_client.py        # Gemini API client
│   ├── audio_handler.py        # Audio processing
│   ├── tool_handler.py         # Tool execution
│   ├── session_manager.py      # Session state
│   ├── logger.py               # Logging
│   ├── models.py               # Data models
│   ├── system_instructions.py  # AI prompts
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── services/
│   │   └── types/
│   ├── package.json
│   └── vite.config.ts
├── log/                        # Log files
├── run.sh                      # Startup script
├── .env                        # Environment config
└── README.md
```

## Logs

- Terminal output is color-coded for easy reading
- Log files are stored in the `log/` directory with daily rotation

## Troubleshooting

### Microphone not working
- Ensure browser has microphone permission
- Check that audio input is set to 16kHz

### Connection issues
- Verify backend is running on port 8765
- Check WebSocket connection in browser console
- Ensure service account has Vertex AI permissions

### Audio playback issues
- The jitter buffer requires 100-150ms of audio before playback starts
- Check browser console for audio-related errors
