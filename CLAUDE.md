# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered meeting assistant that uses NVIDIA Nemotron LLM and LangGraph to orchestrate multi-agent workflows. The system analyzes meeting transcripts, manages calendar events, finds related meetings, and automatically sends HTML-formatted email summaries with timezone support.

**Frontend**: React 19 + TypeScript + Material-UI (MUI) on port 3000
**Backend**: Flask + LangGraph + NVIDIA Nemotron on port 5000
**Architecture**: Separate frontend/backend with Server-Sent Events (SSE) streaming for real-time workflow visualization

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

## Architecture Overview

### Multi-Agent Workflow (LangGraph)

The system orchestrates a sequential workflow with 9 agent nodes:

1. **Transcript Analyzer** - Extracts key information (title, participants, topics, action items)
2. **Research & Entity Extraction** - Analyzes entities and relationships (optional)
3. **Calendar Context Fetch** - Retrieves past 30 days + next 30 days of events
4. **Related Meetings Finder** - Identifies related past meetings using semantic similarity
5. **Action Planner** - Generates multiple distinct actions (CREATE_EVENT, ADD_NOTES, FIND_SLOT, UPDATE_EVENT)
6. **Decision Analyzer** - Evaluates feasibility, priority, and risks of planned actions
7. **Risk Assessor** - Identifies calendar conflicts, timeline issues, and blockers
8. **Action Executor** - Executes actions in two phases (FIND_SLOT/ADD_NOTES first, then CREATE_EVENT)
9. **Summary Generator** - Creates HTML summary and sends email to stakeholders

Each node is an async function that receives `OrchestratorState` and returns updated state. The workflow is defined using LangGraph's `StateGraph` pattern.

### Workflow State Flow

```
START → analyze_transcript → fetch_calendar_context → find_related_meetings
  → plan_actions → decision_agent → risk_assessment_agent → execute_actions
  → generate_summary → END
```

### Real-Time Execution Logging

Each agent emits logs as it executes:

**Log Types** (defined in `frontend/src/types/workflow.ts`):
- `thinking` - AI model's internal reasoning (from `<think>...</think>` tags)
- `input` - Data being processed by the agent
- `processing` - Steps being performed
- `api_call` - LLM API calls with latency metrics
- `output` - Results/conclusions from the agent
- `timing` - Performance measurements
- `error` - Exceptions and failures

**Log Flow**:
1. Backend agents emit logs via `emit_workflow_event()`
2. Logs are streamed to frontend via SSE `/stream-workflow` endpoint
3. Frontend `useWorkflowStream` hook receives logs and updates `WorkflowContext`
4. React components render logs in agent cards with type-based grouping

### Thinking Stream (Recent Addition)

When Nemotron includes `<think>...</think>` tags in responses:
1. Backend `extract_thinking_content()` extracts thinking text and cleans response
2. First 500 characters of thinking added as "thinking" log type
3. Frontend displays in dedicated "💭 AI Reasoning" accordion (green-styled)
4. Full thinking preserved on backend, truncated for UI performance

This is implemented in: `analyze_transcript`, `plan_actions`, `decision_agent`, `risk_assessment_agent`, `generate_summary`

## Frontend Architecture

The React 19 + TypeScript + Material-UI frontend is structured as:

- **`src/theme/`** - NVIDIA green theme (#76B900) with Material-UI overrides
- **`src/types/workflow.ts`** - TypeScript interfaces (LogEntry, WorkflowEvent, AgentCardState)
- **`src/hooks/`** - Custom hooks:
  - `useMediaRecorder` - Audio recording with WebAudio API
  - `useWorkflowStream` - SSE EventSource connection management
  - `useOrchestrator` - Orchestrator API calls
- **`src/context/WorkflowContext.tsx`** - Global state: agentCards, progress, expanded/collapsed states
- **`src/components/`** - React components:
  - `Recording/` - Audio input and playback
  - `Workflow/` - AgentCard (expandable log display), TimelineBar (progress indicator), WorkflowVisualization (card grid)
  - `Results/` - Summary display and action results

**Key Data Flow**:
1. User records audio → `Recording` component
2. `useOrchestrator` sends to `/transcribe` endpoint
3. Backend runs workflow, emits events to `/stream-workflow` (SSE)
4. `useWorkflowStream` receives events, dispatches to `WorkflowContext`
5. `AgentCard` components re-render with updated logs/status
6. Logs grouped by type in expandable accordions

## Backend Core Modules

### orchestrator_agent.py
- `MeetingOrchestrator` class contains all agent node functions
- `create_orchestrator_graph()` builds/compiles LangGraph workflow
- `emit_workflow_event()` broadcasts agent progress via SSE
- `extract_thinking_content()` extracts `<think>` tags from LLM responses
- `_call_nemotron()` helper for LLM API calls (temp 0.2, top_p 0.95, max_tokens 4096)
- `_extract_json()` parses JSON from responses, handles markdown code blocks

### calender_tool.py (note: misspelled "calendar")
- Google Calendar API integration with OAuth 2.0
- Key methods: `fetch_events()`, `create_event()`, `add_notes_to_event()`, `find_available_slots()`
- Timezone: `America/New_York` via `pytz.timezone()`
- Calendar ID hardcoded in `CALEN_ID` variable

### email_tool.py
- Gmail API integration with OAuth 2.0
- `send_email()` supports plain text and HTML bodies (multipart MIME)

### server.py
- Flask server with two main endpoints:
  - `POST /transcribe` - Audio file upload, 16kHz mono WAV conversion via ffmpeg, ASR via NVIDIA Riva
  - `GET /stream-workflow` - SSE stream for real-time agent updates
  - `POST /run-orchestrator` - Trigger orchestrator with transcript

## Action Planning

### Multi-Action Support

The planner generates **one action per distinct item** mentioned in transcripts:

**Action Types**:
- `CREATE_EVENT` - Schedule new calendar event (date, duration, attendees)
- `ADD_NOTES` - Append notes to existing event
- `FIND_SLOT` - Find available time slots (9-5 working hours, excludes weekends)
- `UPDATE_EVENT` - Modify existing event properties

**Input Context to Planner**:
- Full transcript (2000 character limit)
- Extracted `action_items` array from analysis
- `mentioned_dates` and `participants` arrays
- Key topics and related meetings

**Example**: Transcript mentioning 5 distinct items → 5 separate actions (not consolidated)

### Action Execution (Two-Phase)

**Phase 1** (Parallel):
- All `FIND_SLOT` actions execute first
- All `ADD_NOTES` and `UPDATE_EVENT` actions execute
- Results stored for Phase 2

**Phase 2** (Sequential):
- `CREATE_EVENT` actions use available slots from Phase 1
- If slot not found, defaults to 2 PM EST/EDT on specified date

## State Management

`OrchestratorState` (Pydantic model) contains:
- `audio_transcript` - Input meeting transcript
- `calendar_events` - List of CalendarEvent objects (past 30 days + next 30 days)
- `related_past_meetings` - AI-identified semantically related meetings
- `planned_actions` - List of MeetingAction objects
- `execution_results` - List of result dicts with status/message/details
- `messages` - LangGraph message history (annotated with `add_messages`)

## Timezone & Date Handling

All calendar operations use `America/New_York` timezone via `pytz`:
```python
TIMEZONE = pytz.timezone('America/New_York')  # Auto-handles EST/EDT
```

Date parsing from natural language:
- "tomorrow" → next calendar day
- "next week" → 7 days from today
- "next Tuesday" → next occurrence of Tuesday
- "in 3 days" → today + 3 days
- "november 7th" / "nov 7" → 2025-11-07

Duration extraction:
- "30-minute meeting" → 30 minutes
- "2-hour session" → 120 minutes
- "half hour" → 30 minutes
- Default: 60 minutes if not specified

## Testing & Debugging

### Real-Time Workflow Debugging
```bash
# Terminal 1: Start backend
python server.py

# Terminal 2: Start frontend
cd frontend && npm start

# Browser DevTools Network tab:
# - Filter for /stream-workflow (EventStream, text/event-stream MIME)
# - Watch Console for 📨, ✓, 🚨 emoji logs
# - Each agent card shows logs on expand
```

### Testing with Custom Transcripts
1. Edit `sample_transcript` in `orchestrator_agent.py:main()`
2. Run `python orchestrator_agent.py`
3. Check console logs for workflow execution

### ASR Transcription Testing
```bash
cd python-clients/scripts/asr
python transcribe_file.py --input_file /path/to/audio.wav
```
Requires valid NVIDIA API key and gRPC connectivity to `grpc.nvcf.nvidia.com:443`.

## Attendee Mapping System

### Structure
Configured in `attendee_mapping.json`:
```json
{
  "attendees": [
    {
      "primary_name": "rahual",
      "email": "rahual.rai@bison.howard.edu",
      "aliases": ["Rahual", "RAHUAL", "rahual rai", "Rahual Rai"],
      "first_name": "Rahual",
      "last_name": "Rai"
    }
  ],
  "default_domain": "example.com",
  "fuzzy_match_threshold": 0.8
}
```

### Name Matching Process
1. **Exact match** - Check `primary_name` and `aliases` (case-insensitive)
2. **Fuzzy match** - Sequence matching against aliases (configurable threshold)
3. **Auto-generate** - If no match, generate email as `firstname.lastname@default_domain`

### Adding Attendees
Edit `attendee_mapping.json` and add to `attendees` array. Adjust `fuzzy_match_threshold` (0.7-0.95) for stricter/looser matching.

## Configuration & Troubleshooting

### Email Recipients
Hardcoded in `orchestrator_agent.py:generate_summary()`:
```python
to_addresses=["rahual.rai@bison.howard.edu", "kritika.pant@bison.howard.edu", "biraj.dahal@bison.howard.edu"]
```
Change these addresses in the `generate_summary()` method.

### Calendar Configuration
Update `CALEN_ID` in `calender_tool.py:28`:
```python
CALEN_ID = 'your-calendar-id@group.calendar.google.com'
```
Find calendar ID in Google Calendar settings.

### Resetting Google OAuth
If encountering 403 errors:
1. Delete `token.pickle`
2. Re-run to trigger OAuth re-authentication
3. Ensure OAuth consent screen includes these scopes:
   - `https://www.googleapis.com/auth/calendar`
   - `https://www.googleapis.com/auth/gmail.send`

### Debugging Logs
Set logging level:
```python
logging.basicConfig(level=logging.DEBUG)
```
All modules use `_LOGGER` configured at module level for logging.

## Development Notes

- Python 3.13+ required
- All async operations use `asyncio.run()` or `await`
- Google credentials stored in `token.pickle` (not in git)
- Action type normalization handles uppercase LLM responses ("ADD_NOTES" → "add_notes")
- Two-phase execution ensures FIND_SLOT results available for CREATE_EVENT actions
- `requirements.txt` contains full Anaconda exports - many dependencies unused

## Security Considerations

**CRITICAL - Hardcoded Secrets**: Move these to environment variables:
1. NVIDIA API key in `orchestrator_agent.py:41`
2. NVIDIA API key in `summarizer.py:5`
3. Email recipient addresses (currently hardcoded in `generate_summary()`)
4. Google Calendar ID (currently hardcoded in `calender_tool.py:28`)

## Key Recent Changes (October 2025)

1. **Execution Logging** - All 9 agents now emit comprehensive logs (thinking, input, processing, api_call, output, error)
2. **AI Thinking Stream** - Extract and display `<think>...</think>` tags from Nemotron responses
3. **Card Expansion** - Agent cards remain expanded after completion to display logs
4. **Frontend Redesign** - Migrated from vanilla HTML/CSS/JS to React 19 + TypeScript + Material-UI
5. **Real-Time SSE** - Fixed EventSource connection to explicit backend URL (not proxy)
6. **Multi-Action Planning** - Generate multiple distinct actions from single meeting transcript

## Installation Prerequisites

1. **Backend Dependencies**: `pip install -r requirements.txt`
2. **Frontend Dependencies**: `cd frontend && npm install`
3. **System Requirements**: FFmpeg installed and in PATH (for audio processing)
