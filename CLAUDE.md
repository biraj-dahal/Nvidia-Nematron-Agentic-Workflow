# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered meeting assistant that uses NVIDIA Nemotron LLM and LangGraph to orchestrate multi-agent workflows. The system analyzes meeting transcripts, manages calendar events, finds related meetings, and automatically sends email summaries.

## Architecture

### Multi-Agent Workflow (LangGraph)

The system uses LangGraph to orchestrate a sequential workflow with the following nodes:

1. **analyze_transcript** - Extracts key information from meeting transcripts (title, participants, topics, action items)
2. **fetch_calendar_context** - Retrieves calendar events from Google Calendar (past 30 days + next 30 days)
3. **find_related_meetings** - Uses Nemotron to identify related past meetings based on transcript analysis
4. **plan_actions** - Decides what actions to take (ADD_NOTES, CREATE_EVENT, FIND_SLOT, UPDATE_EVENT)
5. **execute_actions** - Executes planned actions using calendar and email tools
6. **generate_summary** - Creates final summary and sends email to stakeholders

The workflow is defined in `orchestrator_agent.py` using the `StateGraph` pattern. Each node is an async function that receives `OrchestratorState` and returns updated state.

### Core Components

- **orchestrator_agent.py** - Main LangGraph workflow orchestrator
  - `MeetingOrchestrator` class contains all node logic
  - `create_orchestrator_graph()` builds and compiles the LangGraph workflow
  - State flows sequentially: START → analyze → fetch → find → plan → execute → summary → END

- **calender_tool.py** (note: misspelled "calendar" in filename) - Google Calendar API integration
  - Uses OAuth 2.0 authentication with `token.pickle` for credentials
  - Calendar ID is hardcoded in `CALEN_ID` variable
  - Key methods: `fetch_events()`, `create_event()`, `add_notes_to_event()`, `find_available_slots()`

- **email_tool.py** - Gmail API integration
  - Uses OAuth 2.0 with `token.pickle` for credentials
  - `send_email()` sends messages via Gmail API

- **summarizer.py** - NVIDIA Nemotron API client example (basic usage)

### NVIDIA Nemotron Integration

The orchestrator uses NVIDIA Nemotron (`nvidia/llama-3.3-nemotron-super-49b-v1.5`) for LLM operations:
- All LLM calls go through `_call_nemotron()` helper method
- JSON responses are extracted using `_extract_json()` which handles markdown code blocks
- Temperature: 0.2, Top_p: 0.95, Max tokens: 4096

**IMPORTANT**: API keys are currently hardcoded in source files. These should be moved to environment variables.

## Running the Application

### Prerequisites

1. **Install Dependencies**:
   ```bash
   pip install openai langgraph langchain-core google-api-python-client google-auth google-auth-oauthlib pydantic
   ```

2. **Google OAuth Setup**:
   - Place OAuth client secret file: `client_secret_175568546829-c0dm1uj4mhr0k36vb1t12qp6hgmst5hb.apps.googleusercontent.com.json` in project root
   - On first run, authenticate to create `token.pickle`
   - **IMPORTANT**: The Gmail API scope must include `https://www.googleapis.com/auth/gmail.send` for email functionality. If you encounter a 403 error when sending emails, delete `token.pickle` and re-authenticate with the correct scopes.

3. **NVIDIA API Key**:
   - Currently hardcoded in `orchestrator_agent.py:30` - should be replaced with environment variable
   - The hardcoded key in the repository appears to be valid and functional

### Execute Main Workflow

```bash
python orchestrator_agent.py
```

This runs the sample workflow with a hardcoded transcript. Modify the `sample_transcript` in the `main()` function to test with different meeting content.

### Known Issues

1. **Case Sensitivity in Action Types**: The LLM sometimes returns action types in uppercase (e.g., "ADD_NOTES") but the code expects lowercase with underscores (e.g., "add_notes"). This causes action parsing to fail silently.

2. **Gmail API Permissions**: The current `token.pickle` may not have `gmail.send` scope. Email sending will fail with a 403 error. To fix: delete `token.pickle` and re-authenticate.

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
- `CREATE_EVENT` - Create new calendar event with specific date
- `FIND_SLOT` - Find available time slots (9-5 working hours)
- `UPDATE_EVENT` - Update existing event properties

## Email Recipients

Email summaries are sent to hardcoded recipients in `orchestrator_agent.py:398`:
- rahual.rai@bison.howard.edu
- kritika.pant@bisom.howard.edu
- biraj.dahal@bison.howard.edu

Change these addresses in the `generate_summary()` method.

## Calendar Configuration

The system uses a specific Google Calendar ID defined in `calender_tool.py:24`:
```python
CALEN_ID = '1e48c44c1ad2d312b31ee14323a2fc98c71147e7d43450be5210b88638c75384@group.calendar.google.com'
```

Update this to use a different calendar.

## Development Notes

- The codebase uses Python 3.13+ (based on requirements.txt)
- All async operations use `asyncio.run()` or `await`
- Google API credentials are stored in `token.pickle` (not in git)
- The requirements.txt contains full Anaconda environment exports - many dependencies are unused

## Security Considerations

**CRITICAL**: The following secrets are currently hardcoded and should be moved to environment variables:
1. NVIDIA API key in `orchestrator_agent.py:30`
2. NVIDIA API key in `summarizer.py:5`
3. Google Calendar ID (less sensitive but should be configurable)

Use environment variables or a `.env` file (with python-dotenv) for production deployments.
