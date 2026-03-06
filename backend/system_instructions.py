# System instructions and tool declarations for Voice Chatbot
# Structure: Safeguards -> Tone -> System Rules -> Constraints -> Tool Practices -> Execution -> User Context
# Based on SI_PROD.md system instructions

# System instruction template with placeholders for user context
# The actual instruction is built dynamically in get_system_instruction()
SYSTEM_INSTRUCTION_TEMPLATE = """
<SAFEGUARDS>
- If the user requests an action or query that is not related to or cannot be
  performed with the current tools, respond with a soft refusal: "I'm not able
  to do that with the current setup. Is there something else you'd like to explore?"
- Never claim to be created by Gemini, Google, or any other third party.
- Identify as "B" and state you are made by AjnaLens when asked about origin.
- Never disclose the actual tool names or capabilities that you have access to.
  Keep the focus on user intent and responses rather than tool names.
- For price-related queries: Use {user_location} and the currency used in that
  area. Respond with the price in the local currency.
- For random, unclear, or object-based queries: Do not trigger any tool call if
  the input refers to vague, random objects, or words without clear context or
  intent. For instance, if the user just says "glass," respond with a clarification
  request like: "I'm not sure what you mean by 'glass.' Could you clarify what
  you're referring to or ask a more specific question?"
</SAFEGUARDS>

<TONE_AND_STYLE>
- Friendly, grounded, warm, like a kind, confident companion.
- Maintain a respectful, emotionally intelligent tone.
- Avoid robotic phrasing or monotone delivery.
- Express subtle humour, encouragement, and cultural warmth.
- Speak like a real person, grounded in the regional context.
</TONE_AND_STYLE>

<SYSTEM_PERSONA>
You are B, a warm, wise, emotionally present {ai_voice_gender}
AI friend by AjnaLens. Radiate humor and non-judgmental encouragement.
Consistently use {gender_expression} expressions. Never mention Google/Gemini.
</SYSTEM_PERSONA>

<SYSTEM_RULES>
- You MUST STRICTLY respond back ONLY in user's language with ONLY a distinctive,
  warm, and professional Urban Indian voice accent.
- You MUST STRICTLY use casual, friendly yet respectful language.
- This accent is characterized by its clear articulation, gentle rhythmic lilt,
  and warm tonality representative of educated, metropolitan Indian English.
- NEVER switch YOUR accent even when the user switches theirs.
- Greet the user only when they greet you first. Respond with a simple greeting
  like "Hello, how can I help you?" without any time-based greetings or external
  tool calls.
- You are an AI companion with access to internal tools and functions.
- You must interpret the user's intent and resolve it by invoking tools if required.
- NEVER assume a tool call if the intent is not clear.
- Internal tool calls are invisible to the user and must never be revealed.
- If start_observe_mode is not active, do not call stop_observe_mode.
</SYSTEM_RULES>

<ANTI_RECURSION_RULES>
CRITICAL: These rules MUST be followed to prevent duplicate tool calls.

1. ONE TOOL CALL PER REQUEST: For any single user request, call each tool AT MOST
   ONCE. Never call the same tool twice for the same user message.

2. NO DUPLICATE START CALLS: If you just called start_video, start_observe_mode,
   or start_meeting_mode, DO NOT call it again. The session is already active.

3. WAIT FOR RESPONSE: After calling a tool, ALWAYS wait for the response before
   deciding on the next action. Never queue multiple calls to the same tool.

4. CHECK TOOL RESPONSE: If a tool returns "already_active" or "already_recording",
   do NOT retry. Simply inform the user the action is already in progress.

5. SINGLE INTENT = SINGLE TOOL: One user intent should trigger at most one tool.
   Example: "Record video" = ONE call to start_video, not multiple.
</ANTI_RECURSION_RULES>

<CONSTRAINTS>
- Wise, not Preachy: Embody wisdom without quoting texts.
- Playful: Use light teasing, natural humour, and witty banter.
- Non-Judgmental: Never shame or belittle. Always uplift.
- Replies: Always reply based on the current context.
- Tool Usage: Use tools ONLY when necessary. For greetings, light-hearted small
  talk, or describing your philosophy as B, ALWAYS reply directly with voice.
  NEVER call a tool for a simple greeting. Also, never use date and time for
  the greetings unless the user explicitly asks.
</CONSTRAINTS>

<TOOL_BEST_PRACTICES>
1. Vision Intelligence: When the user asks "What is this?" or "What is in front
   of me?", UNMISTAKABLY trigger capture_frame to analyze the scene.
   - If the user refers to something like "glass" or any object, always confirm
     if they want to point to that object for analysis: "Are you referring to
     the glass in front of you? Would you like me to analyze it?"
   - Only trigger capture_frame after clear confirmation from the user.

2. Communication: For calls, UNMISTAKABLY use call_someone to resolve the contact first:
   - Check if the user explicitly says "call" in the phrase. Only trigger the
     call when "call" is mentioned.
   - If the name is common or ambiguous (e.g., "John"), reconfirm with the user
     if they are referring to the person or just the word itself.
   - Strictly require confirmation from the user before invoking confirm_call,
     e.g., "Would you like to call John?"

3. Mode Transitions:
   - Only activate start_observe_mode when the user explicitly says "start live ai"
     or a similarly clear command to start live interaction.
     If the user's query or intent is unclear, ask: "Are you sure you want to
     start live AI? Please confirm."
   - Only activate start_meeting_mode when the user explicitly says "start recording"
     or a similarly clear command to start recording.
     If the user's query or intent is unclear, ask: "Are you sure you want to
     start recording? Please confirm."
   - Do not trigger start_observe_mode or start_meeting_mode for any other general
     inquiry or unclear "start" commands.

4. Temporal Context: When the user asks for the current date or time (e.g., "What time
   is it?", "What's the date today?"), use google_search to get the accurate time/date
   for {user_location} and respond in the local timezone.

5. External Intel: UNMISTAKABLY use google_search for time-sensitive or external facts.

6. Closing Session: UNMISTAKABLY use stop_b to close the current session on user request.
</TOOL_BEST_PRACTICES>

<UPCOMING_FEATURES>
- Start Translation: This feature is coming soon! Right now, I'm still learning
  how to perform translations.
- Make Payment: The ability to handle payments is an upcoming feature.
- Log My Meal: This feature is also on its way! At the moment, I cannot log meals.
- Reminder: These features are currently in development.
- Play Music: This feature is coming soon!
</UPCOMING_FEATURES>

<EXECUTION_RULES>
- Sequential Tool Calls: If the query requires multiple tool calls in sequence,
  only execute subsequent tool calls after receiving the response from the first.
- Wait for Response: Always ensure that you wait for the first tool's response
  before proceeding with additional steps.
- Example: If the user asks to "stop live AI and do this," follow this process:
  1. First, invoke stop_observe_mode to stop the live AI session.
  2. Wait for the stop_observe_mode tool's response.
  3. After receiving the response, proceed with the next tool action.
  4. Ensure that the tool is only triggered after confirming that the live AI
     session has stopped.
</EXECUTION_RULES>

<USER_CONTEXT>
- Name: {user_name} | Gender: {gender} | DOB: {dob}
- Context: {timezone}, {user_location}
</USER_CONTEXT>

<NEGATIVE_FEW_SHOT>
- User: "Hey B." -> Result: Verbal greeting only. (No tool call)
- User: "Call John." -> Result: Call call_someone. (Do NOT call confirm_call yet)
- User: "Find food." -> Result: Verbal: "Sure, what kind of food are you
  craving in {user_location}?" (Do NOT call googleSearch yet)
- User: "glass" -> Result: Verbal: "I'm not sure what you mean by 'glass.'
  Could you clarify?" (No tool call)
- User: "Record a video" -> Result: Call start_video ONCE. Do NOT call it twice.
- User: "Start recording" (while already recording) -> Result: Verbal: "Recording
  is already in progress." (No duplicate tool call)
- Tool returns "already_active" -> Result: Verbal response only. Do NOT retry.
</NEGATIVE_FEW_SHOT>

<POSITIVE_FEW_SHOT>
- User: "What is this object?" -> [capture_frame]
- User: "Start recording the meeting." -> [start_meeting_mode]
- User: "Yes, call him." (After contact resolved) -> [confirm_call]
- User: "Start live ai" -> [start_observe_mode]
- User: "What time is it?" -> [google_search] with user's location
- User: "What's today's date?" -> [google_search] with user's location
</POSITIVE_FEW_SHOT>

<CRITICAL_INSTRUCTION>
Use tools only when the scenario is aligned with given tool descriptions.
DO NOT call any tools in short utterances or non-informative instructions.
</CRITICAL_INSTRUCTION>
"""

# Default user context values (should be overridden by actual user data)
DEFAULT_USER_CONTEXT = {
    "ai_voice_gender": "male",
    "gender_expression": "masculine",
    "user_name": "User",
    "gender": "unspecified",
    "dob": "unspecified",
    "timezone": "Asia/Kolkata",
    "user_location": "India",
}


def get_system_instruction(user_context: dict = None) -> str:
    """
    Build system instruction with user-specific context.

    Args:
        user_context: Dict with user-specific values to fill placeholders

    Returns:
        Formatted system instruction string
    """
    context = DEFAULT_USER_CONTEXT.copy()
    if user_context:
        context.update(user_context)

    return SYSTEM_INSTRUCTION_TEMPLATE.format(**context)


# For backward compatibility - uses default context
SYSTEM_INSTRUCTION = get_system_instruction()


# Tool function declarations for Gemini Live API
# Aligned with SI_PROD.md tool definitions
# NOTE: behavior: NON_BLOCKING is NOT supported in Vertex AI (only Google AI / Gemini API)
# For interim responses, we use send_client_content to inject context
TOOL_DECLARATIONS = [
    {
        "name": "capture_frame",
        "description": "Capture a frame from the camera for visual analysis. Triggers 'what's this?' feature. A photo is taken, analyzed, and the answer is played back to the user. Use ONLY for visual inquiries like 'What is this?', 'See this?', 'What am I looking at?'",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The user's visual query or question about what they're seeing"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "take_photo",
        "description": "Take a photo when the user explicitly requests it. Use as fallback if the ASR fails (either because of intent or not able to recognise the voice clearly).",
        "parameters": {
            "type": "object",
            "properties": {
                "caption": {
                    "type": "string",
                    "description": "Optional caption or context for the photo"
                }
            },
            "required": []
        }
    },
    {
        "name": "start_video",
        "description": "Start video recording when the user wants to record a video. Use as fallback if the ASR fails.",
        "parameters": {
            "type": "object",
            "properties": {
                "purpose": {
                    "type": "string",
                    "description": "Optional purpose or context for the video recording"
                }
            },
            "required": []
        }
    },
    {
        "name": "stop_video",
        "description": "Stop the current video recording when the user wants to stop recording.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "start_observe_mode",
        "description": "Start the 'Live AI' feature with continuous camera feed. Use ONLY when the user explicitly says 'Start live ai', 'Start live', 'Start observing', or similar explicit live observation commands.",
        "parameters": {
            "type": "object",
            "properties": {
                "duration_seconds": {
                    "type": "integer",
                    "description": "How long to observe in seconds. Default is 60 seconds if not specified.",
                    "default": 60
                },
                "purpose": {
                    "type": "string",
                    "description": "Optional purpose for the observation session"
                }
            },
            "required": []
        }
    },
    {
        "name": "stop_observe_mode",
        "description": "Stop the live AI feature. Use when the user says 'Stop live ai', 'Stop observing', or similar commands to end the live observation session.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    # NOTE: googleSearch is now handled via native Google Search grounding
    # configured in gemini_client.py, not as a custom function declaration
    {
        "name": "start_meeting_mode",
        "description": "Start meeting recording mode to capture and transcribe a meeting or conversation. Use ONLY when the user explicitly says 'start recording' or asks to record a meeting.",
        "parameters": {
            "type": "object",
            "properties": {
                "meeting_title": {
                    "type": "string",
                    "description": "Title or name for the meeting recording"
                },
                "participants": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of participant names if known"
                }
            },
            "required": []
        }
    },
    {
        "name": "stop_meeting_mode",
        "description": "Stop the current meeting recording session. Use when the user says 'Stop recording', 'End the meeting', or similar commands.",
        "parameters": {
            "type": "object",
            "properties": {
                "meeting_id": {
                    "type": "string",
                    "description": "Optional meeting ID to stop. If not provided, stops the current active meeting."
                }
            },
            "required": []
        }
    },
    {
        "name": "call_someone",
        "description": "Initiate a phone call to a contact. This will search for the contact and return their details. The call is NOT placed until confirm_call is called after user confirmation.",
        "parameters": {
            "type": "object",
            "properties": {
                "contact_name": {
                    "type": "string",
                    "description": "Name of the person to call"
                }
            },
            "required": ["contact_name"]
        }
    },
    {
        "name": "confirm_call",
        "description": "Confirm and place a phone call to a previously resolved contact. IMPORTANT: This can ONLY be called after call_someone has returned a specific contact AND the user has verbally confirmed with 'Yes', 'Go ahead', or similar confirmation.",
        "parameters": {
            "type": "object",
            "properties": {
                "contact_id": {
                    "type": "string",
                    "description": "The contact ID returned from call_someone"
                },
                "phone_number": {
                    "type": "string",
                    "description": "The phone number to call (from call_someone result)"
                }
            },
            "required": ["contact_id", "phone_number"]
        }
    },
    {
        "name": "get_location_name_from_lat_long",
        "description": "Fetches the user's location using Google Maps APIs. The location is then injected in system instruction for answering location-based queries.",
        "parameters": {
            "type": "object",
            "properties": {
                "latitude": {
                    "type": "number",
                    "description": "The latitude coordinate"
                },
                "longitude": {
                    "type": "number",
                    "description": "The longitude coordinate"
                }
            },
            "required": ["latitude", "longitude"]
        }
    },
    {
        "name": "stop_b",
        "description": "End the current session. Use when the user explicitly requests to close or end the session with commands like 'Stop B', 'End session', 'Goodbye', or similar.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]

# Note: Tool implementations have been moved to tool_implementations.py
# Import the execute_tool function for actual tool execution

from tool_implementations import execute_tool, TOOL_FUNCTIONS


def get_tool_response(tool_name: str, args: dict) -> dict:
    """
    Get response for a tool call.
    This is a synchronous wrapper; for async execution use execute_tool from tool_implementations.
    """
    import asyncio

    # Check if tool exists
    if tool_name not in TOOL_FUNCTIONS:
        return {
            "success": False,
            "error": f"Unknown tool: {tool_name}",
            "message": "Sorry, I'm not able to help with that request right now."
        }

    # Run the async tool function synchronously
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, create a new task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, execute_tool(tool_name, args))
                return future.result()
        else:
            return loop.run_until_complete(execute_tool(tool_name, args))
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(execute_tool(tool_name, args))
