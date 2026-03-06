# Gemini Live API client wrapper
import asyncio
import base64
import json
import subprocess
import time
import uuid
from typing import AsyncGenerator, Optional, Callable, Any
from google import genai
from google.genai import types
from google.oauth2 import credentials as oauth2_credentials
from google.oauth2 import service_account

from config import (
    PROJECT_ID,
    LOCATION,
    MODEL_NAME,
    EndpointMode,
    DEFAULT_ENDPOINT_MODE,
    VERTEX_API_ENDPOINT_PROD,
    VERTEX_API_ENDPOINT_AUTOPUSH,
    SERVICE_ACCOUNT_FILE,
)
from system_instructions import SYSTEM_INSTRUCTION, TOOL_DECLARATIONS
from logger import get_logger

logger = get_logger("gemini_client")


class GeminiLiveClient:
    """Wrapper for Gemini Live API with Vertex AI"""

    def __init__(
        self,
        system_instruction: Optional[str] = None,
        vad_disabled: Optional[bool] = None,
        vad_start_sensitivity: str = "HIGH",
        vad_end_sensitivity: str = "HIGH",
        vad_prefix_padding_ms: Optional[int] = 300,
        vad_silence_duration_ms: Optional[int] = 800,
        voice_name: str = "Aoede",
        endpoint_mode: Optional[EndpointMode] = None
    ):
        self.system_instruction = system_instruction or SYSTEM_INSTRUCTION
        self.vad_disabled = vad_disabled
        self.vad_start_sensitivity = vad_start_sensitivity
        self.vad_end_sensitivity = vad_end_sensitivity
        self.vad_prefix_padding_ms = vad_prefix_padding_ms
        self.vad_silence_duration_ms = vad_silence_duration_ms
        self.voice_name = voice_name
        self.endpoint_mode = endpoint_mode or DEFAULT_ENDPOINT_MODE

        # Determine endpoint and authentication based on mode
        if self.endpoint_mode == EndpointMode.AUTOPUSH:
            # Autopush uses bearer token from gcloud auth
            endpoint = VERTEX_API_ENDPOINT_AUTOPUSH
            credentials = self._get_gcloud_credentials()
            logger.info(f"Using AUTOPUSH endpoint with bearer token: {endpoint}")
        else:
            # Production uses service account key file directly (not relying on env var)
            endpoint = VERTEX_API_ENDPOINT_PROD
            credentials = self._get_service_account_credentials()
            logger.info(f"Using PROD endpoint with service account: {endpoint}")

        # Initialize Vertex AI client with appropriate endpoint and credentials
        self.client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location=LOCATION,
            credentials=credentials,
            http_options={"base_url": f"https://{endpoint}"},
        )
        self._endpoint = endpoint

        self._session = None
        self._context_manager = None  # Keep reference to prevent garbage collection
        self._first_byte_time: Optional[float] = None
        self._request_start_time: Optional[float] = None
        self._is_connected = False

        logger.info(f"GeminiLiveClient initialized for project {PROJECT_ID}, mode={self.endpoint_mode.value}")

    def _get_gcloud_credentials(self) -> oauth2_credentials.Credentials:
        """Get credentials using gcloud auth print-access-token (for Autopush)."""
        try:
            result = subprocess.run(
                ["gcloud", "auth", "print-access-token"],
                capture_output=True,
                text=True,
                check=True
            )
            access_token = result.stdout.strip()
            logger.debug("Successfully obtained gcloud access token")
            return oauth2_credentials.Credentials(token=access_token)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get gcloud access token: {e.stderr}")
            raise ValueError(
                "Failed to get access token. Run: gcloud auth login"
            ) from e
        except FileNotFoundError:
            logger.error("gcloud CLI not found")
            raise ValueError(
                "gcloud CLI not found. Install Google Cloud SDK."
            )

    def _get_service_account_credentials(self) -> service_account.Credentials:
        """Get credentials from service account key file (for Prod)."""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE,
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            logger.debug(f"Loaded service account credentials from {SERVICE_ACCOUNT_FILE}")
            return credentials
        except FileNotFoundError:
            logger.error(f"Service account file not found: {SERVICE_ACCOUNT_FILE}")
            raise ValueError(
                f"Service account file not found: {SERVICE_ACCOUNT_FILE}"
            )
        except Exception as e:
            logger.error(f"Failed to load service account credentials: {e}")
            raise ValueError(
                f"Failed to load service account credentials: {e}"
            ) from e

    def _build_config(self) -> types.LiveConnectConfig:
        """Build the LiveConnectConfig for the session"""
        # Map string sensitivity to enum values
        start_sens_map = {
            "HIGH": types.StartSensitivity.START_SENSITIVITY_HIGH,
            "LOW": types.StartSensitivity.START_SENSITIVITY_LOW,
            "UNSPECIFIED": types.StartSensitivity.START_SENSITIVITY_UNSPECIFIED,
        }
        end_sens_map = {
            "HIGH": types.EndSensitivity.END_SENSITIVITY_HIGH,
            "LOW": types.EndSensitivity.END_SENSITIVITY_LOW,
            "UNSPECIFIED": types.EndSensitivity.END_SENSITIVITY_UNSPECIFIED,
        }

        start_sens = start_sens_map.get(
            self.vad_start_sensitivity,
            types.StartSensitivity.START_SENSITIVITY_HIGH
        )
        end_sens = end_sens_map.get(
            self.vad_end_sensitivity,
            types.EndSensitivity.END_SENSITIVITY_HIGH
        )

        # Build AutomaticActivityDetection with all available options
        vad_config = types.AutomaticActivityDetection(
            disabled=self.vad_disabled,
            start_of_speech_sensitivity=start_sens if not self.vad_disabled else None,
            end_of_speech_sensitivity=end_sens if not self.vad_disabled else None,
            prefix_padding_ms=self.vad_prefix_padding_ms,
            silence_duration_ms=self.vad_silence_duration_ms,
        )

        # Configure tools: native Google Search grounding + custom function declarations
        tools_config = [
            # Native Google Search grounding for real search results
            types.Tool(google_search=types.GoogleSearch()),
            # Custom function declarations for other tools
            types.Tool(function_declarations=TOOL_DECLARATIONS),
        ]

        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=self.system_instruction,
            tools=tools_config,
            input_audio_transcription={},
            output_audio_transcription={},
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=vad_config
            ),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=self.voice_name
                    )
                )
            ),
        )

        logger.debug(
            f"Built config with VAD: disabled={self.vad_disabled}, "
            f"start={self.vad_start_sensitivity}, end={self.vad_end_sensitivity}, "
            f"prefix_padding_ms={self.vad_prefix_padding_ms}, "
            f"silence_duration_ms={self.vad_silence_duration_ms}, voice={self.voice_name}"
        )
        return config

    async def connect(self) -> None:
        """Establish connection to Gemini Live API"""
        if self._is_connected:
            logger.warning("Already connected, skipping connect()")
            return

        config = self._build_config()

        logger.info(f"Connecting to Gemini Live API with model: {MODEL_NAME}")
        # Store the context manager to prevent garbage collection
        self._context_manager = self.client.aio.live.connect(
            model=MODEL_NAME,
            config=config
        )
        self._session = await self._context_manager.__aenter__()
        self._is_connected = True
        logger.info("Connected to Gemini Live API")

    async def disconnect(self) -> None:
        """Disconnect from Gemini Live API"""
        if self._context_manager and self._is_connected:
            try:
                await self._context_manager.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
            finally:
                self._session = None
                self._context_manager = None
                self._is_connected = False
                logger.info("Disconnected from Gemini Live API")

    async def send_audio(self, audio_data: bytes) -> None:
        """
        Send audio chunk to the model.
        Audio should be PCM 16-bit mono at 16kHz.
        Optimal chunk size: 20-40ms (320-640 bytes)
        """
        if not self._session or not self._is_connected:
            logger.error("Cannot send audio: not connected")
            return

        # Track request start time for TTFB calculation
        if self._request_start_time is None:
            self._request_start_time = time.time()

        # Send audio as realtime input
        await self._session.send_realtime_input(
            audio=types.Blob(
                mime_type="audio/pcm;rate=16000",
                data=audio_data
            )
        )

    async def send_audio_base64(self, audio_base64: str) -> None:
        """Send base64-encoded audio chunk"""
        audio_data = base64.b64decode(audio_base64)
        await self.send_audio(audio_data)

    async def send_activity_end(self) -> None:
        """Signal end of audio activity (send when paused >1 second)"""
        if not self._session or not self._is_connected:
            return

        try:
            await self._session.send_realtime_input(activity_end={})
            logger.debug("Sent activity_end signal")
        except Exception as e:
            logger.error(f"Error sending activity_end: {e}")

    async def send_tool_response(
        self,
        function_id: str,
        function_name: str,
        response: Any
    ) -> None:
        """
        Send final tool result to the model as injected context.

        Since the interim PROCESSING FunctionResponse already resolved the tool call
        from the model's perspective, sending a second FunctionResponse with the same
        ID causes the model to repeat itself. Instead, we inject the result as client
        content so the model receives it as new information and speaks about it naturally.

        NOTE: will_continue and NON_BLOCKING behavior are NOT supported in Vertex AI.
        This send_client_content approach is the Vertex AI workaround.
        """
        if not self._session or not self._is_connected:
            logger.error("Cannot send tool response: not connected")
            return

        # Build a concise result summary for the model
        result_text = (
            f"[Tool completed] {function_name} result: "
            f"{json.dumps(response, default=str)}"
        )

        await self._session.send_client_content(
            turns=types.Content(
                parts=[types.Part(text=result_text)],
                role="user"
            ),
            turn_complete=True
        )
        logger.info(f"Sent tool result as context for {function_name}")

    async def send_interim_tool_response(
        self,
        function_id: str,
        function_name: str,
        interim_message: str
    ) -> None:
        """
        Send an interim tool response while the tool executes.

        This uses send_tool_response() with a PROCESSING status, which is the
        correct API method for interim responses. The model receives this as a
        proper tool response and can acknowledge it to the user.

        After tool execution completes, a final tool response with the actual
        result should be sent via send_tool_response().

        Args:
            function_id: The tool call ID from Gemini
            function_name: Name of the tool being executed
            interim_message: The interim message to include in the response
        """
        if not self._session or not self._is_connected:
            logger.error("Cannot send interim tool response: not connected")
            return

        try:
            # Send interim PROCESSING response to unblock the model for speech.
            # NOTE: will_continue is NOT supported in Vertex AI (causes 1007 error).
            # The model treats this as the tool's final result and acknowledges it.
            # The actual result is delivered later via send_client_content() to avoid
            # sending two FunctionResponses with the same ID (which confuses the model).
            interim_response = types.FunctionResponse(
                id=function_id,
                name=function_name,
                response={
                    "status": "PROCESSING",
                    "message": interim_message
                }
            )
            await self._session.send_tool_response(
                function_responses=[interim_response]
            )
            logger.info(f"Sent interim tool response for {function_name}")
        except Exception as e:
            logger.error(f"Failed to send interim tool response: {e}")

    async def receive_messages(self) -> AsyncGenerator[dict, None]:
        """
        Receive and yield messages from the model.
        Yields dictionaries with message type and data.

        NOTE: We use _receive() directly instead of receive() because the SDK's
        receive() method breaks after turn_complete, which prevents multi-turn
        conversations. Using _receive() in a continuous loop allows us to keep
        listening for new turns after the model completes its response.
        """
        if not self._session or not self._is_connected:
            logger.error("Cannot receive: not connected")
            return

        try:
            # Use _receive() directly for continuous multi-turn conversation support
            # The SDK's receive() breaks after turn_complete, but we need to keep
            # listening for subsequent user turns
            while self._is_connected:
                response = await self._session._receive()

                # Skip empty responses (can happen on connection issues)
                if not response:
                    continue

                # Calculate TTFB on first response
                ttfb_ms = None
                if self._request_start_time is not None and self._first_byte_time is None:
                    self._first_byte_time = time.time()
                    ttfb_ms = (self._first_byte_time - self._request_start_time) * 1000
                    logger.info(f"Time to first byte: {ttfb_ms:.2f}ms")

                # Process server content
                if response.server_content:
                    content = response.server_content

                    # Check for interruption
                    if content.interrupted:
                        logger.info("Model response was interrupted")
                        yield {"type": "interrupted"}
                        self._reset_timing()
                        continue

                    # Process model turn parts
                    if content.model_turn and content.model_turn.parts:
                        for part in content.model_turn.parts:
                            # Audio response
                            if part.inline_data and part.inline_data.data:
                                audio_b64 = base64.b64encode(part.inline_data.data).decode()
                                yield {
                                    "type": "audio",
                                    "data": audio_b64,
                                    "ttfb_ms": ttfb_ms
                                }
                                ttfb_ms = None  # Only include TTFB in first chunk

                            # Text from model turn parts — skip for audio-only models
                            # because output_transcription provides the authoritative text.
                            # Yielding both causes duplicate transcript entries.
                            # Only yield part.text if output_transcription is NOT enabled.
                            # (output_audio_transcription is always enabled in our config)

                    # Input transcription - MUST come BEFORE turn_complete to allow aggregation
                    if content.input_transcription and content.input_transcription.text:
                        yield {
                            "type": "transcript",
                            "text": content.input_transcription.text,
                            "role": "user"
                        }

                    # Output transcription - MUST come BEFORE turn_complete to allow aggregation
                    if content.output_transcription and content.output_transcription.text:
                        yield {
                            "type": "transcript",
                            "text": content.output_transcription.text,
                            "role": "model"
                        }

                    # Turn complete - MUST come AFTER all transcriptions so frontend can aggregate first
                    if content.turn_complete:
                        logger.debug("Turn complete")
                        yield {"type": "turn_complete"}
                        self._reset_timing()

                # Process tool calls
                if response.tool_call and response.tool_call.function_calls:
                    for fc in response.tool_call.function_calls:
                        logger.info(f"Tool call: {fc.name} with args: {fc.args}")
                        # Safely convert args to dict
                        try:
                            args_dict = dict(fc.args) if fc.args else {}
                        except (TypeError, AttributeError):
                            args_dict = {}
                        # Generate fallback ID if fc.id is None
                        # Some Gemini responses may not include an ID
                        tool_call_id = fc.id if fc.id else f"tc_{uuid.uuid4().hex[:12]}"
                        if not fc.id:
                            logger.warning(
                                f"Tool call '{fc.name}' has no ID, generated fallback: {tool_call_id}"
                            )
                        yield {
                            "type": "tool_call",
                            "id": tool_call_id,
                            "name": fc.name,
                            "args": args_dict
                        }

                # Process tool call cancellations (e.g., user interruption)
                if response.tool_call_cancellation:
                    cancelled_ids = []
                    if (hasattr(response.tool_call_cancellation, 'ids')
                            and response.tool_call_cancellation.ids):
                        cancelled_ids = list(response.tool_call_cancellation.ids)
                    logger.info(
                        f"Tool call cancellation received for IDs: {cancelled_ids}"
                    )
                    yield {
                        "type": "tool_call_cancellation",
                        "ids": cancelled_ids
                    }

        except asyncio.CancelledError:
            # Task was cancelled - normal during session stop
            logger.debug("Receive task cancelled")
            raise
        except Exception as e:
            # Log and yield error, but don't crash
            # Common exceptions: WebSocket closed, connection reset
            error_str = str(e)
            if "close" in error_str.lower() or "connection" in error_str.lower():
                logger.info(f"Connection closed during receive: {e}")
            else:
                logger.error(f"Error receiving messages: {e}")
            yield {"type": "error", "error": error_str}

    def _reset_timing(self) -> None:
        """Reset timing variables for next request"""
        self._first_byte_time = None
        self._request_start_time = None

    @property
    def is_connected(self) -> bool:
        """Check if connected to Gemini Live API"""
        return self._is_connected

    def get_config_dict(self) -> dict:
        """Get configuration as dictionary for client"""
        return {
            "model": MODEL_NAME,
            "project": PROJECT_ID,
            "location": LOCATION,
            "voice": self.voice_name,
            "endpoint_mode": self.endpoint_mode.value,
            "endpoint": self._endpoint,
            "vad": {
                "disabled": self.vad_disabled,
                "start_sensitivity": self.vad_start_sensitivity,
                "end_sensitivity": self.vad_end_sensitivity,
                "prefix_padding_ms": self.vad_prefix_padding_ms,
                "silence_duration_ms": self.vad_silence_duration_ms,
            }
        }
