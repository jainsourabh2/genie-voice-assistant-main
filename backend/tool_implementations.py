# Tool function implementations for AjnaLens Voice Assistant (B)
# Each tool is an async function aligned with SI_PROD.md tool definitions
# Tools: capture_frame, take_photo, start_video, stop_video, start_observe_mode,
#        stop_observe_mode, start_meeting_mode, stop_meeting_mode, call_someone,
#        confirm_call, get_location_name_from_lat_long, stop_b

import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime
import random
import uuid

from logger import get_logger

logger = get_logger("tool_implementations")


# Active session state tracking to prevent duplicate tool calls
class SessionState:
    """Track active sessions to prevent duplicate start calls."""

    def __init__(self):
        self.video_active = False
        self.video_id: Optional[str] = None
        self.observe_active = False
        self.observe_id: Optional[str] = None
        self.meeting_active = False
        self.meeting_id: Optional[str] = None

    def reset_video(self):
        self.video_active = False
        self.video_id = None

    def reset_observe(self):
        self.observe_active = False
        self.observe_id = None

    def reset_meeting(self):
        self.meeting_active = False
        self.meeting_id = None


# Global session state instance (fallback for backward compatibility)
session_state = SessionState()

# Per-session state storage for multi-client isolation
_session_states: Dict[str, SessionState] = {}

# Tools that use session state (need _state injection)
STATEFUL_TOOLS = {
    "start_video", "stop_video",
    "start_observe_mode", "stop_observe_mode",
    "start_meeting_mode", "stop_meeting_mode",
}


def get_session_state(session_id: str) -> SessionState:
    """Get or create session state for a given session ID."""
    if session_id not in _session_states:
        _session_states[session_id] = SessionState()
    return _session_states[session_id]


def cleanup_session_state(session_id: str) -> None:
    """Remove session state when session ends."""
    removed = _session_states.pop(session_id, None)
    if removed:
        logger.debug(f"Cleaned up session state for {session_id}")


async def capture_frame(
    query: str,
) -> Dict[str, Any]:
    """
    Capture a frame from the camera for visual analysis.

    Args:
        query: The user's visual query or question about what they're seeing

    Returns:
        Dict with captured frame analysis result
    """
    logger.info(f"Capturing frame for query: {query}")

    # Mock frame capture - in production, this would interface with camera hardware
    frame_id = f"frame_{uuid.uuid4().hex[:8]}"
    timestamp = datetime.now().isoformat()

    # Simulated visual analysis result
    # In production, this would send frame to vision model for analysis
    analysis_results = [
        {
            "object": "coffee mug",
            "confidence": 0.92,
            "description": "A white ceramic coffee mug on a wooden desk"
        },
        {
            "object": "laptop",
            "confidence": 0.88,
            "description": "A silver laptop computer, appears to be open"
        },
        {
            "object": "notebook",
            "confidence": 0.75,
            "description": "A spiral-bound notebook with handwritten notes"
        }
    ]

    return {
        "success": True,
        "frame_id": frame_id,
        "timestamp": timestamp,
        "query": query,
        "analysis": analysis_results,
        "message": f"I can see a few things here. There's a white coffee mug on what looks like a wooden desk, a laptop that's open, and a notebook with some handwritten notes.",
    }


async def start_observe_mode(
    duration_seconds: int = 60,
    purpose: Optional[str] = None,
    _state: Optional[SessionState] = None,
) -> Dict[str, Any]:
    """
    Start live observation mode with continuous camera feed.

    Args:
        duration_seconds: How long to observe in seconds (default: 60)
        purpose: Optional purpose for the observation session

    Returns:
        Dict with observation session details
    """
    state = _state if _state is not None else session_state

    # Check if observe mode is already active
    if state.observe_active:
        logger.warning(f"Duplicate start_observe_mode call blocked. Active: {state.observe_id}")
        return {
            "success": False,
            "already_active": True,
            "session_id": state.observe_id,
            "status": "already_active",
            "message": "Live AI is already active. Say 'Stop live AI' when you're done.",
        }

    logger.info(f"Starting observe mode: duration={duration_seconds}s, purpose={purpose}")

    session_id = f"observe_{uuid.uuid4().hex[:8]}"
    start_time = datetime.now().isoformat()

    # Update session state
    state.observe_active = True
    state.observe_id = session_id

    return {
        "success": True,
        "session_id": session_id,
        "status": "active",
        "start_time": start_time,
        "duration_seconds": duration_seconds,
        "purpose": purpose or "general observation",
        "message": f"Live observation mode is now active. I'll keep watching for the next {duration_seconds} seconds. Just let me know when you want me to describe what I see or stop observing.",
    }


# NOTE: googleSearch is now handled via native Google Search grounding
# configured in gemini_client.py - no custom implementation needed


async def stop_meeting_mode(
    meeting_id: Optional[str] = None,
    _state: Optional[SessionState] = None,
) -> Dict[str, Any]:
    """
    Stop the current meeting recording session.

    Args:
        meeting_id: Optional meeting ID to stop. If not provided, stops current meeting.

    Returns:
        Dict with meeting stop confirmation and summary
    """
    state = _state if _state is not None else session_state

    # Check if meeting mode is active
    if not state.meeting_active:
        logger.warning("stop_meeting_mode called but no meeting recording active")
        return {
            "success": False,
            "status": "not_recording",
            "message": "There's no meeting recording in progress.",
        }

    logger.info(f"Stopping meeting mode: {state.meeting_id}")

    end_time = datetime.now().isoformat()
    duration_minutes = random.randint(5, 45)
    active_meeting_id = state.meeting_id

    # Reset session state
    state.reset_meeting()

    return {
        "success": True,
        "meeting_id": active_meeting_id,
        "status": "stopped",
        "end_time": end_time,
        "duration_minutes": duration_minutes,
        "transcript_available": True,
        "message": f"Meeting recording has been stopped. The session lasted about {duration_minutes} minutes. I've saved the transcript and it's ready for review.",
    }


async def start_meeting_mode(
    meeting_title: Optional[str] = None,
    participants: Optional[List[str]] = None,
    _state: Optional[SessionState] = None,
) -> Dict[str, Any]:
    """
    Start meeting recording mode to capture and transcribe a meeting.

    Args:
        meeting_title: Title or name for the meeting recording
        participants: List of participant names if known

    Returns:
        Dict with meeting session details
    """
    state = _state if _state is not None else session_state

    # Check if meeting mode is already active
    if state.meeting_active:
        logger.warning(f"Duplicate start_meeting_mode call blocked. Active: {state.meeting_id}")
        return {
            "success": False,
            "already_active": True,
            "meeting_id": state.meeting_id,
            "status": "already_recording",
            "message": "Meeting recording is already in progress. Say 'Stop recording' when you're done.",
        }

    logger.info(f"Starting meeting mode: title={meeting_title}, participants={participants}")

    meeting_id = f"meeting_{uuid.uuid4().hex[:8]}"
    start_time = datetime.now().isoformat()
    title = meeting_title or f"Meeting {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    # Update session state
    state.meeting_active = True
    state.meeting_id = meeting_id

    return {
        "success": True,
        "meeting_id": meeting_id,
        "status": "recording",
        "title": title,
        "start_time": start_time,
        "participants": participants or [],
        "features": ["audio_recording", "transcription", "speaker_identification"],
        "message": f"Meeting recording has started. I'll capture the audio and transcribe the conversation. The meeting is titled '{title}'. Just say 'Stop recording' when you're done.",
    }


async def call_someone(
    contact_name: str,
) -> Dict[str, Any]:
    """
    Initiate a phone call to a contact (search for contact, don't place call yet).

    Args:
        contact_name: Name of the person to call

    Returns:
        Dict with contact details for confirmation
    """
    logger.info(f"Looking up contact: {contact_name}")

    # Mock contact database - in production, this would search actual contacts
    mock_contacts = {
        "john": {
            "contact_id": "contact_001",
            "full_name": "John Smith",
            "phone_number": "+91 98765 43210",
            "relationship": "Work colleague"
        },
        "mom": {
            "contact_id": "contact_002",
            "full_name": "Mom",
            "phone_number": "+91 98765 43211",
            "relationship": "Family"
        },
        "sarah": {
            "contact_id": "contact_003",
            "full_name": "Sarah Johnson",
            "phone_number": "+91 98765 43212",
            "relationship": "Friend"
        },
        "doctor": {
            "contact_id": "contact_004",
            "full_name": "Dr. Patel",
            "phone_number": "+91 98765 43213",
            "relationship": "Healthcare"
        }
    }

    # Search for contact (case-insensitive partial match)
    search_key = contact_name.lower()
    matched_contact = None

    for key, contact in mock_contacts.items():
        if search_key in key or search_key in contact["full_name"].lower():
            matched_contact = contact
            break

    if matched_contact:
        return {
            "success": True,
            "contact_found": True,
            "contact": matched_contact,
            "requires_confirmation": True,
            "message": f"I found {matched_contact['full_name']}. Their number is {matched_contact['phone_number']}. Should I call them?",
        }
    else:
        return {
            "success": True,
            "contact_found": False,
            "contact": None,
            "requires_confirmation": False,
            "message": f"I couldn't find a contact named {contact_name} in your contacts. Could you give me more details or the full name?",
        }


async def confirm_call(
    contact_id: str,
    phone_number: str,
) -> Dict[str, Any]:
    """
    Confirm and place a phone call to a previously resolved contact.

    Args:
        contact_id: The contact ID returned from call_someone
        phone_number: The phone number to call (from call_someone result)

    Returns:
        Dict with call status
    """
    logger.info(f"Placing call: contact_id={contact_id}, phone={phone_number}")

    call_id = f"call_{uuid.uuid4().hex[:8]}"
    start_time = datetime.now().isoformat()

    return {
        "success": True,
        "call_id": call_id,
        "status": "dialing",
        "contact_id": contact_id,
        "phone_number": phone_number,
        "start_time": start_time,
        "message": f"Calling {phone_number} now. I'll let you know when they answer.",
    }


async def take_photo(
    caption: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Take a photo when the user explicitly requests it.

    Args:
        caption: Optional caption or context for the photo

    Returns:
        Dict with photo capture confirmation
    """
    logger.info(f"Taking photo: caption={caption}")

    photo_id = f"photo_{uuid.uuid4().hex[:8]}"
    timestamp = datetime.now().isoformat()

    return {
        "success": True,
        "photo_id": photo_id,
        "timestamp": timestamp,
        "caption": caption,
        "status": "captured",
        "message": "Photo captured successfully! I've saved it for you.",
    }


async def start_video(
    purpose: Optional[str] = None,
    _state: Optional[SessionState] = None,
) -> Dict[str, Any]:
    """
    Start video recording when the user wants to record a video.

    Args:
        purpose: Optional purpose or context for the video recording

    Returns:
        Dict with video recording session details
    """
    state = _state if _state is not None else session_state

    # Check if video recording is already active
    if state.video_active:
        logger.warning(f"Duplicate start_video call blocked. Active: {state.video_id}")
        return {
            "success": False,
            "already_active": True,
            "video_id": state.video_id,
            "status": "already_recording",
            "message": "Video recording is already in progress. Say 'Stop video' when you're done.",
        }

    logger.info(f"Starting video recording: purpose={purpose}")

    video_id = f"video_{uuid.uuid4().hex[:8]}"
    start_time = datetime.now().isoformat()

    # Update session state
    state.video_active = True
    state.video_id = video_id

    return {
        "success": True,
        "video_id": video_id,
        "status": "recording",
        "start_time": start_time,
        "purpose": purpose,
        "message": "Video recording started. Say 'Stop video' when you're done.",
    }


async def stop_video(
    _state: Optional[SessionState] = None,
) -> Dict[str, Any]:
    """
    Stop the current video recording.

    Returns:
        Dict with video stop confirmation
    """
    state = _state if _state is not None else session_state

    # Check if video recording is active
    if not state.video_active:
        logger.warning("stop_video called but no video recording active")
        return {
            "success": False,
            "status": "not_recording",
            "message": "There's no video recording in progress.",
        }

    logger.info(f"Stopping video recording: {state.video_id}")

    end_time = datetime.now().isoformat()
    duration_seconds = random.randint(5, 120)
    video_id = state.video_id

    # Reset session state
    state.reset_video()

    return {
        "success": True,
        "video_id": video_id,
        "status": "stopped",
        "end_time": end_time,
        "duration_seconds": duration_seconds,
        "message": f"Video recording stopped. The video is {duration_seconds} seconds long and has been saved.",
    }


async def stop_observe_mode(
    _state: Optional[SessionState] = None,
) -> Dict[str, Any]:
    """
    Stop the live AI observation mode.

    Returns:
        Dict with observation stop confirmation
    """
    state = _state if _state is not None else session_state

    # Check if observe mode is active
    if not state.observe_active:
        logger.warning("stop_observe_mode called but no observe mode active")
        return {
            "success": False,
            "status": "not_active",
            "message": "Live AI is not currently active.",
        }

    logger.info(f"Stopping observe mode: {state.observe_id}")

    end_time = datetime.now().isoformat()
    session_id = state.observe_id

    # Reset session state
    state.reset_observe()

    return {
        "success": True,
        "session_id": session_id,
        "status": "stopped",
        "end_time": end_time,
        "message": "Live AI observation mode has been stopped. Let me know if you need anything else.",
    }


async def get_location_name_from_lat_long(
    latitude: float,
    longitude: float,
) -> Dict[str, Any]:
    """
    Fetch location name from latitude and longitude coordinates.

    Args:
        latitude: The latitude coordinate
        longitude: The longitude coordinate

    Returns:
        Dict with location details
    """
    logger.info(f"Getting location name: lat={latitude}, long={longitude}")

    # Mock location lookup - in production, this would use Google Maps API
    mock_locations = [
        {"name": "Connaught Place", "city": "New Delhi", "country": "India"},
        {"name": "Bandra West", "city": "Mumbai", "country": "India"},
        {"name": "Koramangala", "city": "Bangalore", "country": "India"},
        {"name": "Salt Lake City", "city": "Kolkata", "country": "India"},
    ]

    location = random.choice(mock_locations)

    return {
        "success": True,
        "latitude": latitude,
        "longitude": longitude,
        "location_name": location["name"],
        "city": location["city"],
        "country": location["country"],
        "formatted_address": f"{location['name']}, {location['city']}, {location['country']}",
        "message": f"You're currently near {location['name']} in {location['city']}.",
    }


async def stop_b() -> Dict[str, Any]:
    """
    End the current session.

    Returns:
        Dict with session end confirmation
    """
    logger.info("Ending session (stop_b)")

    return {
        "success": True,
        "status": "session_ended",
        "message": "Goodbye! It was nice chatting with you. Take care!",
    }


# Tool function registry - maps tool names to their implementations
# NOTE: googleSearch uses native grounding, not a custom function
TOOL_FUNCTIONS = {
    "capture_frame": capture_frame,
    "take_photo": take_photo,
    "start_video": start_video,
    "stop_video": stop_video,
    "start_observe_mode": start_observe_mode,
    "stop_observe_mode": stop_observe_mode,
    "start_meeting_mode": start_meeting_mode,
    "stop_meeting_mode": stop_meeting_mode,
    "call_someone": call_someone,
    "confirm_call": confirm_call,
    "get_location_name_from_lat_long": get_location_name_from_lat_long,
    "stop_b": stop_b,
}


async def execute_tool(
    tool_name: str, args: Dict[str, Any], session_id: str = None
) -> Dict[str, Any]:
    """
    Execute a tool by name with the given arguments.

    Args:
        tool_name: Name of the tool to execute
        args: Arguments to pass to the tool function
        session_id: Session ID for per-session state isolation

    Returns:
        Tool execution result
    """
    tool_func = TOOL_FUNCTIONS.get(tool_name)

    if not tool_func:
        logger.warning(f"Unknown tool requested: {tool_name}")
        return {
            "success": False,
            "error": f"Unknown tool: {tool_name}",
            "message": "I'm not able to do that with the current setup. Is there something else you'd like to explore?",
        }

    try:
        # Inject per-session state for stateful tools
        if session_id and tool_name in STATEFUL_TOOLS:
            state = get_session_state(session_id)
            result = await tool_func(**args, _state=state)
        else:
            result = await tool_func(**args)
        logger.info(f"Tool {tool_name} executed successfully")
        return result
    except TypeError as e:
        logger.error(f"Tool {tool_name} called with invalid arguments: {e}")
        return {
            "success": False,
            "error": f"Invalid arguments for {tool_name}: {str(e)}",
            "message": "I encountered an issue with that request. Could you please try again?",
        }
    except Exception as e:
        logger.error(f"Tool {tool_name} execution failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Something went wrong. Please try again.",
        }
