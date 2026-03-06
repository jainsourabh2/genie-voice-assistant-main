# Tool call handler with async execution
# Uses asyncio.create_task() for non-blocking tool execution
# Gemini handles interim acknowledgment via RULE 4 in system instructions
# We only send the FINAL tool response to Gemini after execution
# Deduplicates tool calls to prevent duplicate processing
import asyncio
import hashlib
import json
import time
from typing import Callable, Any, Dict, Optional, Awaitable

from datetime import datetime

from config import TOOL_EXECUTION_DELAY, DEDUP_COOLDOWN_SECONDS
from tool_implementations import execute_tool
from logger import get_logger

logger = get_logger("tool_handler")


class ToolHandler:
    """
    Handles tool calls with background execution and deduplication.

    Flow:
    1. Tool call received from Gemini
    2. Check for duplicates (by ID or content hash) - skip if already in-flight
    3. Gemini speaks its own acknowledgment via RULE 4 in system instructions
    4. Wait for execution_delay (default 8s) to allow Gemini to speak
    5. Execute actual tool function asynchronously
    6. Send FINAL response via send_tool_response() to Gemini
    7. This does NOT block receiving the next user turn

    NOTE: We do NOT send interim responses to Gemini. Gemini handles acknowledgments
    naturally via RULE 4 in system instructions ("Let me look into that...").

    Deduplication:
    - Tracks processed tool IDs for the entire session (never auto-cleared)
    - Tracks in-flight tool hashes with cooldown period after completion
    - Content hash stays in dedup set for a cooldown period after tool completes
    - This prevents the model from re-triggering the same tool after receiving
      the final response (a common cause of duplicate tool calls)
    - Only fully cleared on session end via cancel_all()
    """

    def __init__(
        self,
        send_tool_response: Optional[Callable[[str, str, Any], Awaitable[None]]] = None,
        send_interim_to_gemini: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
        on_tool_complete: Optional[Callable[[str, str, Any], Awaitable[None]]] = None,
        execution_delay: float = TOOL_EXECUTION_DELAY,
        session_id: Optional[str] = None
    ):
        """
        Initialize tool handler.

        Args:
            send_tool_response: Async function to send final tool response to Gemini
                               Signature: async (tool_id, tool_name, response) -> None
            send_interim_to_gemini: Async function to send PROCESSING status to Gemini.
                                   This unblocks the model so it can speak an acknowledgment.
                                   Without this, the model goes silent after emitting tool_call.
                                   Signature: async (tool_id, tool_name, message) -> None
            on_tool_complete: Callback when tool execution completes (for UI updates)
                             Signature: async (tool_id, tool_name, result) -> None
            execution_delay: Delay in seconds before executing tool (default: 8)
            session_id: Session ID for per-session state isolation
        """
        self.send_tool_response = send_tool_response
        self.send_interim_to_gemini = send_interim_to_gemini
        self.on_tool_complete = on_tool_complete
        self.execution_delay = execution_delay
        self.session_id = session_id
        self._pending_tasks: Dict[str, asyncio.Task] = {}
        # Track processed tool call IDs for the entire session (never auto-cleared)
        # Maps tool_id -> registration timestamp (monotonic)
        self._processed_tool_ids: Dict[str, float] = {}
        # Track in-flight tool hashes with cooldown-based expiry
        # Maps hash -> expiry timestamp (monotonic)
        # While in-flight: expiry = float('inf') (never expires)
        # After completion: expiry = completion_time + cooldown
        self._in_flight_tool_hashes: Dict[str, float] = {}
        # Cooldown period after tool completion before allowing same tool+args again
        self._dedup_cooldown = DEDUP_COOLDOWN_SECONDS

        logger.info(f"ToolHandler initialized with {execution_delay}s delay")

    def _compute_tool_hash(self, tool_name: str, args: Dict[str, Any]) -> str:
        """
        Compute a hash for a tool call based on name and arguments.
        Used to detect duplicate tool calls even when IDs differ.
        """
        # Sort args for consistent hashing
        args_str = json.dumps(args, sort_keys=True, default=str)
        hash_input = f"{tool_name}:{args_str}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    def is_duplicate_and_register(
        self, tool_id: str, tool_name: str, args: Dict[str, Any]
    ) -> bool:
        """
        Check if a tool call is a duplicate AND register it atomically if not.
        This is a synchronous check that should be called BEFORE any async operations.

        Dedup strategy:
        - Tool IDs are tracked for the entire session (never auto-cleared)
        - Content hashes are tracked with a cooldown period after completion
        - While a tool is in-flight, its hash never expires (expiry = inf)
        - After completion, the hash stays for cooldown seconds to prevent
          the model from re-triggering the same tool after receiving the response

        Returns:
            True if the tool call is a duplicate and should be skipped.
            False if this is a new tool call (now registered) that should be processed.
        """
        now = time.monotonic()
        # Purge expired hash entries first
        self._purge_expired(now)

        # Check for exact ID duplicate (IDs never expire within session)
        if tool_id in self._processed_tool_ids:
            logger.warning(
                f"[DEDUP] Skipping duplicate tool call by ID: {tool_name} (id={tool_id})"
            )
            return True

        # Check for content-based duplicate (in-flight or within cooldown)
        tool_hash = self._compute_tool_hash(tool_name, args)
        if tool_hash in self._in_flight_tool_hashes:
            expiry = self._in_flight_tool_hashes[tool_hash]
            if now < expiry:
                remaining = expiry - now if expiry != float('inf') else 'inf (in-flight)'
                logger.warning(
                    f"[DEDUP] Skipping duplicate tool call by content: {tool_name} "
                    f"(id={tool_id}, hash={tool_hash}, expires_in={remaining})"
                )
                return True
            else:
                # Expired entry, remove it and allow through
                del self._in_flight_tool_hashes[tool_hash]

        # Not a duplicate - register atomically
        self._processed_tool_ids[tool_id] = now
        # Set to infinity while in-flight (never expires until completion)
        self._in_flight_tool_hashes[tool_hash] = float('inf')

        logger.info(
            f"[DEDUP] Registered unique tool call: {tool_name} (id={tool_id}, hash={tool_hash})"
        )
        return False

    def _purge_expired(self, now: float) -> None:
        """Remove expired entries from dedup hash tracking."""
        expired = [h for h, exp in self._in_flight_tool_hashes.items() if now >= exp]
        for h in expired:
            del self._in_flight_tool_hashes[h]
            logger.debug(f"[DEDUP] Purged expired hash entry: {h}")

    async def handle_tool_call(
        self,
        tool_id: str,
        tool_name: str,
        args: Dict[str, Any]
    ) -> bool:
        """
        Handle a tool call with non-blocking execution.

        IMPORTANT: This method assumes is_duplicate_and_register() was called first
        and returned False. The tool call should already be registered.

        Flow:
        1. Notify UI about interim response
        2. Schedule background execution with asyncio.create_task()
        3. Returns immediately - does NOT block the receive loop

        Args:
            tool_id: Unique identifier for this tool call
            tool_name: Name of the tool to execute
            args: Arguments for the tool

        Returns:
            True if the tool call execution was scheduled
        """
        # Compute hash for logging and cleanup callback
        tool_hash = self._compute_tool_hash(tool_name, args)

        logger.info(f"Handling tool call: {tool_name} (id={tool_id}, hash={tool_hash})")

        # Send interim PROCESSING response to unblock the model for speech.
        # Without this, the model goes silent after emitting tool_call + turn_complete.
        # The model needs this FunctionResponse to speak its acknowledgment
        # (e.g., "Sure, let me capture that for you").
        # The cooldown-based dedup prevents re-triggers from the double-response pattern.
        if self.send_interim_to_gemini:
            try:
                await self.send_interim_to_gemini(tool_id, tool_name, "")
                logger.info(f"Sent PROCESSING status to Gemini for {tool_name}")
            except Exception as e:
                logger.error(f"Failed to send PROCESSING status to Gemini: {e}")

        # Schedule background execution with delay using asyncio.create_task()
        # This is NON-BLOCKING - the method returns immediately
        task = asyncio.create_task(
            self._execute_with_delay(tool_id, tool_name, args, tool_hash)
        )
        self._pending_tasks[tool_id] = task

        # Add callback to clean up when done (pass task for outcome-aware cleanup)
        task.add_done_callback(lambda t: self._cleanup_task(tool_id, tool_hash, t))

        logger.debug(
            f"Scheduled tool execution for {tool_name} with {self.execution_delay}s delay"
        )
        return True

    async def _execute_with_delay(
        self,
        tool_id: str,
        tool_name: str,
        args: Dict[str, Any],
        tool_hash: str
    ) -> Any:
        """
        Execute tool and send final response to Gemini.

        The delay allows Gemini to speak the interim response (e.g., "Let me look
        into that for you") before receiving the final tool result. Without this
        delay, the final response arrives immediately and Gemini may skip speaking
        the interim acknowledgment.
        """
        start_time = datetime.now()

        try:
            # Wait for configured delay to allow Gemini to speak interim response
            # This is critical - without the delay, the model receives the final
            # response immediately and may skip vocalizing the interim message
            if self.execution_delay > 0:
                logger.info(
                    f"Waiting {self.execution_delay}s before executing {tool_name} "
                    "(allowing interim speech)"
                )
                await asyncio.sleep(self.execution_delay)

            logger.info(f"Executing tool: {tool_name}")
            result = await self._execute_tool(tool_name, args)

            # Mark as final response
            result["is_interim"] = False

            execution_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Tool {tool_name} completed in {execution_time:.2f}s")

            # Send final response to Gemini via send_tool_response()
            if self.send_tool_response:
                try:
                    await self.send_tool_response(tool_id, tool_name, result)
                    logger.info(f"Sent final tool response to Gemini for {tool_name}")
                except Exception as e:
                    logger.error(f"Failed to send final response to Gemini: {e}")

            # Notify UI about completion
            if self.on_tool_complete:
                try:
                    await self.on_tool_complete(tool_id, tool_name, result)
                except Exception as e:
                    logger.error(f"Failed to notify tool complete: {e}")

            return result

        except asyncio.CancelledError:
            logger.warning(f"Tool execution cancelled: {tool_name}")
            raise
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name} - {e}")
            error_result = {
                "success": False,
                "error": str(e),
                "is_interim": False
            }
            # Still send error response to Gemini
            if self.send_tool_response:
                try:
                    await self.send_tool_response(tool_id, tool_name, error_result)
                except Exception as send_err:
                    logger.error(f"Failed to send error response to Gemini: {send_err}")

            if self.on_tool_complete:
                try:
                    await self.on_tool_complete(tool_id, tool_name, error_result)
                except Exception as cb_err:
                    logger.error(f"Failed to notify tool error: {cb_err}")

            return error_result

    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """
        Execute the actual tool logic using tool_implementations.
        Uses async tool functions that return mock data (to be replaced with real APIs).
        """
        # Pass session_id for per-session state isolation
        result = await execute_tool(tool_name, args, session_id=self.session_id)
        return result

    def _cleanup_task(
        self, tool_id: str, tool_hash: str, task: asyncio.Task
    ) -> None:
        """
        Context-aware cleanup based on how the task finished.

        - Success: normal cooldown to prevent model re-trigger
        - Cancelled: clear dedup entirely so user can retry immediately
        - Failed: 1s micro-cooldown (block re-trigger, allow quick retry)
        """
        if tool_id in self._pending_tasks:
            del self._pending_tasks[tool_id]

        if task.cancelled():
            # Tool was cancelled (user interruption / tool_call_cancellation)
            # Clear dedup entirely — the tool never executed, user should retry
            self._processed_tool_ids.pop(tool_id, None)
            if tool_hash:
                self._in_flight_tool_hashes.pop(tool_hash, None)
            logger.debug(
                f"[DEDUP] Cancelled task {tool_id} cleared from dedup tracking"
            )
            return

        # Check if tool execution failed (returned success=False)
        tool_failed = False
        try:
            result = task.result()
            if isinstance(result, dict) and result.get("success") is False:
                tool_failed = True
        except Exception:
            tool_failed = True

        if tool_failed:
            # Failed tool: 1s micro-cooldown blocks model re-trigger
            # but allows user retry almost immediately
            if tool_hash and tool_hash in self._in_flight_tool_hashes:
                self._in_flight_tool_hashes[tool_hash] = time.monotonic() + 1.0
            logger.debug(
                f"[DEDUP] Failed task {tool_id}, 1s micro-cooldown for hash {tool_hash}"
            )
        else:
            # Successful tool: normal cooldown to prevent model re-trigger
            if tool_hash and tool_hash in self._in_flight_tool_hashes:
                self._in_flight_tool_hashes[tool_hash] = (
                    time.monotonic() + self._dedup_cooldown
                )
                logger.debug(
                    f"[DEDUP] Task {tool_id} completed, hash {tool_hash} "
                    f"in cooldown for {self._dedup_cooldown}s"
                )

        logger.debug(f"Cleaned up task: {tool_id}")

    async def cancel_tool(self, tool_id: str) -> bool:
        """Cancel a pending tool execution"""
        task = self._pending_tasks.get(tool_id)
        if task and not task.done():
            task.cancel()
            logger.info(f"Cancelled tool execution: {tool_id}")
            return True
        return False

    def cancel_tools_by_ids(self, tool_ids: list) -> int:
        """
        Cancel specific tool calls by their IDs.
        Used when Gemini sends tool_call_cancellation messages (e.g., user interruption).
        """
        cancelled = 0
        for tool_id in tool_ids:
            task = self._pending_tasks.get(tool_id)
            if task and not task.done():
                task.cancel()
                cancelled += 1
                logger.info(f"[CANCEL] Cancelled tool execution: {tool_id}")
        if cancelled:
            logger.info(f"[CANCEL] Cancelled {cancelled}/{len(tool_ids)} tool executions")
        return cancelled

    async def cancel_all(self) -> int:
        """Cancel all pending tool executions and clear deduplication tracking"""
        cancelled = 0
        for tool_id, task in list(self._pending_tasks.items()):
            if not task.done():
                task.cancel()
                cancelled += 1
        self._pending_tasks.clear()
        # Clear all deduplication tracking on session end
        self._processed_tool_ids.clear()
        self._in_flight_tool_hashes.clear()
        logger.info(f"Cancelled {cancelled} pending tool executions, cleared dedup tracking")
        return cancelled

    def get_pending_count(self) -> int:
        """Get number of pending tool executions"""
        return len([t for t in self._pending_tasks.values() if not t.done()])

    def get_pending_tools(self) -> list:
        """Get list of pending tool IDs"""
        return [tid for tid, task in self._pending_tasks.items() if not task.done()]


class ToolExecutor:
    """
    Async context manager for tool execution with cleanup.
    Use when you need to ensure tool tasks are cancelled on exit.
    """

    def __init__(self, handler: ToolHandler):
        self.handler = handler

    async def __aenter__(self) -> ToolHandler:
        return self.handler

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.handler.cancel_all()
