"""
Meeting Orchestrator Agent
Coordinates transcription, calendar management, and intelligent note-taking
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Annotated, Any, Sequence, Optional, List, Dict
from enum import Enum
import pytz
from dateutil import parser as dateparser
from difflib import SequenceMatcher

from openai import OpenAI
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

# Timezone configuration - Auto-handles EST/EDT
TIMEZONE = pytz.timezone('America/New_York')

# Load attendee mapping from file
def load_attendee_mapping():
    """Load attendee mapping from attendee_mapping.json"""
    try:
        with open('attendee_mapping.json', 'r') as f:
            mapping_data = json.load(f)
            return mapping_data
    except FileNotFoundError:
        # Fallback to hardcoded mapping if file not found
        # Note: _LOGGER not available during module initialization, using logging directly
        logging.getLogger(__name__).warning("attendee_mapping.json not found, using hardcoded mapping")
        return {
            "attendees": [
                {"primary_name": "rahual", "email": "rahual.rai@bison.howard.edu", "aliases": ["Rahual", "rahual rai"]},
                {"primary_name": "kritika", "email": "kritika.pant@bison.howard.edu", "aliases": ["Kritika", "kritika pant"]},
                {"primary_name": "biraj", "email": "biraj.dahal@bison.howard.edu", "aliases": ["Biraj", "biraj dahal"]}
            ],
            "default_domain": "example.com"
        }

# Load mapping at module initialization
_ATTENDEE_MAPPING = load_attendee_mapping()

def fuzzy_match_name(name: str, threshold: float = 0.8) -> Optional[Dict[str, Any]]:
    """
    Find attendee by fuzzy matching name against aliases
    Returns the attendee record if found, None otherwise
    """
    if not name:
        return None

    name_lower = name.lower().strip()

    # First try exact match
    for attendee in _ATTENDEE_MAPPING.get("attendees", []):
        if name_lower == attendee.get("primary_name", "").lower():
            return attendee

        # Check aliases
        for alias in attendee.get("aliases", []):
            if name_lower == alias.lower():
                return attendee

    # Then try fuzzy matching on aliases
    for attendee in _ATTENDEE_MAPPING.get("attendees", []):
        for alias in attendee.get("aliases", []):
            similarity = SequenceMatcher(None, name_lower, alias.lower()).ratio()
            if similarity >= threshold:
                _LOGGER.info(f"Fuzzy matched '{name}' to '{alias}' (score: {similarity})")
                return attendee

    # Generate email if no match found
    parts = name_lower.split()
    if len(parts) >= 2:
        generated_email = f"{parts[0]}.{parts[-1]}@{_ATTENDEE_MAPPING.get('default_domain', 'example.com')}"
    else:
        generated_email = f"{parts[0]}@{_ATTENDEE_MAPPING.get('default_domain', 'example.com')}"

    _LOGGER.info(f"No attendee match for '{name}', auto-generated email: {generated_email}")
    return {
        "primary_name": name_lower,
        "email": generated_email,
        "aliases": [name],
        "first_name": parts[0] if parts else name,
        "last_name": parts[-1] if len(parts) > 1 else ""
    }

def get_attendee_emails(attendee_names: List[str]) -> List[str]:
    """Convert list of attendee names to email addresses"""
    emails = []
    for name in attendee_names:
        attendee = fuzzy_match_name(name)
        if attendee and attendee.get("email"):
            emails.append(attendee["email"])
    return emails

# Legacy ATTENDEE_MAP for backward compatibility
ATTENDEE_MAP = {
    attendee.get("primary_name"): attendee.get("email")
    for attendee in _ATTENDEE_MAPPING.get("attendees", [])
}

# Import your existing calendar tool
from calender_tool import CalendarAgentTool, CalendarEvent
from email_tool import GmailAgentTool

# Import custom logging configuration
from logging_config import configure_logging

# Use custom colored logging
_LOGGER = configure_logging(__name__, logging.INFO)

# Initialize NVIDIA Nemotron client
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key="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"
)


# Helper functions for summary improvement
def strip_thinking_content(text: str) -> str:
    """Remove thinking/reasoning content from AI output"""
    import re

    # Remove <think> tags
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

    # Remove common thinking phrase patterns
    thinking_patterns = [
        r'(?:I|The model) (?:think|believe|consider|analyze|reason)',
        r'Based on (?:my analysis|my reasoning)',
        r'Therefore(?:,| I)',
        r'To summarize what I',
    ]

    for pattern in thinking_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # Clean up extra whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text).strip()

    return text


def extract_thinking_content(text: str) -> tuple:
    """
    Extract thinking/reasoning content from AI output
    Returns tuple of (thinking_content, cleaned_response)
    """
    import re

    # Extract content between <think> and </think> tags
    thinking_match = re.search(r'<think>(.*?)</think>', text, flags=re.DOTALL)
    thinking_content = thinking_match.group(1).strip() if thinking_match else None

    # Strip thinking tags from response
    cleaned_text = strip_thinking_content(text)

    return thinking_content, cleaned_text


def generate_calendar_link(event_id: str) -> str:
    """Generate Google Calendar edit link for an event"""
    if not event_id:
        return ""
    return f"https://calendar.google.com/calendar/u/0/r/eventedit/{event_id}"


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """Format datetime in readable format"""
    if dt is None:
        dt = datetime.now(TIMEZONE)
    return dt.strftime("%B %d, %Y at %I:%M %p %Z")


class ActionType(str, Enum):
    """Types of actions the orchestrator can take"""
    ADD_NOTES = "add_notes"
    CREATE_EVENT = "create_event"
    FIND_SLOT = "find_available_slot"
    UPDATE_EVENT = "update_event"


class MeetingAction(BaseModel):
    """Represents an action to take based on the meeting"""
    action_type: ActionType
    calendar_event_id: Optional[str] = None
    event_title: Optional[str] = None
    event_date: Optional[str] = None  # ISO format date if specified
    notes: Optional[str] = None
    duration_minutes: int = 60
    attendees: Optional[List[str]] = None  # List of attendee names (e.g., ["rahual", "kritika"])
    reasoning: str = ""


class ExecutionResult(BaseModel):
    """Structured execution result with metadata"""
    timestamp: str  # ISO format datetime
    status: str  # "success", "error", "warning"
    action_type: str  # Type of action performed
    message: str  # User-friendly description
    event_id: Optional[str] = None  # Calendar event ID if applicable
    technical_details: Optional[str] = None  # Event ID or error details


class OrchestratorState(BaseModel):
    """State for the orchestrator agent"""
    audio_transcript: str
    workflow_id: str = ""  # Unique ID for tracing this request through all workflow steps
    calendar_events: List[CalendarEvent] = []
    related_past_meetings: List[Dict[str, Any]] = []
    planned_actions: List[MeetingAction] = []
    execution_results: List[Dict[str, Any]] = []  # Can be old string format or new structured format
    execution_results_structured: List[ExecutionResult] = []  # New structured format
    next_steps: List[str] = []  # AI-suggested next steps
    messages: Annotated[Sequence[Any], add_messages] = []
    auto_execute: bool = True  # If False, skip execution phase for manual approval


class MeetingOrchestrator:
    """Main orchestrator that coordinates all agents and tools"""
    
    def __init__(self):
        self.calendar_tool = CalendarAgentTool()
        self.client = client
        self.email_tool = GmailAgentTool()
        
    def _call_nemotron(self, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        """Helper to call Nemotron with proper formatting and tracking"""
        import time

        # Add JSON formatting instructions to system prompt if needed
        if json_mode:
            system_prompt += "\n\nIMPORTANT: You must respond with ONLY valid JSON. No explanatory text before or after. Start with { or [ and end with } or ]."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # Track API call
        start_time = time.time()
        completion = self.client.chat.completions.create(
            model="nvidia/llama-3.3-nemotron-super-49b-v1.5",
            messages=messages,
            temperature=0.2,
            top_p=0.95,
            max_tokens=4096,
            stream=False
        )
        end_time = time.time()

        response_text = completion.choices[0].message.content
        latency_ms = (end_time - start_time) * 1000

        # Log call details for UI visualization
        call_details = {
            "timestamp": datetime.now(TIMEZONE).isoformat(),
            "model": "nvidia/llama-3.3-nemotron-super-49b-v1.5",
            "latency_ms": latency_ms,
            "json_mode": json_mode,
            "system_prompt_length": len(system_prompt),
            "user_prompt_length": len(user_prompt),
            "response_length": len(response_text),
            "preview": response_text[:200] if len(response_text) > 200 else response_text
        }

        # Store for broadcasting to UI
        if not hasattr(self, 'nemotron_calls'):
            self.nemotron_calls = []
        self.nemotron_calls.append(call_details)

        _LOGGER.debug(f"Nemotron API call: {latency_ms:.0f}ms, response: {len(response_text)} chars")

        return response_text
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from text that might contain markdown or other formatting"""
        import re

        # Remove <think> blocks first
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

        # Look for JSON in markdown code blocks
        json_block_match = re.search(r'```json\s*(\{.*\}|\[.*\])\s*```', text, re.DOTALL)
        if json_block_match:
            return json_block_match.group(1)

        # Look for any code block
        code_block_match = re.search(r'```\s*(\{.*\}|\[.*\])\s*```', text, re.DOTALL)
        if code_block_match:
            return code_block_match.group(1)

        # Look for JSON array or object - find the first complete JSON structure
        # First try to find arrays with balanced brackets
        array_start = text.find('[')
        if array_start != -1:
            bracket_count = 0
            in_string = False
            escape = False
            for i in range(array_start, len(text)):
                char = text[i]

                if escape:
                    escape = False
                    continue

                if char == '\\':
                    escape = True
                    continue

                if char == '"':
                    in_string = not in_string
                    continue

                if not in_string:
                    if char == '[':
                        bracket_count += 1
                    elif char == ']':
                        bracket_count -= 1
                        if bracket_count == 0:
                            return text[array_start:i+1]

        # If no array found, try object with balanced braces
        obj_start = text.find('{')
        if obj_start != -1:
            brace_count = 0
            in_string = False
            escape = False
            for i in range(obj_start, len(text)):
                char = text[i]

                if escape:
                    escape = False
                    continue

                if char == '\\':
                    escape = True
                    continue

                if char == '"':
                    in_string = not in_string
                    continue

                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            return text[obj_start:i+1]

        return text
    
    async def analyze_transcript(self, state: OrchestratorState, config: RunnableConfig):
        """Analyze the transcript to understand meeting context"""
        import time
        _LOGGER.info("Analyzing transcript for meeting context...")

        # Initialize logs
        logs = [
            {
                "type": "processing",
                "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                "message": "Starting transcript analysis..."
            },
            {
                "type": "input",
                "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                "message": f"Transcript length: {len(state.audio_transcript)} characters"
            }
        ]

        emit_workflow_event("stage_start", "Transcript Analyzer", {"description": "Analyzing meeting transcript..."}, logs)

        system_prompt = """You are an expert meeting analyst. Extract key information from meeting transcripts.

AUDIO TRANSCRIPTION CONTEXT:
- Transcripts may contain filler words: "um", "uh", "like", "you know" - ignore these
- Conversations may have false starts and corrections - interpret the final intent
- Overlapping speech and informal language should be interpreted charitably
- "Let me know about", "let's discuss" can indicate scheduling intent
- "Hey [name]" at the start often indicates mentioning someone as a potential attendee

IMPORTANT: Extract actual DATES from mentions like "november seventh", "next week monday" etc. even if informal.

Respond ONLY with valid JSON in exactly this format (no other text):
{
    "meeting_title": "string",
    "is_past_meeting": false,
    "mentioned_dates": ["2025-10-30"],
    "participants": ["John", "Sarah"],
    "key_topics": ["Q4 roadmap", "budget"],
    "action_items": ["John: prepare specs", "Sarah: budget analysis"],
    "summary": "Brief summary of the meeting (normalize grammar)"
}"""

        user_prompt = f"Analyze this meeting transcript and return ONLY JSON (remove filler words, extract dates and names clearly):\n\n{state.audio_transcript}"

        # Track API call timing
        start_time = time.time()
        response = self._call_nemotron(system_prompt, user_prompt, json_mode=True)
        api_duration_ms = int((time.time() - start_time) * 1000)

        # Extract thinking content if present
        thinking_content, clean_response = extract_thinking_content(response)
        if thinking_content:
            logs.append({
                "type": "thinking",
                "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                "message": thinking_content[:500]  # First 500 chars for display
            })

        # Add API call log
        logs.append({
            "type": "api_call",
            "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
            "message": f"Nemotron API call completed",
            "metadata": {
                "model": "nvidia/llama-3.3-nemotron-super-49b-v1.5",
                "latency_ms": api_duration_ms
            }
        })

        _LOGGER.debug(f"Raw response from Nemotron:\n{response}\n")

        try:
            # Extract JSON from response
            json_str = self._extract_json(clean_response)
            _LOGGER.info(f"Extracted JSON: {json_str[:200]}...")
            analysis = json.loads(json_str)

            # Handle case where LLM returns a list instead of a dictionary
            if isinstance(analysis, list):
                analysis = {
                    "meeting_title": "Meeting Discussion",
                    "is_past_meeting": False,
                    "mentioned_dates": [],
                    "participants": [],
                    "key_topics": [],
                    "action_items": analysis if analysis else [],
                    "summary": "Analysis result"
                }

            # Add output logs
            logs.append({
                "type": "output",
                "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                "message": f"Analysis complete: {len(analysis.get('key_topics', []))} topics, {len(analysis.get('action_items', []))} action items"
            })

            # Update state directly
            state.messages.append({
                "role": "assistant",
                "content": f"Meeting Analysis: {json.dumps(analysis, indent=2)}"
            })
            # Don't return analysis, just update messages
            emit_workflow_event("stage_complete", "Transcript Analyzer", {"status": "success"}, logs)
            return state
        except (json.JSONDecodeError, Exception) as e:
            _LOGGER.error(f"Failed to parse analysis JSON: {e}")
            _LOGGER.error(f"Raw response: {response[:500]}")
            
            # Create a default analysis and store in messages
            default_analysis = {
                "meeting_title": "Meeting Discussion",
                "is_past_meeting": False,
                "mentioned_dates": [],
                "participants": [],
                "key_topics": [],
                "action_items": [],
                "summary": state.audio_transcript[:200]
            }
            state.messages.append({
                "role": "assistant",
                "content": f"Meeting Analysis: {json.dumps(default_analysis, indent=2)}"
            })
            emit_workflow_event("stage_complete", "Transcript Analyzer", {"status": "success"})
            return state
    
    async def fetch_calendar_context(self, state: OrchestratorState, config: RunnableConfig):
        """Fetch relevant calendar events"""
        _LOGGER.info("Fetching calendar events...")

        logs = [
            {
                "type": "processing",
                "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                "message": "Starting calendar context fetch..."
            },
            {
                "type": "input",
                "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                "message": "Fetching events from past 30 days and next 30 days"
            }
        ]

        emit_workflow_event("stage_start", "Calendar Context Fetch", {"description": "Fetching calendar events..."}, logs)

        # Get events from past 30 days and next 30 days
        events = self.calendar_tool.fetch_events(days_ahead=30, days_back=30, max_results=50)
        state.calendar_events = events

        _LOGGER.info(f"Found {len(events)} calendar events")

        # Add output logs
        logs.append({
            "type": "output",
            "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
            "message": f"Calendar fetch complete: found {len(events)} events"
        })

        emit_workflow_event("stage_complete", "Calendar Context Fetch", {"status": "success"}, logs)
        return state
    
    async def find_related_meetings(self, state: OrchestratorState, config: RunnableConfig):
        """Use Nemotron to find related past meetings"""
        import time
        _LOGGER.info("Finding related past meetings...")

        logs = [
            {
                "type": "processing",
                "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                "message": "Starting related meetings search..."
            },
            {
                "type": "input",
                "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                "message": f"Analyzing {len(state.calendar_events)} calendar events"
            }
        ]

        emit_workflow_event("stage_start", "Related Meetings Finder", {"description": "Finding related past meetings..."}, logs)

        # Get the analysis from messages
        analysis_msg = state.messages[-1] if state.messages else {}
        if isinstance(analysis_msg, dict):
            analysis = analysis_msg.get('content', '{}')
        else:
            analysis = getattr(analysis_msg, 'content', '{}')

        # Create a summary of calendar events for context
        events_summary = []
        for event in state.calendar_events[:20]:  # Limit to 20 events
            events_summary.append({
                "id": event.id,
                "title": event.summary,
                "start": event.start,
                "description": (event.description or "")[:100]  # Truncate descriptions
            })

        system_prompt = """You are an expert at finding related calendar events.

Return ONLY a JSON array of related event IDs (no other text):
[
    {
        "event_id": "calendar_event_id",
        "relevance_score": 8,
        "reasoning": "why related"
    }
]

If no events are related, return an empty array: []"""

        user_prompt = f"""Meeting Analysis:
{analysis[:500]}

Calendar Events:
{json.dumps(events_summary, indent=2)[:1000]}

Which calendar events are related? Return ONLY JSON."""

        # Track API call timing
        start_time = time.time()
        response = self._call_nemotron(system_prompt, user_prompt, json_mode=True)
        api_duration_ms = int((time.time() - start_time) * 1000)

        logs.append({
            "type": "api_call",
            "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
            "message": "Nemotron API call completed",
            "metadata": {
                "model": "nvidia/llama-3.3-nemotron-super-49b-v1.5",
                "latency_ms": api_duration_ms
            }
        })

        _LOGGER.debug(f"Raw related meetings response:\n{response}\n")

        try:
            json_str = self._extract_json(response)
            _LOGGER.info(f"Related meetings JSON: {json_str[:200]}...")
            related = json.loads(json_str)

            # Ensure it's a list
            if not isinstance(related, list):
                related = []

            # Add output logs
            logs.append({
                "type": "output",
                "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                "message": f"Found {len(related)} related meetings"
            })

            # Update state directly
            state.related_past_meetings = related
            _LOGGER.info(f"Found {len(related)} related meetings")
            emit_workflow_event("stage_complete", "Related Meetings Finder", {"status": "success"}, logs)
            return state
        except (json.JSONDecodeError, Exception) as e:
            _LOGGER.error(f"Failed to parse related meetings: {e}")
            _LOGGER.error(f"Raw response: {response[:500]}")
            state.related_past_meetings = []
            emit_workflow_event("stage_complete", "Related Meetings Finder", {"status": "success"})
            return state
    
    async def plan_actions(self, state: OrchestratorState, config: RunnableConfig):
        """Decide what actions to take based on the analysis"""
        import time
        _LOGGER.info("Planning actions...")

        # Initialize logs
        logs = [
            {
                "type": "processing",
                "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                "message": "Starting action planning based on meeting analysis..."
            },
            {
                "type": "input",
                "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                "message": "Analyzing transcript and calendar context for action planning"
            }
        ]

        emit_workflow_event("stage_start", "Action Planner", {"description": "Planning actions based on meeting context..."}, logs)

        # Calculate dates for the prompt
        today = datetime.now(TIMEZONE).date()
        tomorrow = today + timedelta(days=1)
        today_str = today.isoformat()
        tomorrow_str = tomorrow.isoformat()

        system_prompt = """You are a meeting action planner. Based on transcript and calendar, decide actions.

⚠️ CRITICAL INSTRUCTION: GENERATE MULTIPLE ACTIONS FOR MULTIPLE REQUESTS
- If the transcript or extracted action_items list contains MULTIPLE distinct meetings, events, or tasks:
  - Create a SEPARATE action for EACH distinct item
  - Do NOT consolidate multiple scheduling requests into a single action
  - If 3 meetings are mentioned, return an array of 3 CREATE_EVENT actions
  - The length of your output array should match the number of distinct action items

Actions available:
- ADD_NOTES: Add notes to existing event
- CREATE_EVENT: Create new calendar event for FUTURE meetings mentioned in transcript
- FIND_SLOT: Find available time slots (9-5) for reference
- UPDATE_EVENT: Update existing event details

RULES:
1. If transcript mentions scheduling/planning a FUTURE meeting → use CREATE_EVENT
2. For past meetings with discussion points → use ADD_NOTES on related events
3. Use FIND_SLOT only if you need to find available times (system will auto-use first slot for CREATE_EVENT if needed)
4. Only create events for FUTURE meetings, never for past discussions
5. MULTI-ACTION RULE: Always generate one action per distinct meeting/item mentioned, never combine multiple meetings into one action

CONVERSATIONAL SCHEDULING PATTERNS:
These common conversational patterns indicate meeting scheduling:
- "Hey [name] next week on [date]" → SCHEDULING INTENT: Create meeting with [name] on [date]
- "let's [do/meet] [time description]" → SCHEDULING INTENT: Create meeting at specified time
- "let's do [time]" → SCHEDULING INTENT: Confirm time and create meeting
- "[name] next [day/week/date]" → SCHEDULING INTENT: Create meeting with [name] at that time
- "schedule [item]" → SCHEDULING INTENT: Create meeting for that item
- "discuss [topic] [time reference]" → If future time, CREATE_EVENT, else ADD_NOTES

DURATION DETECTION:
Extract meeting duration from transcript using these patterns:
- "30-minute meeting" / "30 minute meeting" → 30
- "1-hour meeting" / "one hour" → 60
- "2-hour session" / "two hours" → 120
- "90 minutes" / "ninety minutes" → 90
- "half hour" / "half an hour" → 30
- "quick 15-minute sync" → 15
- "45-min standup" → 45
- "all-day session" → 480 (8 hours)
- If no duration mentioned → default to 60 minutes

DATE PARSING (Today is {today_date}):
Convert natural language dates to YYYY-MM-DD format:
- "tomorrow" → {tomorrow_date}
- "next Monday/Tuesday/etc" → find next occurrence of that weekday
- "next week" → 7 days from today
- "in 3 days" → today + 3 days
- "this Friday" → upcoming Friday
- "November 5th" / "Nov 5" → 2025-11-05
- If no date mentioned → use next available business day

Always output event_date in YYYY-MM-DD format.

ATTENDEE EXTRACTION:
Extract attendee names from transcript and map to lowercase keys:
- "Rahual" / "Rahual Rai" → ["rahual"]
- "Kritika" / "Kritika Pant" → ["kritika"]
- "Biraj" / "Biraj Dahal" → ["biraj"]
- "Rahual and Kritika" → ["rahual", "kritika"]
- "with the team" → ["rahual", "kritika", "biraj"]
- If no attendees mentioned → null or empty array

System will auto-convert names to email addresses.

Return ONLY JSON array (no other text):

Example 1 - Add notes to past meeting:
[
    {{
        "action_type": "ADD_NOTES",
        "calendar_event_id": "event_id_here",
        "notes": "Follow-up: John to prepare specs, Sarah handles budget",
        "reasoning": "Document action items from follow-up discussion"
    }}
]

Example 2 - Create future meeting with duration and attendees:
[
    {{
        "action_type": "CREATE_EVENT",
        "event_title": "Project Phoenix Planning Session",
        "event_date": "2025-11-05",
        "duration_minutes": 120,
        "attendees": ["rahual", "kritika"],
        "notes": "Q4 roadmap planning",
        "reasoning": "Transcript requests scheduling a 2-hour planning meeting next week with Rahual and Kritika"
    }}
]

Example 3 - Informal scheduling pattern (Hey [name] next week on [date]):
[
    {{
        "action_type": "CREATE_EVENT",
        "event_title": "Financials Discussion",
        "event_date": "2025-11-07",
        "duration_minutes": 45,
        "attendees": ["prada"],
        "notes": "Discuss organization financials",
        "reasoning": "Transcript mentions 'hey prada next week on november seventh... to discuss our organization financials' - this is scheduling intent with implied attendee and date"
    }}
]

Example 4 - Short meeting with team:
[
    {{
        "action_type": "CREATE_EVENT",
        "event_title": "Quick Standup",
        "event_date": "2025-10-30",
        "duration_minutes": 30,
        "attendees": ["rahual", "kritika", "biraj"],
        "notes": "Daily sync",
        "reasoning": "Transcript mentions '30-minute standup tomorrow with the team'"
    }}
]

Example 5 - Both actions:
[
    {{
        "action_type": "ADD_NOTES",
        "calendar_event_id": "abc123",
        "notes": "Action items assigned",
        "reasoning": "Document current meeting outcomes"
    }},
    {{
        "action_type": "CREATE_EVENT",
        "event_title": "Follow-up Meeting",
        "event_date": "2025-11-01",
        "duration_minutes": 60,
        "notes": "Review progress on action items",
        "reasoning": "Schedule follow-up meeting as discussed (no duration specified, using default 60 min)"
    }}
]

If no actions needed, return empty array: []""".format(
            today_date=today_str,
            tomorrow_date=tomorrow_str
        )

        # Extract analyzed data from messages (added by analyze_transcript)
        analysis = None
        for msg in reversed(state.messages):
            # Handle both dict and AIMessage/BaseMessage objects
            content = msg.get("content") if isinstance(msg, dict) else msg.content
            if content and "Meeting Analysis:" in content:
                try:
                    analysis_str = content.split("Meeting Analysis: ")[1].strip()
                    # Parse the JSON, handling multiple levels of nesting
                    parsed = json.loads(analysis_str)

                    # Handle nested JSON strings (up to 3 levels deep)
                    for _ in range(3):
                        if isinstance(parsed, str):
                            parsed = json.loads(parsed)
                        else:
                            break

                    # Ensure analysis is a dict, not a list
                    if isinstance(parsed, list) and parsed:
                        parsed = parsed[0]

                    if isinstance(parsed, dict):
                        analysis = parsed
                        break
                except (IndexError, json.JSONDecodeError, AttributeError, ValueError) as e:
                    _LOGGER.warning(f"Failed to parse analysis from message: {e}")
                    pass

        # Build context with analyzed data
        context = {
            "transcript": state.audio_transcript[:2000],  # Increased from 800 to 2000 for more context
            "action_items": analysis.get("action_items", []) if analysis else [],
            "mentioned_dates": analysis.get("mentioned_dates", []) if analysis else [],
            "participants": analysis.get("participants", []) if analysis else [],
            "key_topics": analysis.get("key_topics", []) if analysis else [],
            "related_meetings": [
                {"id": m.get("id"), "title": m.get("summary"), "date": m.get("start")}
                for m in state.related_past_meetings[:3]
            ],
            "calendar_events": [
                {"id": e.id, "title": e.summary, "start": e.start}
                for e in state.calendar_events[:5]
            ]
        }

        # Log the context being sent to the LLM
        _LOGGER.info(f"PLAN_ACTIONS CONTEXT:")
        _LOGGER.info(f"  Action items count: {len(context.get('action_items', []))}")
        _LOGGER.info(f"  Action items: {context.get('action_items', [])}")
        _LOGGER.info(f"  Participants: {context.get('participants', [])}")
        _LOGGER.info(f"  Mentioned dates: {context.get('mentioned_dates', [])}")
        _LOGGER.info(f"  Transcript length: {len(context['transcript'])} chars")

        user_prompt = f"""Context:
{json.dumps(context, indent=2)}

What actions should be taken? Return ONLY JSON."""

        # Track API call timing
        start_time = time.time()
        response = self._call_nemotron(system_prompt, user_prompt, json_mode=True)
        api_duration_ms = int((time.time() - start_time) * 1000)

        # Extract thinking content if present
        thinking_content, clean_response = extract_thinking_content(response)
        if thinking_content:
            logs.append({
                "type": "thinking",
                "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                "message": thinking_content[:500]  # First 500 chars for display
            })

        # Add API call log
        logs.append({
            "type": "api_call",
            "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
            "message": f"Nemotron action planning API call completed",
            "metadata": {
                "model": "nvidia/llama-3.3-nemotron-super-49b-v1.5",
                "latency_ms": api_duration_ms
            }
        })

        _LOGGER.debug(f"Raw actions response from Nemotron:\n{response}\n")

        try:
            json_str = self._extract_json(clean_response)
            _LOGGER.info(f"Actions JSON: {json_str[:200]}")
            actions_data = json.loads(json_str)

            # Ensure it's a list - if single object, wrap in list
            if not isinstance(actions_data, list):
                if isinstance(actions_data, dict):
                    actions_data = [actions_data]
                    _LOGGER.info("Wrapped single action object in array")
                else:
                    actions_data = []

            # Normalize action types from uppercase to expected lowercase format
            action_type_mapping = {
                "ADD_NOTES": "add_notes",
                "CREATE_EVENT": "create_event",
                "FIND_SLOT": "find_available_slot",
                "UPDATE_EVENT": "update_event"
            }

            for action in actions_data:
                if "action_type" in action:
                    original_type = action["action_type"]
                    if original_type in action_type_mapping:
                        action["action_type"] = action_type_mapping[original_type]
                        _LOGGER.info(f"Normalized action type: {original_type} -> {action['action_type']}")

            actions = [MeetingAction(**action) for action in actions_data]
            state.planned_actions = actions

            # Log detailed action information
            _LOGGER.info(f"✓ Planned {len(actions)} actions:")
            action_summary = []
            for i, action in enumerate(actions, 1):
                _LOGGER.info(f"  Action {i}: {action.action_type}")
                action_detail = f"Action {i}: {action.action_type}"
                if action.action_type == "create_event":
                    _LOGGER.info(f"    Title: {action.event_title}")
                    _LOGGER.info(f"    Date: {action.event_date}")
                    _LOGGER.info(f"    Duration: {action.duration_minutes}m")
                    _LOGGER.info(f"    Attendees: {action.attendees}")
                    action_detail += f" - {action.event_title} on {action.event_date}"
                elif action.action_type == "add_notes":
                    _LOGGER.info(f"    Event ID: {action.calendar_event_id}")
                    _LOGGER.info(f"    Notes: {action.notes[:100]}...")
                    action_detail += f" - {action.calendar_event_id}"
                action_summary.append(action_detail)

            # Add output log
            logs.append({
                "type": "output",
                "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                "message": f"Successfully planned {len(actions)} actions for execution"
            })

            emit_workflow_event("stage_complete", "Action Planner", {"status": "success"}, logs)
            return state
        except (json.JSONDecodeError, Exception) as e:
            _LOGGER.error(f"Failed to parse actions: {e}")
            _LOGGER.error(f"Raw response: {response[:500]}")

            # Add error log
            logs.append({
                "type": "error",
                "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                "message": f"Failed to parse planned actions: {str(e)}"
            })

            state.planned_actions = []
            emit_workflow_event("stage_complete", "Action Planner", {"status": "success"}, logs)
            return state
    
    def _create_execution_result(self, status: str, action_type: str, message: str,
                                event_id: str = None, technical_details: str = None) -> Dict[str, Any]:
        """Create a structured execution result dictionary with timestamp"""
        return {
            "timestamp": datetime.now(TIMEZONE).isoformat(),
            "status": status,  # "success", "error", "warning"
            "action_type": action_type,
            "message": message,
            "event_id": event_id,
            "technical_details": technical_details
        }

    async def execute_actions(self, state: OrchestratorState, config: RunnableConfig):
        """Execute the planned actions in two phases: FIND_SLOT first, then others"""
        import time
        _LOGGER.info("Executing planned actions...")

        # Initialize logs
        logs = [
            {
                "type": "processing",
                "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                "message": "Starting action execution in two phases..."
            },
            {
                "type": "input",
                "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                "message": f"Total actions to execute: {len(state.planned_actions)}"
            }
        ]

        emit_workflow_event("stage_start", "Action Executor", {"description": "Executing planned actions..."}, logs)

        # Skip execution if auto_execute is False (manual approval required)
        if not state.auto_execute:
            _LOGGER.info("Auto-execute disabled - skipping action execution (awaiting manual approval)")
            logs.append({
                "type": "output",
                "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                "message": "Skipped execution - awaiting user approval"
            })
            state.execution_results = [
                self._create_execution_result(
                    status="warning",
                    action_type="pending_approval",
                    message="Actions planned but not executed - awaiting user approval",
                    technical_details="Manual approval required before execution"
                )
            ]
            emit_workflow_event("stage_complete", "Action Executor", {"status": "success"}, logs)
            return state

        results = []
        available_slots = []

        # Phase 1: Execute FIND_SLOT and ADD_NOTES actions first
        for action in state.planned_actions:
            if action.action_type not in [ActionType.FIND_SLOT, ActionType.ADD_NOTES, ActionType.UPDATE_EVENT]:
                continue

            _LOGGER.info(f"Executing action: {action.action_type}")

            try:
                if action.action_type == ActionType.FIND_SLOT:
                    # Find available time slot
                    slots = self.calendar_tool.find_available_slots(
                        duration_minutes=action.duration_minutes,
                        days_ahead=14,
                        max_slots=3
                    )

                    if slots:
                        available_slots = slots  # Store for CREATE_EVENT to use
                        slot_details = ", ".join([f"{slot.start} ({slot.duration_minutes} min)" for slot in slots])
                        results.append(self._create_execution_result(
                            status="success",
                            action_type="find_available_slot",
                            message=f"Found {len(slots)} available slots",
                            technical_details=slot_details
                        ))
                    else:
                        results.append(self._create_execution_result(
                            status="warning",
                            action_type="find_available_slot",
                            message="No available slots found in the next 14 days",
                            technical_details="Check calendar availability or extend search period"
                        ))

                elif action.action_type == ActionType.ADD_NOTES:
                    result = self.calendar_tool.add_notes_to_event(
                        action.calendar_event_id, action.notes
                    )
                    results.append(self._create_execution_result(
                        status="success",
                        action_type="add_notes",
                        message=f"Added notes to event {action.calendar_event_id}",
                        event_id=action.calendar_event_id,
                        technical_details=result
                    ))

                elif action.action_type == ActionType.UPDATE_EVENT:
                    event_id = action.calendar_event_id
                    updates = {"description": action.notes or "Updated notes"}
                    self.calendar_tool.update_event(event_id, updates)
                    results.append(self._create_execution_result(
                        status="success",
                        action_type="update_event",
                        message=f"Updated event with new notes",
                        event_id=event_id,
                        technical_details=f"Event ID: {event_id}"
                    ))

            except Exception as e:
                error_msg = f"Error executing {action.action_type}: {str(e)}"
                _LOGGER.error(error_msg)
                results.append(self._create_execution_result(
                    status="error",
                    action_type=str(action.action_type),
                    message=f"Failed to {action.action_type}",
                    technical_details=str(e)
                ))

        # Phase 2: Execute CREATE_EVENT actions (can now use available_slots)
        for action in state.planned_actions:
            if action.action_type != ActionType.CREATE_EVENT:
                continue

            _LOGGER.info(f"Executing action: {action.action_type}")

            try:
                # Determine start and end times
                if action.event_date:
                    # Date provided, find first available slot on that date
                    target_date = action.event_date  # Format: "2025-11-05"

                    # Try to find available slot on specific date
                    slots_on_date = self.calendar_tool.find_available_slots(
                        duration_minutes=action.duration_minutes,
                        days_ahead=14,
                        max_slots=10
                    )

                    # Filter for the target date
                    matching_slots = [s for s in slots_on_date if s.start.startswith(target_date)]

                    if matching_slots:
                        slot = matching_slots[0]  # Use first available on that day
                        start_time, end_time = slot.start, slot.end
                        _LOGGER.info(f"Using first available slot on {target_date}: {start_time}")
                    else:
                        # No slots on specific date, use default afternoon time
                        # Create timezone-aware datetime for 2 PM EST/EDT
                        target_dt = datetime.strptime(target_date, "%Y-%m-%d")
                        start_dt = TIMEZONE.localize(target_dt.replace(hour=14, minute=0, second=0))
                        end_dt = start_dt + timedelta(minutes=action.duration_minutes)
                        start_time = start_dt.isoformat()
                        end_time = end_dt.isoformat()
                        _LOGGER.info(f"No free slots on {target_date}, using default 2 PM EST/EDT: {start_time}")
                else:
                    # No date provided, use first available slot from any available slots
                    if available_slots:
                        slot = available_slots[0]
                        start_time, end_time = slot.start, slot.end
                        _LOGGER.info(f"Using first available slot: {start_time}")
                    else:
                        # Find a slot now
                        slots = self.calendar_tool.find_available_slots(
                            duration_minutes=action.duration_minutes,
                            days_ahead=14,
                            max_slots=1
                        )
                        if slots:
                            start_time, end_time = slots[0].start, slots[0].end
                            _LOGGER.info(f"Found and using slot: {start_time}")
                        else:
                            results.append(self._create_execution_result(
                                status="error",
                                action_type="create_event",
                                message=f"Cannot create event: No available slots found",
                                technical_details=f"Title: {action.event_title}"
                            ))
                            continue

                # Map attendee names to email addresses using fuzzy matching
                attendee_emails = None
                if action.attendees:
                    # Use the new fuzzy matching function
                    attendee_emails = get_attendee_emails(action.attendees)
                    _LOGGER.info(f"Mapped {len(action.attendees)} attendees to {len(attendee_emails)} emails")

                event_id = self.calendar_tool.create_event(
                    title=action.event_title or "New Meeting",
                    start_time=start_time,
                    end_time=end_time,
                    description=action.notes or "",
                    attendees=attendee_emails
                )

                attendee_info = f" with {len(attendee_emails)} attendees" if attendee_emails else ""
                results.append(self._create_execution_result(
                    status="success",
                    action_type="create_event",
                    message=f"Created event '{action.event_title}'{attendee_info}",
                    event_id=event_id,
                    technical_details=f"Scheduled for {start_time}"
                ))
                _LOGGER.info(f"Created new event '{action.event_title}' with ID: {event_id}")

            except Exception as e:
                error_msg = f"Error executing {action.action_type}: {str(e)}"
                _LOGGER.error(error_msg)
                results.append(self._create_execution_result(
                    status="error",
                    action_type="create_event",
                    message=f"Failed to create event '{action.event_title}'",
                    technical_details=str(e)
                ))

        state.execution_results = results

        # Add output log with execution summary
        successful_count = sum(1 for r in results if r.get("status") == "success")
        error_count = sum(1 for r in results if r.get("status") == "error")
        logs.append({
            "type": "output",
            "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
            "message": f"Execution complete: {successful_count} successful, {error_count} failed"
        })

        emit_workflow_event("stage_complete", "Action Executor", {"status": "success"}, logs)
        return state
    
    async def generate_summary(self, state: OrchestratorState, config: RunnableConfig):
        """Generate a final summary of what was done"""
        import time
        _LOGGER.info("Generating final summary...")

        # Initialize logs
        logs = [
            {
                "type": "processing",
                "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                "message": "Starting final summary generation..."
            },
            {
                "type": "input",
                "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                "message": f"Summarizing {len(state.planned_actions)} planned actions and meeting context"
            }
        ]

        emit_workflow_event("stage_start", "Summary Generator", {"description": "Generating meeting summary and sending notifications..."}, logs)

        system_prompt = """You are a meeting assistant. Create a clear, structured summary organized by sections using markdown format.

Format your response with these EXACT markdown section headers:

## Meeting Overview
[2-3 sentences about the meeting]

## Key Topics Discussed
- Bullet point 1
- Bullet point 2
- Bullet point 3

## Scheduled Events
- **Event Title**: Date, attendees, duration
- **Another Event**: Date, attendees, duration

## Action Items
- [ ] Specific action item (assigned to: person name)
- [ ] Another action item (assigned to: person name)

Requirements:
- Be specific and actionable
- Keep each section concise but detailed
- No introductions, explanations, or reasoning - just the facts
- Use markdown formatting: **bold** for emphasis, - for bullets, [ ] for tasks
- Start directly with the ## Meeting Overview header"""

        context = {
            "transcript_preview": state.audio_transcript[:500],
            "actions_taken": [
                {
                    "action": action.action_type,
                    "title": action.event_title,
                    "reasoning": action.reasoning
                }
                for action in state.planned_actions
            ]
        }

        user_prompt = f"""Based on this meeting context, create a structured summary:

{json.dumps(context, indent=2)}"""

        # Track API call timing
        start_time = time.time()
        response = self._call_nemotron(system_prompt, user_prompt)
        api_duration_ms = int((time.time() - start_time) * 1000)

        # Extract thinking content if present
        thinking_content, summary = extract_thinking_content(response)
        if thinking_content:
            logs.append({
                "type": "thinking",
                "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                "message": thinking_content[:500]  # First 500 chars for display
            })

        # Add API call log
        logs.append({
            "type": "api_call",
            "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
            "message": f"Nemotron summary generation API call completed",
            "metadata": {
                "model": "nvidia/llama-3.3-nemotron-super-49b-v1.5",
                "latency_ms": api_duration_ms
            }
        })

        _LOGGER.info(f"Generated summary (cleaned): {summary[:200]}...")

        # Generate next steps using AI
        next_steps = await self._generate_next_steps(state, summary)
        state.next_steps = next_steps

        # Create HTML formatted version
        html_summary = self._create_html_summary(summary, state)

        # Try to send email, but don't fail if permissions are insufficient
        try:
            self.email_tool.send_email(
                to_addresses=["Dores.Lashley@SolarNyx.com"],
                subject="AI Meeting Summary: " + datetime.now(TIMEZONE).strftime("%Y-%m-%d %I:%M %p %Z"),
                body=summary,
                html_body=html_summary
            )
            _LOGGER.info("Summary email sent successfully.")
        except Exception as e:
            _LOGGER.warning(f"Failed to send email: {e}")
            _LOGGER.warning("Continuing workflow without sending email.")

        state.messages.append({
            "role": "assistant",
            "content": f"Summary:\n{summary}"
        })

        # Add output log
        logs.append({
            "type": "output",
            "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
            "message": f"Summary generated and email sent to {len(state.planned_actions)} recipients"
        })

        emit_workflow_event("stage_complete", "Summary Generator", {"status": "success"}, logs)
        return state

    async def _generate_next_steps(self, state: OrchestratorState, summary: str) -> List[str]:
        """Generate AI-suggested next steps based on meeting summary"""
        _LOGGER.info("Generating suggested next steps...")

        system_prompt = """You are a meeting facilitator. Based on the meeting summary and scheduled events,
suggest 3-4 proactive next steps the team should take. Focus on:
- Preparation tasks for scheduled meetings
- Follow-up items that need attention
- Stakeholder communications needed
- Resources or materials that should be prepared

Format as a numbered list with brief descriptions. Be specific and actionable."""

        user_prompt = f"""Meeting Summary:
{summary}

Scheduled Events: {len(state.planned_actions)} events

Generate 3-4 specific next steps the team should take:"""

        try:
            response = self._call_nemotron(system_prompt, user_prompt)
            # Parse response into bullet points
            lines = response.strip().split('\n')
            next_steps = [line.strip() for line in lines if line.strip() and not line.startswith('#')]
            return next_steps[:4]  # Return max 4 steps
        except Exception as e:
            _LOGGER.warning(f"Failed to generate next steps: {e}")
            return []

    def _create_html_summary(self, summary: str, state: OrchestratorState) -> str:
        """Create HTML formatted email summary"""
        import markdown2

        # Convert markdown to HTML
        summary_html = markdown2.markdown(summary, extras=['fenced-code-blocks', 'tables', 'task_lists'])

        # Build actions table
        actions_html = ""
        for i, action in enumerate(state.planned_actions, 1):
            action_badge = {
                "add_notes": "🗒️ Add Notes",
                "create_event": "📅 Create Event",
                "find_available_slot": "🔍 Find Slot",
                "update_event": "✏️ Update Event"
            }.get(action.action_type, action.action_type)

            actions_html += f"""
            <tr style="background-color: {'#f9f9f9' if i % 2 == 0 else 'white'};">
                <td style="padding: 12px; border: 1px solid #ddd;">{action_badge}</td>
                <td style="padding: 12px; border: 1px solid #ddd;">{action.event_title or 'N/A'}</td>
                <td style="padding: 12px; border: 1px solid #ddd;">{action.reasoning}</td>
            </tr>
            """

        # Build enhanced results list with status indicators and calendar links
        results_html = ""
        for result in state.execution_results:
            # Handle both old string format and new dict format for backward compatibility
            if isinstance(result, dict):
                status = result.get("status", "unknown")
                icon = "✅" if status == "success" else "❌" if status == "error" else "⚠️"
                timestamp = result.get("timestamp", "")
                message = result.get("message", "")
                event_id = result.get("event_id", "")
                tech_details = result.get("technical_details", "")

                calendar_link = ""
                if event_id:
                    link_url = generate_calendar_link(event_id)
                    calendar_link = f'<br/><a href="{link_url}" style="color: #667eea; text-decoration: none;">📅 Edit in Calendar</a>'

                tech_html = f'<div style="font-size: 11px; color: #999; margin-top: 8px;">ID: {tech_details or event_id}</div>' if tech_details or event_id else ""

                results_html += f'''<div style="background: {'#e8f5e9' if status == 'success' else '#ffebee'}; border-left: 4px solid {'#4CAF50' if status == 'success' else '#f44336'}; padding: 15px; margin-bottom: 12px; border-radius: 4px;">
                    <div style="display: flex; align-items: start; gap: 12px;">
                        <span style="font-size: 18px; line-height: 1.4;">{icon}</span>
                        <div style="flex: 1;">
                            <div style="font-weight: bold; margin-bottom: 4px;">{message}</div>
                            {calendar_link}
                            {tech_html}
                            <div style="font-size: 12px; color: #666; margin-top: 8px;">⏰ {timestamp}</div>
                        </div>
                    </div>
                </div>'''
            else:
                # Old string format - simple display
                results_html += f'<li style="margin-bottom: 8px;">{result}</li>'

        # Build next steps section
        next_steps_html = ""
        if state.next_steps:
            for i, step in enumerate(state.next_steps, 1):
                next_steps_html += f'<div style="background: #f0f7ff; border-left: 4px solid #2196F3; padding: 12px; margin-bottom: 10px; border-radius: 4px;"><strong>💡 {step}</strong></div>'
            next_steps_section = f'''
            <div style="margin-bottom: 25px;">
                <h2 style="color: #667eea;">💡 Suggested Next Steps</h2>
                <div style="margin-top: 15px;">
                    {next_steps_html}
                </div>
            </div>
            '''
        else:
            next_steps_section = ""

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                .summary-content h2 {{ color: #667eea; margin-top: 20px; margin-bottom: 10px; font-size: 18px; }}
                .summary-content h3 {{ color: #667eea; margin-top: 15px; margin-bottom: 8px; font-size: 16px; }}
                .summary-content ul {{ margin: 10px 0; padding-left: 20px; }}
                .summary-content li {{ margin-bottom: 8px; line-height: 1.6; }}
                .summary-content strong {{ font-weight: bold; color: #333; }}
                .summary-content em {{ font-style: italic; color: #555; }}
                .summary-content code {{ background-color: #f0f0f0; padding: 2px 6px; border-radius: 3px; font-family: monospace; }}
                .summary-content pre {{ background-color: #f5f5f5; padding: 12px; border-radius: 4px; overflow-x: auto; }}
                .summary-content pre code {{ background-color: transparent; padding: 0; }}
                .summary-content table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
                .summary-content th {{ background-color: #667eea; color: white; padding: 12px; text-align: left; border: 1px solid #667eea; }}
                .summary-content td {{ padding: 10px 12px; border: 1px solid #ddd; }}
                .summary-content input[type="checkbox"] {{ margin-right: 8px; }}
            </style>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px;">
                <h1 style="margin: 0; font-size: 28px;">🤖 AI Meeting Summary</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9;">{datetime.now(TIMEZONE).strftime("%B %d, %Y at %I:%M %p %Z")}</p>
            </div>

            <div style="background: #f5f5f5; padding: 20px; border-radius: 8px; margin-bottom: 25px;">
                <h2 style="margin-top: 0; color: #667eea; margin-bottom: 15px;">Meeting Summary</h2>
                <div class="summary-content" style="color: #444;">{summary_html}</div>
            </div>

            <div style="margin-bottom: 25px;">
                <h2 style="color: #667eea;">🎯 Actions Planned</h2>
                <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                    <thead>
                        <tr style="background-color: #667eea; color: white;">
                            <th style="padding: 12px; text-align: left; border: 1px solid #667eea;">Action</th>
                            <th style="padding: 12px; text-align: left; border: 1px solid #667eea;">Details</th>
                            <th style="padding: 12px; text-align: left; border: 1px solid #667eea;">Reasoning</th>
                        </tr>
                    </thead>
                    <tbody>
                        {actions_html}
                    </tbody>
                </table>
            </div>

            <div style="margin-bottom: 25px;">
                <h2 style="color: #667eea;">✅ Execution Results</h2>
                <div style="margin-top: 15px;">
                    {results_html}
                </div>
            </div>

            {next_steps_section}

            <div style="text-align: center; padding: 20px; color: #999; font-size: 12px; border-top: 1px solid #ddd;">
                <p>Generated by NVIDIA Nemotron AI Meeting Orchestrator</p>
                <p>Powered by LangGraph & Google Calendar API</p>
            </div>
        </body>
        </html>
        """

        return html

    async def research_agent(self, state: OrchestratorState, config: RunnableConfig):
        """Research agent: Extracts entities and gathers background context"""
        _LOGGER.info("Research Agent: Extracting entities and gathering context...")
        emit_workflow_event("stage_start", "Research & Entity Extraction", {"description": "Extracting entities and gathering context..."})

        system_prompt = """You are a research agent that extracts important entities from a meeting transcript
and provides context about them. Your job is to identify:
- Key projects, products, or initiatives mentioned
- Important people or teams involved
- Technologies, tools, or frameworks mentioned
- Competitors or external organizations referenced

For each entity, provide:
1. Entity name
2. Entity type (project/person/technology/organization)
3. Brief context (1-2 sentences about its relevance)

Format your response as JSON with structure:
{
  "entities": [
    {"name": "...", "type": "...", "context": "..."},
    ...
  ],
  "key_topics": ["topic1", "topic2", "..."],
  "summary": "Brief summary of key context"
}"""

        user_prompt = f"""Meeting transcript:
{state.audio_transcript[:1000]}...

Extract key entities and provide context for research:"""

        try:
            response = self._call_nemotron(system_prompt, user_prompt, json_mode=True)
            json_str = self._extract_json(response)
            research_data = json.loads(json_str)

            # Store research findings in state
            state.messages.append({
                "role": "assistant",
                "agent": "research_agent",
                "content": f"Research findings: {research_data.get('summary', 'Context gathered')}",
                "research_data": research_data
            })

            _LOGGER.info(f"Research Agent: Identified {len(research_data.get('entities', []))} entities")
            emit_workflow_event("stage_complete", "Research & Entity Extraction", {"status": "success"})
            return state

        except Exception as e:
            _LOGGER.warning(f"Research Agent error: {e}")
            state.messages.append({
                "role": "assistant",
                "agent": "research_agent",
                "content": f"Research agent completed with note: {str(e)}"
            })
            emit_workflow_event("stage_complete", "Research & Entity Extraction", {"status": "success"})
            return state

    async def decision_agent(self, state: OrchestratorState, config: RunnableConfig):
        """Decision agent: Analyzes options and provides intelligent recommendations"""
        import time
        _LOGGER.info("Decision Agent: Analyzing planned actions and providing recommendations...")

        # Initialize logs
        logs = [
            {
                "type": "processing",
                "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                "message": "Starting decision analysis of planned actions..."
            },
            {
                "type": "input",
                "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                "message": f"Analyzing {len(state.planned_actions)} planned actions for feasibility and priority"
            }
        ]

        emit_workflow_event("stage_start", "Decision Analyzer", {"description": "Analyzing options and providing recommendations..."}, logs)

        system_prompt = """You are a decision-making agent that analyzes proposed actions and provides
intelligent recommendations. You evaluate options based on:
- Priority and urgency
- Resource availability and constraints
- Stakeholder impact
- Timeline feasibility
- Risk factors

For the planned actions, provide:
1. Priority ranking (critical/high/medium/low)
2. Feasibility score (0-10)
3. Recommended approach
4. Potential risks and mitigation strategies

Format as JSON:
{
  "decisions": [
    {
      "action_index": 0,
      "priority": "high",
      "feasibility": 8,
      "recommendation": "...",
      "risks": ["risk1", "risk2"],
      "mitigation": "..."
    }
  ],
  "overall_assessment": "...",
  "critical_path_items": ["..."]
}"""

        user_prompt = f"""Planned actions to evaluate:
{json.dumps(state.planned_actions[:3], default=str, indent=2)}

Analyze these actions and provide recommendations:"""

        try:
            # Track API call timing
            start_time = time.time()
            response = self._call_nemotron(system_prompt, user_prompt, json_mode=True)
            api_duration_ms = int((time.time() - start_time) * 1000)

            # Extract thinking content if present
            thinking_content, clean_response = extract_thinking_content(response)
            if thinking_content:
                logs.append({
                    "type": "thinking",
                    "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                    "message": thinking_content[:500]  # First 500 chars for display
                })

            # Add API call log
            logs.append({
                "type": "api_call",
                "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                "message": f"Nemotron decision analysis API call completed",
                "metadata": {
                    "model": "nvidia/llama-3.3-nemotron-super-49b-v1.5",
                    "latency_ms": api_duration_ms
                }
            })

            json_str = self._extract_json(clean_response)
            decisions_data = json.loads(json_str)

            # Handle case where LLM returns a list instead of a dictionary
            if isinstance(decisions_data, list):
                decisions_data = {"decisions": decisions_data, "overall_assessment": "Analysis complete"}

            state.messages.append({
                "role": "assistant",
                "agent": "decision_agent",
                "content": f"Decision analysis: {decisions_data.get('overall_assessment', 'Analysis complete')}",
                "decisions_data": decisions_data
            })

            _LOGGER.info(f"Decision Agent: Analyzed {len(decisions_data.get('decisions', []))} actions")

            # Add output log
            logs.append({
                "type": "output",
                "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                "message": f"Decision analysis complete: {len(decisions_data.get('decisions', []))} actions evaluated"
            })

            emit_workflow_event("stage_complete", "Decision Analyzer", {"status": "success"}, logs)
            return state

        except Exception as e:
            _LOGGER.warning(f"Decision Agent error: {e}")

            # Add error log
            logs.append({
                "type": "error",
                "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                "message": f"Decision analysis error: {str(e)}"
            })

            state.messages.append({
                "role": "assistant",
                "agent": "decision_agent",
                "content": f"Decision agent completed with note: {str(e)}"
            })
            emit_workflow_event("stage_complete", "Decision Analyzer", {"status": "success"}, logs)
            return state

    async def risk_assessment_agent(self, state: OrchestratorState, config: RunnableConfig):
        """Risk assessment agent: Identifies and evaluates risks in planned actions"""
        import time
        _LOGGER.info("Risk Assessment Agent: Identifying potential risks...")

        # Initialize logs
        logs = [
            {
                "type": "processing",
                "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                "message": "Starting risk assessment of planned actions..."
            },
            {
                "type": "input",
                "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                "message": f"Assessing risks for {len(state.planned_actions)} planned actions and calendar conflicts"
            }
        ]

        emit_workflow_event("stage_start", "Risk Assessor", {"description": "Evaluating risks and potential issues..."}, logs)

        system_prompt = """You are a risk assessment agent specialized in identifying potential issues
in meeting action items and scheduled events. Evaluate risks in:
- Calendar conflicts and double-bookings
- Timeline compression and feasibility
- Resource conflicts and availability
- Dependency chain breaks
- External blocker risks

For each identified risk, provide:
1. Risk description
2. Severity (critical/high/medium/low)
3. Affected action(s)
4. Mitigation strategy
5. Owner recommendation

Format as JSON:
{
  "risks": [
    {
      "description": "...",
      "severity": "high",
      "affected_actions": [0, 1],
      "mitigation": "...",
      "owner": "..."
    }
  ],
  "overall_risk_level": "medium",
  "critical_blockers": ["..."],
  "recommendations": ["..."]
}"""

        action_summary = f"""
Actions: {len(state.planned_actions)}
Calendar events: {len(state.calendar_events)}
Transcript length: {len(state.audio_transcript)} chars

Planned actions summary:
{json.dumps([{"title": a.event_title, "date": a.event_date} for a in state.planned_actions[:3]], indent=2)}
"""

        user_prompt = f"""Meeting context and planned actions:
{action_summary}

Identify risks and provide assessment:"""

        try:
            # Track API call timing
            start_time = time.time()
            response = self._call_nemotron(system_prompt, user_prompt, json_mode=True)
            api_duration_ms = int((time.time() - start_time) * 1000)

            # Extract thinking content if present
            thinking_content, clean_response = extract_thinking_content(response)
            if thinking_content:
                logs.append({
                    "type": "thinking",
                    "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                    "message": thinking_content[:500]  # First 500 chars for display
                })

            # Add API call log
            logs.append({
                "type": "api_call",
                "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                "message": f"Nemotron risk assessment API call completed",
                "metadata": {
                    "model": "nvidia/llama-3.3-nemotron-super-49b-v1.5",
                    "latency_ms": api_duration_ms
                }
            })

            json_str = self._extract_json(clean_response)
            risk_data = json.loads(json_str)

            # Handle case where LLM returns a list instead of a dictionary
            if isinstance(risk_data, list):
                risk_data = {"risks": risk_data, "overall_risk_level": "medium"}

            state.messages.append({
                "role": "assistant",
                "agent": "risk_assessment_agent",
                "content": f"Risk assessment: {risk_data.get('overall_risk_level', 'unknown')} risk level identified",
                "risk_data": risk_data
            })

            _LOGGER.info(f"Risk Assessment Agent: Identified {len(risk_data.get('risks', []))} risks")

            # Add output log
            logs.append({
                "type": "output",
                "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                "message": f"Risk assessment complete: {len(risk_data.get('risks', []))} risks identified, {risk_data.get('overall_risk_level', 'unknown')} overall level"
            })

            emit_workflow_event("stage_complete", "Risk Assessor", {"status": "success"}, logs)
            return state

        except Exception as e:
            _LOGGER.warning(f"Risk Assessment Agent error: {e}")

            # Add error log
            logs.append({
                "type": "error",
                "timestamp": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                "message": f"Risk assessment error: {str(e)}"
            })

            state.messages.append({
                "role": "assistant",
                "agent": "risk_assessment_agent",
                "content": f"Risk assessment completed with note: {str(e)}"
            })
            emit_workflow_event("stage_complete", "Risk Assessor", {"status": "success"}, logs)
            return state


# Build the LangGraph workflow
def create_orchestrator_graph():
    """Create the orchestrator workflow graph"""
    
    orchestrator = MeetingOrchestrator()
    workflow = StateGraph(OrchestratorState)
    
    # Add nodes
    workflow.add_node("analyze_transcript", orchestrator.analyze_transcript)
    workflow.add_node("research_agent", orchestrator.research_agent)
    workflow.add_node("fetch_calendar_context", orchestrator.fetch_calendar_context)
    workflow.add_node("find_related_meetings", orchestrator.find_related_meetings)
    workflow.add_node("plan_actions", orchestrator.plan_actions)
    workflow.add_node("decision_agent", orchestrator.decision_agent)
    workflow.add_node("risk_assessment_agent", orchestrator.risk_assessment_agent)
    workflow.add_node("execute_actions", orchestrator.execute_actions)
    workflow.add_node("generate_summary", orchestrator.generate_summary)

    # Define the flow: Analyze → Research → Fetch Calendar → Find Related → Plan → Decide → Risk Assess → Execute → Summarize
    workflow.add_edge(START, "analyze_transcript")
    workflow.add_edge("analyze_transcript", "research_agent")
    workflow.add_edge("research_agent", "fetch_calendar_context")
    workflow.add_edge("fetch_calendar_context", "find_related_meetings")
    workflow.add_edge("find_related_meetings", "plan_actions")
    workflow.add_edge("plan_actions", "decision_agent")
    workflow.add_edge("decision_agent", "risk_assessment_agent")
    workflow.add_edge("risk_assessment_agent", "execute_actions")
    workflow.add_edge("execute_actions", "generate_summary")
    workflow.add_edge("generate_summary", END)
    
    return workflow.compile()


# Event callback system for streaming progress
_event_callback = None

def set_workflow_event_callback(callback):
    """Set a callback function for workflow events"""
    global _event_callback
    _event_callback = callback
    if callback:
        _LOGGER.info(f"✓ [set_workflow_event_callback] Callback set successfully: {callback}")
    else:
        _LOGGER.warning(f"⚠️ [set_workflow_event_callback] Callback set to None")

def emit_workflow_event(event_type: str, agent_name: str, data: dict = None, logs: list = None):
    """Emit a workflow event to all listeners with optional log entries"""
    global _event_callback
    event = {
        "type": event_type,
        "agent": agent_name,
        "timestamp": datetime.now(TIMEZONE).isoformat(),
    }
    if data:
        event.update(data)
    if logs:
        event["logs"] = logs

    if _event_callback:
        _LOGGER.info(f"🔌 [emit_workflow_event] Emitting {event_type} for {agent_name}" + (f" with {len(logs)} logs" if logs else ""))
        _event_callback(event)
    else:
        _LOGGER.warning(f"⚠️ [emit_workflow_event] No callback set! Event not emitted: {event_type} for {agent_name}")


# Helper function for Flask integration
async def run_orchestrator(transcript: str, auto_execute: bool = True, event_callback=None) -> dict:
    """
    Run the orchestrator workflow and return serializable results

    Args:
        transcript: Meeting transcript text
        auto_execute: If True, execute actions; if False, return planned actions only
        event_callback: Optional callback function for streaming events

    Returns:
        Dictionary with planned_actions, execution_results, and summary
    """
    import uuid

    # Generate unique workflow ID for tracing
    workflow_id = uuid.uuid4().hex[:8]

    # Log workflow start with prominent ID
    _LOGGER.info("")
    _LOGGER.info("🔷" * 40)
    _LOGGER.info(f"WORKFLOW INITIATED - ID: {workflow_id}")
    _LOGGER.info("🔷" * 40)
    _LOGGER.info(f"Auto-execute: {auto_execute} | Transcript length: {len(transcript)} chars")
    _LOGGER.info("")

    # Set up the event callback if provided
    if event_callback:
        set_workflow_event_callback(event_callback)

    # Create the graph
    graph = create_orchestrator_graph()

    # Initialize state with workflow ID
    initial_state = OrchestratorState(
        audio_transcript=transcript,
        workflow_id=workflow_id,
        auto_execute=auto_execute
    )

    # Run the orchestrator
    result = await graph.ainvoke(initial_state)

    # Extract summary from messages
    summary = ""
    if result.get('messages'):
        last_message = result['messages'][-1]
        if isinstance(last_message, dict):
            summary = last_message.get('content', '')
        else:
            summary = getattr(last_message, 'content', '')
        # Extract just the summary part (after "Summary:\n")
        if "Summary:\n" in summary:
            summary = summary.split("Summary:\n", 1)[1].strip()

    # Serialize results
    serialized_results = {
        "planned_actions": [
            {
                "action_type": action.action_type.value,
                "calendar_event_id": action.calendar_event_id,
                "event_title": action.event_title,
                "event_date": action.event_date,
                "duration_minutes": action.duration_minutes,
                "attendees": action.attendees,
                "notes": action.notes,
                "reasoning": action.reasoning
            }
            for action in result['planned_actions']
        ],
        "execution_results": result['execution_results'],
        "summary": summary,
        "calendar_events_count": len(result['calendar_events']),
        "related_meetings_count": len(result['related_past_meetings'])
    }

    _LOGGER.info(f"Orchestrator completed: {len(result['planned_actions'])} actions planned")
    return serialized_results


# Example usage
async def main():
    """Example of how to use the orchestrator"""
    
    # Sample transcript (you'd get this from your audio transcription)
    sample_transcript = """
    This is a follow-up to our Project Phoenix meeting. We discussed the Q4 roadmap 
    and decided to schedule a planning session next week. Rahual will prepare the technical 
    specs, and Kritika will handle the budget analysis. We need to find time for a 2-hour 
    planning meeting, preferably on Tuesday or Wednesday afternoon.
    """
    
    # Create the graph
    graph = create_orchestrator_graph()
    
    # Initialize state
    initial_state = OrchestratorState(
        audio_transcript=sample_transcript
    )
    
    # Run the orchestrator
    _LOGGER.info("Starting orchestrator workflow...")
    result = await graph.ainvoke(initial_state)

    # Log results (using logger instead of print for consistency)
    from logging_config import log_section_header, log_section_footer

    log_section_header(_LOGGER, "ORCHESTRATOR RESULTS")

    _LOGGER.info(f"Found {len(result['calendar_events'])} calendar events")
    _LOGGER.info(f"Identified {len(result['related_past_meetings'])} related meetings")
    _LOGGER.info(f"Planned {len(result['planned_actions'])} actions")

    _LOGGER.info("--- Planned Actions ---")
    for action in result['planned_actions']:
        _LOGGER.info(f"  {action.action_type}: {action.reasoning}")
        if action.event_title:
            _LOGGER.info(f"    Event: {action.event_title}")

    _LOGGER.info("--- Execution Results ---")
    for result_msg in result['execution_results']:
        _LOGGER.info(f"  {result_msg}")

    _LOGGER.info("--- Final Summary ---")
    if result.get('messages'):
        last_message = result['messages'][-1]
        # Handle both dict and AIMessage object
        summary_text = last_message.get('content', 'No summary available') if isinstance(last_message, dict) else getattr(last_message, 'content', 'No summary available')
        _LOGGER.info(summary_text)

    log_section_footer(_LOGGER)


if __name__ == "__main__":
    asyncio.run(main())