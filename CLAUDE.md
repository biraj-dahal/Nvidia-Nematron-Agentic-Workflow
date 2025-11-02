# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered meeting assistant that uses NVIDIA Nemotron LLM and LangGraph to orchestrate multi-agent workflows. The system analyzes meeting transcripts, manages calendar events, finds related meetings, and automatically sends HTML-formatted email summaries with timezone support.

**Frontend**: React 19 + TypeScript + Material-UI (MUI) on port 3000
**Backend**: Flask + LangGraph + NVIDIA Nemotron on port 5000
**Architecture**: Separate frontend/backend with Server-Sent Events (SSE) streaming for real-time workflow visualization

## Development Commands

### Backend Setup & Running

```bash
# Install dependencies
pip install -r requirements.txt

# Set NVIDIA API key
export API_KEY="your_nvidia_api_key_here"

# Start Flask server (handles /transcribe endpoint + SSE streaming)
python server.py  # Listens on http://localhost:5000

# Run main orchestrator workflow with test transcript (standalone)
python orchestrator_agent.py

# Test Google Calendar integration (requires OAuth setup)
python calender_tool.py
```

### Frontend Setup & Running

```bash
cd frontend

# Install dependencies
npm install

# Start development server (port 3000, proxies API calls to localhost:5000)
npm start

# Run Jest tests in watch mode
npm test

# Build for production
npm run build

# Lint TypeScript/React code
npm run lint
```

### Testing

**Backend Tests** (python-clients/tests):
```bash
# Run unit tests
cd python-clients
python -m pytest tests/unit/

# Run with verbose output
python -m pytest tests/unit/ -v

# Run specific test file
python -m pytest tests/unit/test_nlp.py

# Run integration tests (requires NVIDIA API credentials)
python -m pytest tests/integration/ -v
```

**Full Stack Testing**:
```bash
# Terminal 1: Start backend
python server.py

# Terminal 2: Start frontend
cd frontend && npm start

# Terminal 3: Test workflow
# Open http://localhost:3000 and record audio to test end-to-end
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

## Backend Architecture

### File Organization

**Root Level Files** (meeting orchestration):
- `server.py` - Flask server with SSE streaming and audio transcription
- `orchestrator_agent.py` - LangGraph workflow orchestration (9 agents)
- `calender_tool.py` - Google Calendar API integration (OAuth 2.0)
- `email_tool.py` - Gmail API integration for sending HTML summaries
- `attendee_mapping.json` - Name-to-email mappings with fuzzy matching config

**python-clients/** (NVIDIA SDK for ASR/NLP):
- Separate package for NVIDIA Riva and NIM client integrations
- Contains reusable ASR clients and tests in `tests/unit/` and `tests/integration/`

### Core Backend Modules

#### orchestrator_agent.py (Primary)
- `MeetingOrchestrator` class - Contains all 9 agent node functions
- `create_orchestrator_graph()` - Builds/compiles LangGraph StateGraph workflow
- `emit_workflow_event()` - Broadcasts agent progress to SSE clients in real-time
- `extract_thinking_content()` - Parses `<think>...</think>` tags from Nemotron responses
- `_call_nemotron()` - Helper for LLM API calls (temp 0.2, top_p 0.95, max_tokens 4096)
- `_extract_json()` - Parses JSON from LLM responses, handles markdown code blocks
- `fuzzy_match_name()` - Maps meeting attendees to emails using sequence matching
- `load_attendee_mapping()` - Loads attendee_mapping.json or fallback hardcoded mapping

#### server.py (Flask API)
Main endpoints:
- `POST /transcribe` - Audio upload, ffmpeg conversion to 16kHz mono WAV, NVIDIA Riva ASR transcription
- `GET /stream-workflow` - Server-Sent Events (SSE) stream for real-time workflow updates
- `POST /run-orchestrator` - Trigger orchestrator with transcript text
- `convert_to_nvidia_format()` - Uses ffmpeg or pydub for audio conversion

#### calender_tool.py (Note: Misspelled "calendar")
- Google Calendar API v3 integration with OAuth 2.0
- Key methods: `fetch_events()`, `create_event()`, `add_notes_to_event()`, `find_available_slots()`
- Timezone: Hardcoded `America/New_York` via `pytz.timezone()`
- Calendar ID: Hardcoded in `CALEN_ID` variable (should be moved to environment)
- Supports 2-phase action execution (find slots first, then create events)

#### email_tool.py
- Gmail API integration with OAuth 2.0
- `send_email()` - Supports plain text and HTML body formatting (multipart MIME)
- Used for sending HTML-formatted meeting summaries to stakeholders

### Data Flow

```
Audio Input → convert_to_nvidia_format() → NVIDIA Riva ASR
   ↓
Flask /transcribe endpoint captures transcript
   ↓
/run-orchestrator triggers workflow
   ↓
LangGraph orchestrates 9 agents:
  1. analyze_transcript → 2. fetch_calendar_context → 3. find_related_meetings
  4. plan_actions → 5. decision_agent → 6. risk_assessment_agent
  7. execute_actions → 8. generate_summary → END
   ↓
emit_workflow_event() streams updates to SSE clients
   ↓
generate_summary() sends email + calender_tool creates/updates events
```

## Frontend-Backend Communication

### API Contract

**Audio Recording Flow:**
1. Frontend (`Recording` component) captures WAV blob from WebAudio API
2. Sends POST to `/transcribe` with FormData containing audio file
3. Backend converts to 16kHz mono, calls NVIDIA Riva ASR
4. Returns JSON: `{ transcript: "text", duration: ms }`

**Workflow Execution Flow:**
1. Frontend sends POST to `/run-orchestrator` with `{ transcript: "text" }`
2. Backend starts LangGraph workflow in background
3. Agents call `emit_workflow_event()` to broadcast progress
4. Frontend connects to `GET /stream-workflow` (SSE EventSource)
5. Frontend receives real-time log events: `{ agent, type, log, timestamp }`
6. Workflow completes, final event includes `execution_results` and email status

**Event Types Streamed:**
- `thinking` - AI reasoning from `<think>` tags
- `input` - Data being processed
- `processing` - Steps being executed
- `api_call` - LLM API calls with latency
- `output` - Agent results/conclusions
- `timing` - Performance measurements
- `error` - Exceptions during execution

### Development Patterns

**Adding a New Agent:**
1. Define async function in `MeetingOrchestrator` class (orchestrator_agent.py)
2. Function signature: `async def agent_name(self, state: OrchestratorState) -> Dict`
3. Use `self.emit_workflow_event()` for logging/progress
4. Return updated state dict with modified fields
5. Add node to graph in `create_orchestrator_graph()`: `graph.add_node("node_name", self.agent_name)`
6. Add edge to route from previous node
7. Frontend automatically displays new agent in workflow visualization

**Modifying Agent Logging:**
1. Call `emit_workflow_event(agent="agent_name", log_type="type", log="message")`
2. Log types must match TypeScript enum in `frontend/src/types/workflow.ts`
3. Logs are queued and broadcast to all SSE-connected clients
4. Frontend groups logs by type in expandable accordions

**Frontend State Management:**
1. Global state in `WorkflowContext` (agentCards, progress, expanded/collapsed)
2. `useWorkflowStream` hook manages EventSource connection and state updates
3. Component re-renders triggered by context updates
4. Agent card expanded state persists during workflow execution

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

### Environment Variable Setup

**Required:**
- `API_KEY` - NVIDIA API key for Nemotron and Riva services

**Optional (defaults shown):**
```bash
export API_KEY="your_nvidia_api_key_here"
export NEMOTRON_MODEL="nvidia/llama-3.3-nemotron-super-49b-v1.5"
```

### Email Recipients
Hardcoded in `orchestrator_agent.py` → `MeetingOrchestrator.generate_summary()`:
```python
to_addresses=["rahual.rai@bison.howard.edu", "kritika.pant@bison.howard.edu", "biraj.dahal@bison.howard.edu"]
```
**To change:** Edit the list in the `generate_summary()` method. These should be environment variables in production.

### Calendar Configuration
Hardcoded in `calender_tool.py:28`:
```python
CALEN_ID = 'your-calendar-id@group.calendar.google.com'
```
Find your calendar ID in Google Calendar → Settings → Calendar integration section. **Should be moved to environment variable.**

### Common Development Issues

**Issue: "API_KEY environment variable is not set"**
- Solution: `export API_KEY="your-key-here"` before running Flask server
- Or add to `.env` file and load with `python-dotenv`

**Issue: Frontend can't connect to backend (CORS errors)**
- Check that backend is running: `python server.py` should show "* Running on http://127.0.0.1:5000"
- Frontend proxy is set to `http://localhost:4000` in package.json (may need to update)
- Verify Flask CORS is initialized: `CORS(app)` in server.py

**Issue: SSE connection drops or doesn't receive events**
- Check Network tab in DevTools: filter for "stream-workflow" request
- Should be "pending" with Content-Type `text/event-stream`
- If connection closes, check backend logs for workflow errors
- Event queue may be full if processing is slow - check `broadcast_workflow_event()` logs

**Issue: Audio transcription fails**
- Ensure FFmpeg is installed: `which ffmpeg`
- Check file is valid WAV: `ffmpeg -i recording.wav`
- Verify NVIDIA Riva connectivity: requires `grpc.nvcf.nvidia.com:443` access
- Try `python-clients/scripts/asr/transcribe_file.py` directly to debug

**Issue: Calendar events not being created**
1. Delete generated OAuth credentials and re-authenticate: `rm token.pickle`
2. Ensure OAuth scopes include:
   - `https://www.googleapis.com/auth/calendar`
   - `https://www.googleapis.com/auth/gmail.send`
3. Check email configured in attendee_mapping.json matches attendees in transcript
4. Look for "FIND_SLOT" action - if no available slots, defaults to 2 PM EST

**Issue: Frontend types don't match backend events**
- Ensure `frontend/src/types/workflow.ts` has all log types your agents emit
- Agent must send exactly: `emit_workflow_event(agent="name", log_type="type", log="msg")`
- Valid types: `thinking`, `input`, `processing`, `api_call`, `output`, `timing`, `error`

### Debugging Logs
Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Backend modules use `_LOGGER` for structured logging. Check orchestrator_agent.py line ~30 for logger initialization.

Monitor workflow in real-time:
```bash
# Terminal 1: Backend with verbose logging
python server.py 2>&1 | grep -E "broadcast|emit|agent"

# Terminal 2: Frontend dev mode
cd frontend && npm start

# Terminal 3: Trigger workflow
curl -X POST http://localhost:5000/run-orchestrator \
  -H "Content-Type: application/json" \
  -d '{"transcript": "schedule a meeting with rahual tomorrow at 2pm"}'
```

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

## Key Code Patterns & Architectural Decisions

### State Management (OrchestratorState)
Pydantic model defined in orchestrator_agent.py containing:
- `audio_transcript` - Input text
- `calendar_events` - CalendarEvent list (60-day window)
- `related_past_meetings` - Semantically similar meetings found by agent
- `planned_actions` - List of MeetingAction objects (CREATE_EVENT, ADD_NOTES, etc.)
- `execution_results` - Results from executing actions
- `messages` - LangGraph message history for context

**Pattern:** Each agent receives full state, modifies relevant fields, returns updated state dict. LangGraph's `add_messages` annotation handles message history automatically.

### Event Emission Pattern
```python
self.emit_workflow_event(
    agent="agent_name",
    log_type="processing",  # Must match TypeScript enum
    log="Human readable message"
)
```
Every major step should emit at least:
1. `input` - What the agent received
2. `processing` - What it's doing
3. `output` or `error` - Result

### Action Execution Pattern (Two-Phase)
**Phase 1** (Parallel): FIND_SLOT, ADD_NOTES, UPDATE_EVENT
- Results stored in execution_results
- Next phase reads these results

**Phase 2** (Sequential): CREATE_EVENT
- Uses slot recommendations from Phase 1
- Falls back to 2 PM EST if no slot available

### LangGraph Workflow Structure
```python
graph = StateGraph(OrchestratorState)
graph.add_node("node_name", self.agent_function)
graph.add_edge("source_node", "target_node")
graph.add_edge("final_node", END)
graph.set_entry_point("first_node")
return graph.compile()
```

## Known Limitations & Technical Debt

1. **Hardcoded Configuration**
   - Email recipients hardcoded in generate_summary()
   - Calendar ID hardcoded in calender_tool.py
   - NVIDIA API key passed directly (should use environment variables)
   - **Fix:** Move to environment variables or config file

2. **SSE Queue Management**
   - Event queue can overflow if processing slow (workflow_event_queues list)
   - Dead queues removed only during broadcasts
   - **Fix:** Implement max queue size with timeout eviction

3. **Fuzzy Matching Sensitivity**
   - Single threshold (0.8) for all attendees
   - May generate false positives or miss legitimate matches
   - **Fix:** Per-attendee thresholds or ML-based matching

4. **Audio Conversion Fallbacks**
   - Uses FFmpeg first, falls back to pydub
   - pydub less reliable for WAV conversion
   - **Fix:** Standardize on FFmpeg, make pydub optional

5. **OAuth Token Handling**
   - Generated on first run, persists locally
   - No token refresh mechanism
   - **Fix:** Implement refresh token flow

6. **Error Handling**
   - Limited retry logic for API calls
   - 403 errors from Google Calendar often require manual re-auth
   - **Fix:** Implement exponential backoff and auto-retry

## Installation Prerequisites

1. **Backend Dependencies**: `pip install -r requirements.txt`
   - Note: requirements.txt has full Anaconda export (many unused dependencies)
   - Consider creating minimal requirements file for faster installation
2. **Frontend Dependencies**: `cd frontend && npm install`
3. **System Requirements**: FFmpeg installed and in PATH (for audio processing)
