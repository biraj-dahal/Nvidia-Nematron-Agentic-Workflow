# Multi-Agent System Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    User Input / Query                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  ORCHESTRATOR (Brain)                        │
│  - Intent Classification                                     │
│  - Request Routing                                           │
│  - Conversation Management                                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┬────────────┐
        │              │               │            │
        ▼              ▼               ▼            ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   CALENDAR   │ │  SUMMARIZER  │ │  ARCHIVIST   │ │    SCRIBE    │
│    AGENT     │ │    AGENT     │ │    AGENT     │ │   SERVICE    │
├──────────────┤ ├──────────────┤ ├──────────────┤ ├──────────────┤
│ - Create     │ │ - Summarize  │ │ - RAG        │ │ - Take notes │
│   events     │ │   text       │ │ - Vector DB  │ │ - Search     │
│ - Check      │ │ - Extract    │ │ - Semantic   │ │ - Retrieve   │
│   availability│ │   key points │ │   search     │ │ - Tags       │
│ - List       │ │ - Meeting    │ │ - Archive    │ │              │
│   events     │ │   notes      │ │   docs       │ │              │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
        │              │               │            │
        └──────────────┴───────────────┴────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  LangGraph State Management                  │
│  - Workflow orchestration                                    │
│  - State tracking                                            │
│  - Error handling                                            │
└─────────────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│               Response to User                               │
└─────────────────────────────────────────────────────────────┘
```

## LangGraph Workflow

```
[Start] → [Classify Intent] → [Route Decision]
                                      │
                    ┌─────────────────┼─────────────────┬────────────┐
                    ▼                 ▼                 ▼            ▼
              [Calendar]        [Summarizer]      [Archivist]  [Scribe]
                    │                 │                 │            │
                    └─────────────────┴─────────────────┴────────────┘
                                      │
                                      ▼
                              [Finalize Response]
                                      │
                                      ▼
                                   [End]
```

## Component Details

### Orchestrator (Brain)
- **Purpose**: Central coordinator for all agents
- **Responsibilities**:
  - Classify user intent using Nemotron model
  - Route requests to appropriate agents
  - Maintain conversation history
  - Coordinate multi-agent interactions

### Calendar Agent
- **Type**: Specialized Agent
- **Tools**: Event creation, availability checking, event management
- **Model**: Uses Nemotron for natural language understanding

### Summarizer Agent
- **Type**: Specialized Agent
- **Capabilities**: Text summarization, key point extraction, meeting notes
- **Model**: Uses Nemotron for content generation

### Archivist Agent
- **Type**: Agentic RAG
- **Components**:
  - ChromaDB for vector storage
  - HuggingFace embeddings
  - Semantic search capabilities
  - Context-aware retrieval

### Scribe Service
- **Type**: Tool (not an agent)
- **Storage**: JSON-based note storage
- **Features**: Note taking, searching, tagging, retrieval

## Technology Stack

- **LLM**: NVIDIA Nemotron-nano-9b-v2
- **Framework**: LangGraph + LangChain
- **Vector Store**: ChromaDB
- **Embeddings**: Sentence Transformers (all-MiniLM-L6-v2)
- **Language**: Python 3.8+

## Data Flow

1. **User Input** → Orchestrator
2. **Intent Classification** → Determine agent
3. **Agent Selection** → Route to specific agent
4. **Agent Processing** → Execute specialized task
5. **Response Generation** → Format and return
6. **History Update** → Store conversation context
