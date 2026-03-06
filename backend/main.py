# WebSocket server entry point for Voice Chatbot
import asyncio
import json
import time
from datetime import datetime
from typing import Optional

import websockets
from websockets.server import WebSocketServerProtocol

from config import WS_HOST, WS_PORT, ACTIVITY_END_THRESHOLD, EndpointMode
from logger import get_logger
from models import (
    MessageType,
    InitMessage,
    VADSettings,
    SessionStartedMessage,
    TranscriptMessage,
    AudioResponseMessage,
    ToolCallMessage,
    ToolResponseMessage,
    TurnCompleteMessage,
    SessionEndedMessage,
    ErrorMessage,
    InterruptedMessage,
)
from gemini_client import GeminiLiveClient
from session_manager import SessionManager
from audio_handler import AudioHandler
from tool_handler import ToolHandler
from tool_implementations import cleanup_session_state

logger = get_logger("main")


class VoiceChatServer:
    """WebSocket server for voice chatbot"""

    def __init__(self):
        self.session_manager = SessionManager()
        self.audio_handler = AudioHandler()
        self._active_connections: dict[str, dict] = {}
        logger.info("VoiceChatServer initialized")

    async def handle_connection(self, websocket: WebSocketServerProtocol):
        """Handle a single WebSocket connection"""
        connection_id = id(websocket)
        logger.info(f"New connection: {connection_id}")

        gemini_client: Optional[GeminiLiveClient] = None
        tool_handler: Optional[ToolHandler] = None
        session_id: Optional[str] = None
        receive_task: Optional[asyncio.Task] = None
        last_audio_time: float = 0
        activity_end_sent: bool = False

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type")

                    # Handle init message
                    if msg_type == MessageType.INIT.value:
                        logger.info("Received init message")

                        # Parse init message
                        vad_settings = data.get("vad_settings", {})
                        system_instruction = data.get("system_instruction")
                        voice_name = data.get("voice_name", "Aoede")

                        # Parse endpoint mode (AUTOPUSH or PROD)
                        endpoint_mode_str = data.get("endpoint_mode")
                        endpoint_mode = None
                        if endpoint_mode_str:
                            try:
                                endpoint_mode = EndpointMode(endpoint_mode_str)
                                logger.info(f"Using endpoint mode: {endpoint_mode.value}")
                            except ValueError:
                                logger.warning(
                                    f"Invalid endpoint_mode '{endpoint_mode_str}', using default"
                                )

                        # Create Gemini client with full VAD configuration
                        gemini_client = GeminiLiveClient(
                            system_instruction=system_instruction,
                            vad_disabled=vad_settings.get("disabled"),
                            vad_start_sensitivity=vad_settings.get("start_sensitivity", "HIGH"),
                            vad_end_sensitivity=vad_settings.get("end_sensitivity", "HIGH"),
                            vad_prefix_padding_ms=vad_settings.get("prefix_padding_ms"),
                            vad_silence_duration_ms=vad_settings.get("silence_duration_ms"),
                            voice_name=voice_name,
                            endpoint_mode=endpoint_mode
                        )

                        # Create session
                        session = self.session_manager.create_session(
                            config=gemini_client.get_config_dict()
                        )
                        session_id = session.session_id

                        # Create tool handler with callbacks
                        # The tool handler sends:
                        # 1. PROCESSING status to Gemini (model generates its own interim response)
                        # 2. Final response to Gemini (after tool execution completes)
                        # Note: We use closures to capture websocket and session_id
                        # The callbacks are async functions that match the expected signatures
                        async def on_complete(tid: str, name: str, result: dict) -> None:
                            await self._handle_tool_complete(
                                websocket, session_id, tid, name, result
                            )

                        tool_handler = ToolHandler(
                            send_tool_response=gemini_client.send_tool_response,
                            send_interim_to_gemini=gemini_client.send_interim_tool_response,
                            on_tool_complete=on_complete,
                            session_id=session_id
                        )

                        # Connect to Gemini
                        await gemini_client.connect()

                        # Start receiving messages from Gemini
                        receive_task = asyncio.create_task(
                            self._receive_gemini_messages(
                                websocket, gemini_client, tool_handler, session_id
                            )
                        )

                        # Send session started message
                        response = SessionStartedMessage(
                            session_id=session_id,
                            model=gemini_client.get_config_dict()["model"],
                            config=gemini_client.get_config_dict()
                        )
                        await websocket.send(response.model_dump_json())
                        logger.info(f"Session started: {session_id}")

                    # Handle audio message
                    elif msg_type == MessageType.AUDIO.value:
                        if not gemini_client or not gemini_client.is_connected:
                            logger.warning("Received audio but no active session")
                            continue

                        audio_data = data.get("data", "")
                        if audio_data:
                            # Update last audio time for activity detection
                            current_time = time.time()

                            # Check if we need to reset activity_end flag
                            if activity_end_sent:
                                activity_end_sent = False

                            last_audio_time = current_time
                            self.session_manager.update_last_audio_time(session_id, current_time)

                            # Send audio to Gemini
                            await gemini_client.send_audio_base64(audio_data)

                    # Handle stop message
                    elif msg_type == MessageType.STOP.value:
                        logger.info(f"Stop requested for session: {session_id}")

                        # Cancel tool executions
                        if tool_handler:
                            await tool_handler.cancel_all()

                        # Disconnect from Gemini
                        if gemini_client:
                            await gemini_client.disconnect()

                        # Cancel receive task
                        if receive_task:
                            receive_task.cancel()
                            try:
                                await receive_task
                            except asyncio.CancelledError:
                                pass

                        # End session
                        if session_id:
                            self.session_manager.end_session(session_id)
                            cleanup_session_state(session_id)

                            response = SessionEndedMessage(session_id=session_id)
                            await websocket.send(response.model_dump_json())

                        # Reset state
                        gemini_client = None
                        tool_handler = None
                        receive_task = None

                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                    error = ErrorMessage(error="Invalid JSON message", details=str(e))
                    await websocket.send(error.model_dump_json())

                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    error = ErrorMessage(error="Message processing error", details=str(e))
                    await websocket.send(error.model_dump_json())

        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"Connection closed: {e.code} {e.reason}")

        except Exception as e:
            logger.error(f"Connection error: {e}")

        finally:
            # Cleanup
            if tool_handler:
                await tool_handler.cancel_all()

            if gemini_client:
                await gemini_client.disconnect()

            if receive_task and not receive_task.done():
                receive_task.cancel()

            if session_id:
                self.session_manager.end_session(session_id)
                cleanup_session_state(session_id)

            logger.info(f"Connection cleaned up: {connection_id}")

    async def _receive_gemini_messages(
        self,
        websocket: WebSocketServerProtocol,
        client: GeminiLiveClient,
        tool_handler: ToolHandler,
        session_id: str
    ):
        """Receive and forward messages from Gemini to client"""
        try:
            async for msg in client.receive_messages():
                msg_type = msg.get("type")

                if msg_type == "audio":
                    logger.debug(f"Received audio from Gemini, size={len(msg['data'])} bytes")
                    response = AudioResponseMessage(
                        data=msg["data"],
                        ttfb_ms=msg.get("ttfb_ms")
                    )
                    await websocket.send(response.model_dump_json())
                    logger.debug("Sent audio response to client")

                elif msg_type == "transcript":
                    self.session_manager.add_transcript(
                        session_id,
                        msg["role"],
                        msg["text"]
                    )
                    response = TranscriptMessage(
                        role=msg["role"],
                        text=msg["text"],
                        is_final=True
                    )
                    await websocket.send(response.model_dump_json())

                elif msg_type == "text":
                    # Text from model (transcription)
                    response = TranscriptMessage(
                        role="model",
                        text=msg["text"],
                        is_final=False
                    )
                    await websocket.send(response.model_dump_json())

                elif msg_type == "tool_call":
                    # IMPORTANT: Check for duplicate AND register BEFORE notifying client
                    # This prevents the UI from showing duplicate tool calls
                    # The check and registration is atomic (synchronous) to avoid race conditions
                    if tool_handler.is_duplicate_and_register(
                        msg["id"], msg["name"], msg["args"]
                    ):
                        # Skip duplicate tool call - do not record or notify client
                        logger.debug(
                            f"Duplicate tool call filtered before UI notification: {msg['name']}"
                        )
                        continue

                    # Record tool call (only for non-duplicates)
                    self.session_manager.add_tool_call(
                        session_id,
                        msg["id"],
                        msg["name"],
                        msg["args"]
                    )

                    # Notify client (only for non-duplicates)
                    response = ToolCallMessage(
                        id=msg["id"],
                        name=msg["name"],
                        args=msg["args"]
                    )
                    await websocket.send(response.model_dump_json())

                    # Handle tool call (triggers background execution)
                    # This will always return True now since we pre-filtered duplicates
                    await tool_handler.handle_tool_call(
                        msg["id"],
                        msg["name"],
                        msg["args"]
                    )

                elif msg_type == "tool_call_cancellation":
                    # Gemini cancelled tool calls (e.g., user interrupted)
                    cancelled_ids = msg.get("ids", [])
                    if cancelled_ids:
                        cancelled_count = tool_handler.cancel_tools_by_ids(
                            cancelled_ids
                        )
                        logger.info(
                            f"Cancelled {cancelled_count} tool executions "
                            f"from Gemini cancellation: {cancelled_ids}"
                        )

                elif msg_type == "turn_complete":
                    response = TurnCompleteMessage()
                    await websocket.send(response.model_dump_json())

                elif msg_type == "interrupted":
                    response = InterruptedMessage()
                    await websocket.send(response.model_dump_json())

                elif msg_type == "error":
                    response = ErrorMessage(
                        error=msg.get("error", "Unknown error")
                    )
                    await websocket.send(response.model_dump_json())

        except asyncio.CancelledError:
            logger.debug("Gemini receive task cancelled")
        except Exception as e:
            logger.error(f"Error receiving from Gemini: {e}")
            error = ErrorMessage(error="Gemini connection error", details=str(e))
            try:
                await websocket.send(error.model_dump_json())
            except:
                pass

    async def _handle_tool_complete(
        self,
        websocket: WebSocketServerProtocol,
        session_id: str,
        tool_id: str,
        tool_name: str,
        result: dict
    ):
        """
        Handle tool completion: update session and notify client.
        Note: The tool response to Gemini is sent by ToolHandler directly via
        send_tool_response callback. This method only updates session state
        and notifies the frontend.
        """
        try:
            # Update session state
            self.session_manager.update_tool_response(session_id, tool_id, result)

            # Notify frontend client
            response = ToolResponseMessage(
                id=tool_id,
                name=tool_name,
                response=result
            )
            await websocket.send(response.model_dump_json())

            logger.info(f"Tool completion notified to frontend: {tool_name}")

        except Exception as e:
            logger.error(f"Failed to handle tool complete: {e}")

    async def start(self):
        """Start the WebSocket server"""
        logger.info(f"Starting WebSocket server on {WS_HOST}:{WS_PORT}")

        async with websockets.serve(
            self.handle_connection,
            WS_HOST,
            WS_PORT,
            ping_interval=20,
            ping_timeout=20
        ):
            logger.info(f"WebSocket server running on ws://{WS_HOST}:{WS_PORT}")
            await asyncio.Future()  # Run forever


async def main():
    """Main entry point"""
    server = VoiceChatServer()
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())
