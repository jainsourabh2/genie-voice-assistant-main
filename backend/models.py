# Pydantic models for WebSocket messages
from typing import Optional, Any, List, Dict
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class MessageType(str, Enum):
    """WebSocket message types"""
    # Client -> Server
    INIT = "init"
    AUDIO = "audio"
    STOP = "stop"

    # Server -> Client
    SESSION_STARTED = "session_started"
    TRANSCRIPT = "transcript"
    AUDIO_RESPONSE = "audio_response"
    TOOL_CALL = "tool_call"
    TOOL_RESPONSE = "tool_response"
    TURN_COMPLETE = "turn_complete"
    ERROR = "error"
    SESSION_ENDED = "session_ended"
    INTERRUPTED = "interrupted"


class VADSettings(BaseModel):
    """Voice Activity Detection settings - full configuration options"""
    disabled: Optional[bool] = Field(
        default=None,
        description="If true, disables automatic activity detection - client must send activity signals"
    )
    start_sensitivity: str = Field(
        default="HIGH",
        description="START_SENSITIVITY_HIGH, START_SENSITIVITY_LOW, or START_SENSITIVITY_UNSPECIFIED"
    )
    end_sensitivity: str = Field(
        default="HIGH",
        description="END_SENSITIVITY_HIGH, END_SENSITIVITY_LOW, or END_SENSITIVITY_UNSPECIFIED"
    )
    prefix_padding_ms: Optional[int] = Field(
        default=None,
        description="Duration in ms of detected speech before start-of-speech is committed"
    )
    silence_duration_ms: Optional[int] = Field(
        default=None,
        description="Duration in ms of silence before end-of-speech is committed"
    )


class InitMessage(BaseModel):
    """Client initialization message"""
    type: MessageType = MessageType.INIT
    system_instruction: Optional[str] = None
    vad_settings: Optional[VADSettings] = None
    voice_name: str = Field(default="Aoede")
    endpoint_mode: Optional[str] = Field(
        default=None,
        description="AUTOPUSH (sandbox with bearer token) or PROD (service account)"
    )


class AudioMessage(BaseModel):
    """Audio data message (base64 encoded PCM)"""
    type: MessageType = MessageType.AUDIO
    data: str  # Base64 encoded audio


class StopMessage(BaseModel):
    """Stop session message"""
    type: MessageType = MessageType.STOP


class TranscriptMessage(BaseModel):
    """Transcription message"""
    type: MessageType = MessageType.TRANSCRIPT
    role: str  # "user" or "model"
    text: str
    timestamp: datetime = Field(default_factory=datetime.now)
    is_final: bool = False
    ttfb_ms: Optional[float] = None  # Time to first byte (model responses only)


class AudioResponseMessage(BaseModel):
    """Audio response from model"""
    type: MessageType = MessageType.AUDIO_RESPONSE
    data: str  # Base64 encoded audio
    ttfb_ms: Optional[float] = None


class ToolCallMessage(BaseModel):
    """Tool call notification"""
    type: MessageType = MessageType.TOOL_CALL
    id: str
    name: str
    args: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)


class ToolResponseMessage(BaseModel):
    """Tool response message"""
    type: MessageType = MessageType.TOOL_RESPONSE
    id: str
    name: str
    response: Any
    timestamp: datetime = Field(default_factory=datetime.now)


class TurnCompleteMessage(BaseModel):
    """Turn completion notification"""
    type: MessageType = MessageType.TURN_COMPLETE
    timestamp: datetime = Field(default_factory=datetime.now)


class SessionStartedMessage(BaseModel):
    """Session started confirmation"""
    type: MessageType = MessageType.SESSION_STARTED
    session_id: str
    model: str
    config: Dict[str, Any]


class SessionEndedMessage(BaseModel):
    """Session ended notification"""
    type: MessageType = MessageType.SESSION_ENDED
    session_id: str


class ErrorMessage(BaseModel):
    """Error message"""
    type: MessageType = MessageType.ERROR
    error: str
    details: Optional[str] = None


class InterruptedMessage(BaseModel):
    """Model was interrupted"""
    type: MessageType = MessageType.INTERRUPTED
    timestamp: datetime = Field(default_factory=datetime.now)
