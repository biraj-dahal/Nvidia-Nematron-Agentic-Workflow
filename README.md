# NVIDIA Nemotron Agentic Workflow Orchestrator

**Hackathon Project Powered by NVIDIA Nemotron**

An intelligent AI-powered meeting assistant that transcribes audio, analyzes conversations, and automatically orchestrates calendar events and email notifications using a sophisticated multi-agent workflow.

## Key Features

🤖 **9-Agent Orchestration**
- Analyze Transcript
- Research & Entity Extraction
- Fetch Calendar Context
- Find Related Meetings
- Plan Actions
- Decision Analysis
- Risk Assessment
- Execute Actions
- Generate Summary

📊 **Interactive Workflow Visualization**
- Real-time node graph showing agent activation
- Live Nemotron API call tracking
- Execution timeline
- Agent details and reasoning display

🎤 **Voice Processing**
- Audio recording and transcription via NVIDIA Parakeet ASR
- Automatic calendar event scheduling
- Email notifications to attendees

⚡ **Powered by NVIDIA Nemotron**
- llama-3.3-nemotron-super-49b-v1.5 backbone
- Intelligent decision making and risk assessment
- Real-time API instrumentation

## Quick Start

### Prerequisites
- Python 3.9+
- FFmpeg installed
- Google Calendar API credentials (OAuth 2.0)
- NVIDIA API Key for Nemotron and Parakeet services

### Installation

1. **Clone and setup**
   ```bash
   cd Nvidia-Nematron-Agentic-Workflow
   pip install -r requirements.txt
   ```

2. **Set NVIDIA API Key**
   ```bash
   export API_KEY="your_nvidia_api_key_here"
   ```

3. **Configure Google Calendar**
   - Place OAuth credentials in `credentials.json`
   - Update attendee mappings in `attendee_mapping.json`

4. **Start the server**
   ```bash
   python server.py
   ```
   Server runs at `http://localhost:3000`

## Usage

### Recording a Meeting
1. Visit `http://localhost:3000` in your browser
2. Click **"Start Recording"** to capture audio
3. Speak or play meeting audio
4. Click **"End Recording"** when done

### Viewing Workflow Visualization
1. Click **"Watch Workflow Visualization"** button
2. See real-time agent activation in interactive graph
3. Monitor Nemotron API calls and metrics
4. Track execution timeline

### Results
- **Meeting Summary**: AI-generated analysis with key topics
- **Calendar Events**: Auto-created for scheduled items
- **Action Items**: Tracked with assignees and deadlines
- **Email Notifications**: Sent to all attendees

## Architecture

```
User Audio → ASR Transcription → Multi-Agent Orchestration → Outputs
              (Parakeet)        (9 Specialized Agents)     (Calendar/Email)
                                      ↓
                           NVIDIA Nemotron Analysis
```

**Technology Stack**
- Backend: Python, Flask, LangGraph
- Frontend: HTML/CSS/JS with vis.js
- ASR: NVIDIA Parakeet (gRPC)
- LLM: NVIDIA Nemotron Super 49B
- Calendar: Google Calendar API v3
- AI Framework: LangGraph for workflow orchestration

## Project Structure

```
├── server.py                 # Flask backend
├── orchestrator_agent.py     # Multi-agent workflow
├── index.html               # Main UI
├── workflow_viewer.html      # Workflow visualization
├── styles.css               # Styling
├── script.js                # Frontend logic
├── attendee_mapping.json     # User configuration
└── README.md               # This file
```

## How It Works

1. **Transcription**: Audio is converted to 16kHz mono WAV and transcribed using NVIDIA Parakeet ASR
2. **Analysis**: Nemotron analyzes the transcript through 9 specialized agents
3. **Decision Making**: Agents evaluate options, assess risks, and recommend actions
4. **Execution**: Calendar events are created and emails sent to attendees
5. **Visualization**: Interactive graph shows real-time agent workflow progression

## Demo Features

- **Auto-execute Toggle**: Run actions automatically or require approval
- **Live Metrics**: See Nemotron API latency and response sizes
- **Structured Output**: JSON-based reasoning from each agent
- **Email Summaries**: Formatted HTML emails with action items and next steps

## Screenshots

<!-- Add screenshot of main interface -->
`[Main Interface Screenshot]` - Audio recording and results display

<!-- Add screenshot of workflow visualization -->
`[Workflow Visualization Screenshot]` - Interactive agent orchestration graph

<!-- Add screenshot of workflow results -->
`[Results Display Screenshot]` - Meeting summary and action items

## Notes

- Requires valid NVIDIA and Google API credentials
- Transcription quality depends on audio input
- Calendar events created in user's default timezone (EST/EDT)
- Attendee names matched with fuzzy matching against configured users

## Acknowledgments

Built for the NVIDIA Hackathon showcasing:
- Multi-agent AI workflow orchestration
- LangGraph-based state management
- NVIDIA Nemotron for intelligent decision-making
- Production-ready agentic architecture
