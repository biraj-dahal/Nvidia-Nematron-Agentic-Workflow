# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered meeting assistant that uses NVIDIA Nemotron LLM and LangGraph to orchestrate multi-agent workflows. The system analyzes meeting transcripts, manages calendar events, finds related meetings, and automatically sends HTML-formatted email summaries with timezone support.

**Frontend**: React 19 + TypeScript + Material-UI (MUI) on port 3000
**Backend**: Flask + LangGraph + NVIDIA Nemotron on port 5000
**Architecture**: Separate frontend/backend with Server-Sent Events (SSE) streaming

## Development Commands

### Backend
```bash
# Start Flask server (handles /transcribe endpoint + SSE streaming)
python server.py

# Run main orchestrator workflow with test transcript
python orchestrator_agent.py

# Test Google Calendar integration
python calender_tool.py
```

### Frontend
```bash
cd frontend

# Start development server (port 3000, proxies to localhost:5000)
npm start

# Run Jest tests in watch mode
npm test

# Build for production
npm run build
```

## Environment Configuration

### Setup Required Files

1. **`.env` file** (or export variables):
   ```bash
   export API_KEY="your_nvidia_api_key"
   export NEMOTRON_MODEL="nvidia/llama-3.3-nemotron-super-49b-v1.5"
   ```
   See `.env.example` for all available configuration options.

2. **Google OAuth credentials**:
   - Place OAuth client secret as `client_secret_*.apps.googleusercontent.com.json` in project root
   - First run auto-generates `token.pickle` after authentication
   - If auth fails, delete `token.pickle` and re-run to re-authenticate

3. **Attendee mapping** (`attendee_mapping.json`):
   - Maps names to email addresses for calendar invites
   - Add new attendees to the `attendees` array
   - Supports fuzzy matching via `fuzzy_match_threshold` (default: 0.8)

## Frontend Architecture

The frontend is built with **React 19 + TypeScript + Material-UI** and structured as:

- **`src/theme/`** - NVIDIA green theme (#76B900) with Material-UI overrides
- **`src/types/`** - TypeScript interfaces for workflow state and components
- **`src/hooks/`** - Custom hooks (`useMediaRecorder`, `useWorkflowStream`, `useOrchestrator`)
- **`src/context/`** - Global `WorkflowContext` for state management
- **`src/components/`** - React components organized by feature (Recording, Workflow, Results)

**Key libraries**: Axios (HTTP), Emotion (CSS-in-JS), Material-UI (components), Server-Sent Events (real-time updates)

## Real-Time Workflow Visualization

The frontend displays live workflow progress via Server-Sent Events (SSE):

- **Timeline Bar**: Shows all 9 agents (pending/active/completed) with progress percentage
- **Expandable Agent Cards**: Real-time status updates with auto-collapse on completion
- **SSE Streaming**: Backend emits `stage_start` and `stage_complete` events to `/stream-workflow` endpoint
- **NVIDIA Theme**: Green (#76B900) animations with pulsing active agent indicator

**Technical**: `orchestrator_agent.py` emits workflow events → `server.py` broadcasts via SSE → React hooks (`useWorkflowStream`) update UI in real-time

## Architecture

### Multi-Agent Workflow (LangGraph)

The system uses LangGraph to orchestrate a sequential workflow with the following nodes:

1. **analyze_transcript** - Extracts key information from meeting transcripts (title, participants, topics, action items)
2. **fetch_calendar_context** - Retrieves calendar events from Google Calendar (past 30 days + next 30 days)
3. **find_related_meetings** - Uses Nemotron to identify related past meetings based on transcript analysis
4. **plan_actions** - Decides what actions to take with enhanced prompts for duration/date/attendee extraction
5. **execute_actions** - Executes planned actions in two phases (FIND_SLOT/ADD_NOTES first, then CREATE_EVENT)
6. **generate_summary** - Creates HTML-formatted summary and sends email to stakeholders

The workflow is defined in `orchestrator_agent.py` using the `StateGraph` pattern. Each node is an async function that receives `OrchestratorState` and returns updated state.

### Core Components

- **orchestrator_agent.py** - Main LangGraph workflow orchestrator
  - `MeetingOrchestrator` class contains all node logic
  - `create_orchestrator_graph()` builds and compiles the LangGraph workflow
  - State flows sequentially: START → analyze → fetch → find → plan → execute → summary → END
  - `_extract_json()` handles LLM response parsing with `<think>` block removal
  - `_create_html_summary()` generates beautiful HTML emails with gradient headers and action tables

- **calender_tool.py** (note: misspelled "calendar" in filename) - Google Calendar API integration
  - Uses OAuth 2.0 authentication with `token.pickle` for credentials
  - Calendar ID is hardcoded in `CALEN_ID` variable
  - Timezone: `America/New_York` via `pytz.timezone()` (lines 9, 26)
  - Key methods: `fetch_events()`, `create_event()`, `add_notes_to_event()`, `find_available_slots()`

- **email_tool.py** - Gmail API integration
  - Uses OAuth 2.0 with `token.pickle` for credentials
  - `send_email()` supports both plain text and HTML bodies (multipart MIME)

- **translate.py** - `NemotronTranscriptAgent` for advanced transcript analysis with specialized persona

- **server.py** - Flask backend for audio transcription
  - Accepts audio uploads, converts to 16kHz mono WAV via ffmpeg
  - Calls NVIDIA ASR (transcribe_file.py from python-clients)
  - Requires `API_KEY` environment variable

### Web Interface

The frontend (`frontend/` React app) provides:
- Audio recording and playback controls
- Real-time workflow visualization with SSE updates
- Meeting transcript display
- Action approval/cancellation interface

Backend API endpoints:
- `POST /transcribe` - Accepts audio files, returns transcript
- `POST /run-orchestrator` - Triggers workflow execution
- `GET /stream-workflow` - SSE stream for real-time agent updates

### NVIDIA Nemotron Integration

The orchestrator uses NVIDIA Nemotron (`nvidia/llama-3.3-nemotron-super-49b-v1.5`) for LLM operations:
- All LLM calls go through `_call_nemotron()` helper method
- JSON responses are extracted using `_extract_json()` which handles markdown code blocks and `<think>` tags
- Temperature: 0.2, Top_p: 0.95, Max tokens: 4096

**IMPORTANT**: API keys are currently hardcoded in source files. These should be moved to environment variables.

## Installation Prerequisites

1. **Backend Dependencies**: `pip install -r requirements.txt` (installs all Python packages)
2. **Frontend Dependencies**: `cd frontend && npm install` (installs React/TypeScript packages)
3. **System Requirements**: FFmpeg installed and in PATH (for audio processing)

## State Management

The `OrchestratorState` (Pydantic model) contains:
- `audio_transcript` - Input meeting transcript text
- `calendar_events` - List of CalendarEvent objects from Google Calendar
- `related_past_meetings` - AI-identified related meetings
- `planned_actions` - List of MeetingAction objects to execute
- `execution_results` - String results from action execution
- `messages` - LangGraph message history (annotated with `add_messages`)

## Action Types

The system supports four action types (defined in `ActionType` enum):
- `ADD_NOTES` - Append notes to existing calendar event
- `CREATE_EVENT` - Create new calendar event with specific date, duration, and attendees
- `FIND_SLOT` - Find available time slots (9-5 working hours, skips weekends)
- `UPDATE_EVENT` - Update existing event properties

### MeetingAction Model

Each action includes:
- `action_type` - One of the four ActionType values
- `calendar_event_id` - Event ID for ADD_NOTES/UPDATE_EVENT
- `event_title` - Title for CREATE_EVENT
- `event_date` - ISO format date (YYYY-MM-DD)
- `notes` - Description/notes content
- `duration_minutes` - Meeting duration (default: 60)
- `attendees` - List of attendee names (e.g., `["rahual", "kritika"]`) - automatically mapped to emails
- `reasoning` - LLM's explanation for this action

## Timezone & Date Handling

### Timezone Configuration

All calendar operations use `America/New_York` timezone via `pytz`:
```python
TIMEZONE = pytz.timezone('America/New_York')  # Auto-handles EST/EDT
```

Calendar events are created with proper timezone awareness using `TIMEZONE.localize()`.

### Date Parsing

The LLM prompt includes examples for converting natural language dates:
- "tomorrow" → next calendar day
- "next week" → 7 days from today
- "next Tuesday" → next occurrence of Tuesday
- "in 3 days" → today + 3 days

Current date is injected into the prompt dynamically.

### Duration Detection

The LLM extracts duration from patterns like:
- "30-minute meeting" → 30
- "2-hour session" → 120
- "half hour" → 30
- "quick 15-minute sync" → 15
- Default: 60 minutes if not specified

## Multi-Action Planning (NEW!)

### Overview

The action planner now intelligually generates **multiple distinct actions** when a transcript mentions multiple scheduling requests or action items. This is critical for the hackathon demo where a single meeting might discuss 3-5 different follow-up items.

### How It Works

1. **Extract Analysis Data**: The `analyze_transcript` node extracts structured `action_items` from the full transcript
2. **Pass to Planner**: The `plan_actions` node receives:
   - Full transcript (2000 characters, up from 800)
   - Explicit `action_items` array
   - `mentioned_dates` array
   - `participants` array
   - Key topics
3. **Generate Multiple Actions**: The LLM is prompted with explicit instructions:
   ```
   ⚠️ CRITICAL INSTRUCTION: GENERATE MULTIPLE ACTIONS FOR MULTIPLE REQUESTS
   - If the transcript contains MULTIPLE distinct meetings, events, or tasks:
     - Create a SEPARATE action for EACH distinct item
     - Do NOT consolidate multiple scheduling requests into a single action
   ```
4. **Return Array**: Returns an array with one action per distinct item

### Example

**Input Transcript** (695 characters):
```
We need to organize several meetings for next week.

First, I need to schedule a 30-minute standup with Rahual on Monday afternoon at 2 PM to discuss the project status.

Second, let's set up a 2-hour planning session with Kritika on Wednesday morning to go over the Q4 roadmap and budget strategy.

Third, we should schedule an all-hands meeting with the entire team (Rahual, Kritika, and Biraj) on Friday at 3 PM for a 60-minute project update.

Also, I think we should add a note to yesterday's Project Phoenix meeting about the budget approval we discussed there.

Finally, could we find some available time slots next week in the morning hours for a potential sync with the finance team?
```

**Output: 5 Planned Actions**
1. **CREATE_EVENT** - Project Status Standup (Rahual, 30min, Nov 3)
2. **CREATE_EVENT** - Q4 Roadmap Planning (Kritika, 120min, Nov 5)
3. **CREATE_EVENT** - All-Hands Project Update (Rahual/Kritika/Biraj, 60min, Nov 7)
4. **ADD_NOTES** - Budget approval note to Phoenix meeting
5. **FIND_SLOT** - Available morning slots for finance sync

### Key Improvements (October 2025)

1. **Increased Context Window**: Transcript sent to LLM increased from 800 to 2000 characters
2. **Structured Action Items**: Extracted action_items passed explicitly to planner
3. **Enhanced Prompt**: Clear multi-action instruction at top of system prompt
4. **Better Logging**: Detailed logs show how many actions were planned and their details

### Debugging Multi-Action Issues

If you're not seeing multiple actions generated:

1. **Check extracted action_items**: Look for logs in plan_actions step
   ```
   INFO:orchestrator_agent:PLAN_ACTIONS CONTEXT:
   INFO:orchestrator_agent:  Action items count: 5
   INFO:orchestrator_agent:  Action items: [...]
   ```

2. **Check LLM response**: The raw actions response should contain array with multiple items
   ```
   INFO:orchestrator_agent:Raw actions response from Nemotron:
   [
       {"action_type": "CREATE_EVENT", ...},
       {"action_type": "CREATE_EVENT", ...},
       ...
   ]
   ```

3. **Check parsed actions**: Final count should match analysis
   ```
   INFO:orchestrator_agent:✓ Planned 5 actions:
     Action 1: ActionType.CREATE_EVENT
     Action 2: ActionType.CREATE_EVENT
     ...
   ```

### Testing Multi-Action Planning

Use this test script to verify multi-action behavior:

```bash
python /tmp/test_multi_action.py
```

Expected output: 5 actions for the test transcript above.

## Email Recipients & Attendee Mapping

### Email Recipients

Email summaries are sent to hardcoded recipients in `orchestrator_agent.py:602`:
- rahual.rai@bison.howard.edu
- kritika.pant@bison.howard.edu
- biraj.dahal@bison.howard.edu

Change these addresses in the `generate_summary()` method.

### Attendee Mapping

The `ATTENDEE_MAP` dictionary (orchestrator_agent.py:25-29) maps names to email addresses:
```python
ATTENDEE_MAP = {
    "rahual": "rahual.rai@bison.howard.edu",
    "kritika": "kritika.pant@bison.howard.edu",
    "biraj": "biraj.dahal@bison.howard.edu"
}
```

When the LLM identifies attendees in a transcript, it outputs lowercase names (e.g., `["rahual", "kritika"]`), which are automatically converted to email addresses for calendar invites.

## Calendar Configuration

The system uses a specific Google Calendar ID defined in `calender_tool.py:28`:
```python
CALEN_ID = '1e48c44c1ad2d312b31ee14323a2fc98c71147e7d43450be5210b88638c75384@group.calendar.google.com'
```

Update this to use a different calendar.

## Testing

To debug the real-time workflow visualization:
- Start backend: `python server.py` (port 5000)
- Start frontend: `cd frontend && npm start` (port 3000)
- Open DevTools Network tab → look for `/stream-workflow` connection (EventStream, `text/event-stream` MIME type)
- Watch XHR messages for `stage_start` and `stage_complete` events

To test with a custom transcript, edit the `sample_transcript` in `orchestrator_agent.py:main()` and run `python orchestrator_agent.py`.

For ASR transcription testing:
```bash
cd python-clients/scripts/asr
python transcribe_file.py --input_file /path/to/audio.wav
```
Requires valid NVIDIA API key and gRPC connectivity to `grpc.nvcf.nvidia.com:443`.

## Development Notes

- The codebase uses Python 3.13+ (based on requirements.txt)
- All async operations use `asyncio.run()` or `await`
- Google API credentials are stored in `token.pickle` (not in git)
- The requirements.txt contains full Anaconda environment exports - many dependencies are unused
- Action type normalization handles uppercase LLM responses (e.g., "ADD_NOTES" → "add_notes")
- Two-phase execution ensures FIND_SLOT results are available for CREATE_EVENT actions

## Attendee Mapping System

### Structure
The attendee system has evolved from hardcoded dictionaries to a configurable `attendee_mapping.json`:

```json
{
  "attendees": [
    {
      "primary_name": "rahual",
      "email": "rahual.rai@bison.howard.edu",
      "aliases": ["Rahual", "RAHUAL", "rahual rai", "Rahual Rai", "rai"],
      "first_name": "Rahual",
      "last_name": "Rai"
    }
  ],
  "default_domain": "example.com",
  "fuzzy_match_threshold": 0.8
}
```

### Name Matching Process
1. **Exact match** - Check `primary_name` and `aliases` for exact match (case-insensitive)
2. **Fuzzy match** - Use sequence matching against aliases (threshold: 0.8 by default, configurable)
3. **Auto-generate** - If no match found, generate email as `firstname.lastname@default_domain` or `firstname@default_domain`

### Adding New Attendees
Edit `attendee_mapping.json` and add to the `attendees` array:
```json
{
  "primary_name": "newperson",
  "email": "newperson@company.com",
  "aliases": ["NewPerson", "New Person", "np"],
  "first_name": "New",
  "last_name": "Person"
}
```

### Fuzzy Matching Adjustment
Modify `fuzzy_match_threshold` in `attendee_mapping.json` to adjust matching sensitivity:
- Higher value (0.95): Stricter matching, more auto-generation
- Lower value (0.7): More lenient matching, accepts partial name variations

## Module Dependencies

### Core Modules
- **orchestrator_agent.py** - Main orchestration, imports `CalendarAgentTool`, `GmailAgentTool`
- **calender_tool.py** - Google Calendar API, requires OAuth and timezone configuration
- **email_tool.py** - Gmail API, uses same OAuth credentials as calendar
- **translate.py** - Transcript analysis utilities (imported as needed)

### Frontend & Server
- **server.py** - Flask app serving `/transcribe` and `/stream-workflow` endpoints
- **frontend/src/App.tsx** - Main React app component
- **frontend/src/context/WorkflowContext.tsx** - Global workflow state management

### External Dependencies
- **python-clients/** - NVIDIA Riva ASR client library (submodule containing gRPC clients)
  - Used by `server.py` to transcribe audio via `transcribe_file.py` script
  - Requires `grpc.nvcf.nvidia.com:443` connectivity
  - Depends on NVIDIA API key for authentication

## Configuration & Troubleshooting

### Changing Calendar
Update `CALEN_ID` in `calender_tool.py:28`:
```python
CALEN_ID = 'your-calendar-id@group.calendar.google.com'
```
Find your calendar ID in Google Calendar settings.

### Resetting Google OAuth
If you encounter 403 errors or permission issues:
1. Delete `token.pickle`
2. Re-run the application to trigger OAuth re-authentication
3. Ensure the OAuth consent screen has requested these scopes:
   - `https://www.googleapis.com/auth/calendar`
   - `https://www.googleapis.com/auth/gmail.send`

### Debugging
Set logging level in code or via environment:
```python
logging.basicConfig(level=logging.DEBUG)
```
The `_LOGGER` is configured at module level in `orchestrator_agent.py`.

## Security Considerations

**CRITICAL**: The following secrets are currently hardcoded and should be moved to environment variables:
1. NVIDIA API key in `orchestrator_agent.py:41`
2. NVIDIA API key in `summarizer.py:5`
3. Google Calendar ID (less sensitive but should be configurable)

Use environment variables or a `.env` file (with python-dotenv) for production deployments.
