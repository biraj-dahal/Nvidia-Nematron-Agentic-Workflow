# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered meeting assistant that uses NVIDIA Nemotron LLM and LangGraph to orchestrate multi-agent workflows. The system analyzes meeting transcripts, manages calendar events, finds related meetings, and automatically sends HTML-formatted email summaries with timezone support.

**Frontend**: React 19 + TypeScript + Material-UI (MUI)
**Backend**: Flask + LangGraph + NVIDIA Nemotron
**Architecture**: Separate frontend (port 3000) and backend (port 5000) with SSE streaming

## Recent Enhancements

The system now includes:

- **EST/EDT Timezone Support**: All calendar operations use `pytz` with `America/New_York` timezone (auto-handles DST)
- **Smart Duration Detection**: Extracts meeting duration from natural language ("30-minute standup", "2-hour session", "half hour")
- **Natural Date Parsing**: Converts relative dates to ISO format ("tomorrow", "next week", "next Tuesday")
- **Automatic Attendee Invitations**: Maps names to emails via `ATTENDEE_MAP` and sends calendar invites
- **HTML Email Formatting**: Professional gradient-styled email summaries with responsive design
- **Improved JSON Parsing**: Handles LLM `<think>` blocks and balanced bracket counting
- **Two-Phase Execution**: FIND_SLOT actions execute first, then CREATE_EVENT can use discovered slots

## React Frontend Architecture (New!)

The frontend has been completely migrated from vanilla HTML/CSS/JS to **React 19 + TypeScript + Material-UI**:

### Project Structure

```
frontend/
├── src/
│   ├── theme/
│   │   └── nvidiaTheme.ts              # MUI theme with NVIDIA green (#76B900)
│   ├── types/
│   │   └── workflow.ts                 # All TypeScript interfaces & types
│   ├── hooks/
│   │   ├── useMediaRecorder.ts         # Audio recording logic
│   │   ├── useWorkflowStream.ts        # SSE connection for live events
│   │   ├── useOrchestrator.ts          # API calls to backend
│   │   └── index.ts                    # Barrel exports
│   ├── context/
│   │   └── WorkflowContext.tsx         # Global workflow state management
│   ├── components/
│   │   ├── Recording/
│   │   │   ├── RecordingControls.tsx   # Start/Stop buttons
│   │   │   ├── AudioPlayer.tsx         # Playback component
│   │   │   ├── TranscriptionDisplay.tsx# Transcript display
│   │   │   └── index.ts
│   │   ├── Workflow/
│   │   │   ├── TimelineBar.tsx         # 9-agent timeline with progress
│   │   │   ├── AgentCard.tsx           # Expandable agent status card
│   │   │   ├── WorkflowVisualization.tsx # Main workflow container
│   │   │   └── index.ts
│   │   └── Results/
│   │       ├── ActionCards.tsx         # Grid of planned actions
│   │       ├── ExecutionResults.tsx    # Execution result list
│   │       ├── Summary.tsx             # Meeting summary display
│   │       ├── ApprovalButtons.tsx     # Approve/Cancel buttons
│   │       └── index.ts
│   ├── App.tsx                         # Main app component
│   └── index.tsx                       # Providers & theme setup
└── package.json                        # Proxy: http://localhost:5000
```

### Key Technologies

- **React 19**: Latest React with automatic batching
- **TypeScript**: Full type safety across all components
- **Material-UI (v7)**: Professional component library with dark theme
- **Axios**: HTTP client for API requests
- **Emotion**: CSS-in-JS for styled components
- **Server-Sent Events (SSE)**: Real-time workflow updates

### Custom Hooks

**useMediaRecorder** - Audio recording
```typescript
const { recordingState, startRecording, stopRecording, resetRecording } = useMediaRecorder();
```

**useWorkflowStream** - Real-time SSE updates
```typescript
const { isConnected, startStream, closeStream, error } = useWorkflowStream(onEvent);
```

**useOrchestrator** - Backend API integration
```typescript
const { isLoading, error, result, transcribeAudio, runOrchestrator } = useOrchestrator();
```

### State Management

**WorkflowContext** provides global state:
```typescript
workflow: {
  isRunning: boolean;
  currentAgent: string | null;
  completedAgents: string[];
  agentCards: AgentCardState[];
  progress: number; // 0-100
}
```

### Theme

Uses NVIDIA-themed Material-UI with:
- Primary: `#76B900` (NVIDIA Green)
- Dark Background: `#000000`
- Card Background: `#1a1a1a`
- Full dark mode support with custom component overrides

### Running the Frontend

```bash
cd frontend
npm install
npm start
```

Runs on `http://localhost:3000` with proxy to backend on `http://localhost:5000`

## Real-Time Workflow Visualization

The system now features inline, ChatGPT-style workflow visualization that shows live progress as agents execute:

### Key Features

1. **Timeline Bar** - Shows all 9 agents with status indicators:
   - Pending (gray)
   - Active (green with pulsing glow animation)
   - Completed (green checkmark)
   - Progress bar fills as stages complete

2. **Expandable Agent Cards** - Click to expand/collapse:
   - Agent name and current status description
   - Real-time streaming updates as agent works
   - Status badge (Active/Completed/Error)
   - Auto-collapses when stage completes
   - Smooth animations for expand/collapse

3. **Real-Time Streaming** - Uses Server-Sent Events (SSE):
   - Backend emits `stage_start` and `stage_complete` events
   - Frontend receives updates in real-time
   - No polling, efficient one-way communication
   - Auto-scrolls to active agent for visibility

### Technical Implementation

**Backend (server.py)**:
- `/stream-workflow` endpoint: SSE stream for workflow events
- `broadcast_workflow_event()`: Sends events to all connected clients
- Thread-safe queue management for multiple clients

**Orchestrator (orchestrator_agent.py)**:
- `emit_workflow_event()`: Emits stage_start/stage_complete events
- Event callback system: Events flow from orchestrator to frontend
- All 9 agents (nodes) emit events at start and completion

**Frontend (script.js)**:
- `startWorkflowStream()`: Initiates SSE connection
- `handleWorkflowEvent()`: Processes incoming events
- `createAgentCard()`: Dynamically builds expandable card UI
- `updateTimeline()`: Updates timeline progress bar

**Styling (styles.css)**:
- NVIDIA green theme with animations
- Pulsing active agent indicator
- Smooth transitions and hover effects
- Custom scrollbar for event log

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

### Web UI & Recording

The repository includes a web interface for recording and transcribing meetings:

- **index.html** - Recording interface ("Core 4.0" app)
- **script.js** - Client-side audio recording and upload logic
- **styles.css** - NVIDIA-themed styling
- **server.py** - Flask backend with `/transcribe` endpoint

To run the web UI:
```bash
# Set NVIDIA API key
export API_KEY=your_nvidia_api_key

# Start Flask server
python server.py

# Open http://localhost:5000 in browser
```

Requirements: ffmpeg must be installed and in PATH for audio conversion.

### NVIDIA Nemotron Integration

The orchestrator uses NVIDIA Nemotron (`nvidia/llama-3.3-nemotron-super-49b-v1.5`) for LLM operations:
- All LLM calls go through `_call_nemotron()` helper method
- JSON responses are extracted using `_extract_json()` which handles markdown code blocks and `<think>` tags
- Temperature: 0.2, Top_p: 0.95, Max tokens: 4096

**IMPORTANT**: API keys are currently hardcoded in source files. These should be moved to environment variables.

## Running the Application

### Prerequisites

1. **Install Dependencies**:
   ```bash
   pip install openai langgraph langchain-core google-api-python-client google-auth google-auth-oauthlib pydantic pytz python-dateutil flask flask-cors
   ```

2. **Google OAuth Setup**:
   - Place OAuth client secret file: `client_secret_175568546829-c0dm1uj4mhr0k36vb1t12qp6hgmst5hb.apps.googleusercontent.com.json` in project root
   - On first run, authenticate to create `token.pickle`
   - **Required scopes**:
     - `https://www.googleapis.com/auth/calendar`
     - `https://www.googleapis.com/auth/gmail.send`
   - If you encounter a 403 error, delete `token.pickle` and re-authenticate

3. **NVIDIA API Key**:
   - Currently hardcoded in `orchestrator_agent.py:41` - should be replaced with environment variable
   - For Flask server, set as `API_KEY` environment variable

### Execute Main Workflow

```bash
python orchestrator_agent.py
```

This runs the sample workflow with a hardcoded transcript. Modify the `sample_transcript` in the `main()` function to test with different meeting content.

### Test Individual Tools

```bash
# Test calendar tool independently
python calender_tool.py

# The email and summarizer tools don't have standalone test modes
```

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

## Testing the Inline Workflow Visualization

To see the real-time workflow visualization in action:

1. **Start the Flask server**:
   ```bash
   python server.py
   ```

2. **Open the web interface**:
   ```
   http://localhost:3000
   ```

3. **Record a meeting or paste a transcript**:
   - Click "Start Recording" to capture audio
   - OR manually provide transcript via the API

4. **Watch the visualization**:
   - The timeline bar appears showing all 9 agents
   - As each agent executes, it becomes highlighted in green with pulsing animation
   - Agent cards appear below showing real-time status
   - Click any card to expand and see full details
   - Progress bar fills as agents complete
   - When agent finishes, card auto-collapses and turns completed (solid green)

5. **Monitor SSE Connection**:
   - Open browser DevTools → Network tab
   - Look for `/stream-workflow` connection
   - Should show as EventStream with `text/event-stream` MIME type
   - Watch XHR messages for `stage_start` and `stage_complete` events

## Common Development Commands

### Run the Main Orchestrator
```bash
python orchestrator_agent.py
```
This executes a sample workflow with hardcoded transcript. Modify `sample_transcript` in `main()` to test different content.

### Test Calendar Tool
```bash
python calender_tool.py
```
Tests Google Calendar API integration independently.

### Run the Web UI & Recording
```bash
# Set NVIDIA API key
export API_KEY=your_nvidia_api_key

# Start Flask server (runs on http://localhost:5000)
python server.py
```

### Test ASR Transcription (Python-Clients)
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
- **server.py** - Flask app serving `index.html` and handling `/transcribe` endpoint
- **index.html** - Main UI for audio recording and workflow execution
- **workflow_viewer.html** - Separate visualization interface (displays workflow graph in real-time)
- **script.js** - Client-side audio recording and upload logic
- **styles.css** - NVIDIA-themed styling applied to both interfaces

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
