# Nvidia Nemotron Agentic Workflow

A sophisticated multi-agent system powered by NVIDIA's Nemotron-nano-9b-v2 model and LangGraph for intelligent task orchestration and execution.

## 🌟 Overview

This project implements a comprehensive agentic workflow where a central "Brain" (Orchestrator) manages a team of specialized agents and tools. Each agent operates as a node in a LangGraph workflow, enabling seamless collaboration and intelligent task routing.

## 🏗️ Architecture

### Central Orchestrator (The "Brain")
The Orchestrator serves as the central coordinator that:
- Classifies user intent using advanced NLP
- Routes requests to appropriate specialized agents
- Maintains conversation history
- Coordinates multi-agent interactions

### Specialized Agents

#### 1. **Calendar Agent** (The "Tool-User")
Handles all scheduling and calendar operations:
- Create, list, and delete events
- Check availability for time slots
- Manage appointments and meetings
- Natural language date/time understanding

#### 2. **Scribe Service** (The Tool)
A dedicated tool (not an agent) for note management:
- Take and store notes with timestamps
- Search notes by content or tags
- Retrieve recent notes
- Organize notes with tags

#### 3. **Summarizer Agent** (The "Note-Taker")
Processes and condenses information:
- Summarize long texts and documents
- Extract key points from content
- Summarize conversations and meetings
- Generate structured meeting summaries

#### 4. **Archivist Agent** (The "Agentic RAG")
Implements Retrieval-Augmented Generation (RAG):
- Store documents in vector database (ChromaDB)
- Semantic search across archived content
- Answer questions using retrieved context
- Archive and retrieve information intelligently

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- NVIDIA API key for Nemotron model access

### Installation

1. Clone the repository:
```bash
git clone https://github.com/biraj-dahal/Nvidia-Nematron-Agentic-Workflow.git
cd Nvidia-Nematron-Agentic-Workflow
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env and add your NVIDIA_API_KEY
```

### Configuration

Edit the `.env` file with your credentials:

```env
NVIDIA_API_KEY=your_nvidia_api_key_here
NEMOTRON_MODEL=nvidia/nemotron-nano-9b-instruct
CHROMA_PERSIST_DIRECTORY=./chroma_db
```

## 💻 Usage

### Interactive Mode

Run the main application for an interactive session:

```bash
python main.py
```

This starts an interactive console where you can:
- Ask questions and make requests
- See which agent handles each request
- Check system status
- View agent statistics

### Example Commands

```
# Calendar operations
You: Schedule a meeting tomorrow at 3 PM

# Note-taking
You: Take note: Review project proposal by Friday

# Summarization
You: Summarize this text: [long text here]

# Document archival
You: Archive this document: [document content]

# Search archived content
You: Search for information about remote work policy

# System status
You: status
```

### Programmatic Usage

```python
from src.workflow import MultiAgentWorkflow

# Initialize workflow
workflow = MultiAgentWorkflow(
    nvidia_api_key="your_api_key",
    model="nvidia/nemotron-nano-9b-instruct"
)

# Process a request
result = workflow.run("Create a meeting for tomorrow at 2 PM")
print(result['response'])

# Check agent status
status = workflow.get_status()
print(status)
```

### Running Examples

```bash
python examples/basic_usage.py
```

## 📁 Project Structure

```
Nvidia-Nematron-Agentic-Workflow/
├── src/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── calendar_agent.py      # Calendar management
│   │   ├── summarizer_agent.py    # Text summarization
│   │   ├── archivist_agent.py     # RAG and document storage
│   │   └── orchestrator.py        # Central coordinator
│   ├── tools/
│   │   ├── __init__.py
│   │   └── scribe.py              # Note-taking service
│   ├── config/
│   │   └── __init__.py            # Configuration management
│   └── workflow.py                # LangGraph workflow
├── examples/
│   └── basic_usage.py             # Example usage
├── main.py                        # Interactive CLI
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment template
├── .gitignore                     # Git ignore rules
└── README.md                      # This file
```

## 🧠 How It Works

### LangGraph Workflow

The system uses LangGraph to create a stateful workflow graph:

1. **Intent Classification**: User input is analyzed to determine intent
2. **Agent Routing**: Request is routed to the appropriate agent
3. **Agent Processing**: Specialized agent handles the request
4. **Response Finalization**: Result is formatted and returned

```
User Input → Classify Intent → Route to Agent → Process → Return Response
                    ↓
            [Calendar | Summarizer | Archivist | Scribe]
```

### State Management

Each workflow maintains state including:
- User input
- Classified intent
- Agent used
- Agent response
- Conversation history
- Error tracking

## 🔧 Advanced Features

### RAG with ChromaDB

The Archivist Agent uses ChromaDB for vector storage:
- Semantic search capabilities
- Document chunking and embedding
- Persistent storage
- Context-aware retrieval

### Multi-Agent Coordination

The Orchestrator can:
- Route requests to multiple agents
- Maintain conversation context
- Track agent usage statistics
- Generate conversation summaries

### Extensibility

Easy to extend with new agents:
1. Create new agent class
2. Add to Orchestrator
3. Update workflow routing
4. Implement agent-specific logic

## 📊 Example Outputs

### Calendar Agent
```
🤖 CALENDAR Agent:
Event 'Team Meeting' created successfully for 2024-10-29 14:00 to 2024-10-29 15:00
```

### Summarizer Agent
```
🤖 SUMMARIZER Agent:
Key Points:
- Revenue growth exceeded expectations by 15%
- New digital marketing campaign launched
- Platform upgrade completed successfully
- Customer satisfaction improved by 8 points
- Action items identified for next quarter
```

### Archivist Agent
```
🤖 ARCHIVIST Agent:
Successfully archived document with 3 chunks.
```

### Scribe Service
```
🤖 SCRIBE Agent:
Note taken: Need to review the Q4 budget proposals
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

- NVIDIA for the Nemotron model
- LangChain and LangGraph teams
- ChromaDB for vector storage capabilities

## 📞 Support

For issues, questions, or contributions, please open an issue on GitHub.

---

Built with ❤️ using NVIDIA Nemotron and LangGraph
