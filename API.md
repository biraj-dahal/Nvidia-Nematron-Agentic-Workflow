# API Documentation

## MultiAgentWorkflow

Main entry point for the multi-agent system.

### Initialization

```python
from src.workflow import MultiAgentWorkflow

workflow = MultiAgentWorkflow(
    nvidia_api_key="your_api_key",
    model="nvidia/nemotron-nano-9b-instruct"
)
```

### Methods

#### `run(user_input: str) -> Dict[str, Any]`

Process user input through the workflow.

**Parameters:**
- `user_input` (str): User's natural language input

**Returns:**
- Dictionary containing:
  - `user_input`: Original input
  - `agent_used`: Agent that processed the request
  - `response`: Agent's response
  - `intent`: Classified intent
  - `error`: Error message if any

**Example:**
```python
result = workflow.run("Schedule a meeting tomorrow at 2 PM")
print(result['response'])
```

#### `get_status() -> Dict[str, Any]`

Get status of all agents in the system.

**Returns:**
- Dictionary with agent statistics

**Example:**
```python
status = workflow.get_status()
print(f"Calendar events: {status['calendar_agent']['events_count']}")
```

---

## Orchestrator

Central coordinator managing all agents.

### Initialization

```python
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from src.agents import Orchestrator

llm = ChatNVIDIA(api_key="your_key", model="nvidia/nemotron-nano-9b-instruct")
orchestrator = Orchestrator(llm)
```

### Methods

#### `process_input(user_input: str) -> Dict[str, Any]`

Process user input and route to appropriate agent.

**Returns:**
- Dictionary with user input, intent, agent used, and response

---

## CalendarAgent

Manages calendar operations and scheduling.

### Methods

#### `create_event(event_data: str) -> str`

Create a new calendar event.

**Parameters:**
- `event_data`: JSON string with event details (title, start_time, end_time, description)

**Example:**
```python
import json
event = {
    "title": "Team Meeting",
    "start_time": "2024-10-29 14:00",
    "end_time": "2024-10-29 15:00",
    "description": "Quarterly review"
}
response = calendar_agent.create_event(json.dumps(event))
```

#### `list_events(filter_criteria: str = "") -> str`

List all calendar events.

**Returns:**
- Formatted string of all events

#### `check_availability(time_slot: str) -> str`

Check availability for a time slot.

**Parameters:**
- `time_slot`: JSON string with start_time and end_time

#### `delete_event(title: str) -> str`

Delete an event by title.

---

## SummarizerAgent

Processes and summarizes text information.

### Methods

#### `summarize_text(text: str, max_length: Optional[int] = None) -> str`

Summarize a given text.

**Parameters:**
- `text`: Text to summarize
- `max_length`: Optional maximum length in words

**Example:**
```python
summary = summarizer.summarize_text(long_text, max_length=100)
```

#### `extract_key_points(text: str, num_points: int = 5) -> List[str]`

Extract key points from text.

**Parameters:**
- `text`: Text to analyze
- `num_points`: Number of key points to extract

**Returns:**
- List of key points

#### `summarize_conversation(messages: List[str]) -> str`

Summarize a conversation.

**Parameters:**
- `messages`: List of conversation messages

#### `summarize_meeting_notes(notes: str) -> Dict[str, Any]`

Create structured summary of meeting notes.

**Returns:**
- Dictionary with summary and structured information

---

## ArchivistAgent

Handles document storage and retrieval (RAG).

### Methods

#### `archive_document(content: str, metadata: Optional[Dict] = None) -> str`

Archive a document in the vector store.

**Parameters:**
- `content`: Document content
- `metadata`: Optional metadata dictionary

**Example:**
```python
archivist.archive_document(
    content="Company policy document...",
    metadata={"type": "policy", "date": "2024-10-28"}
)
```

#### `retrieve_documents(query: str, k: int = 3) -> List[Document]`

Retrieve relevant documents.

**Parameters:**
- `query`: Search query
- `k`: Number of documents to retrieve

#### `query_with_context(query: str, k: int = 3) -> str`

Query with RAG (retrieval-augmented generation).

**Parameters:**
- `query`: User question
- `k`: Number of context documents

**Returns:**
- Generated answer with context

**Example:**
```python
answer = archivist.query_with_context("What is our remote work policy?")
```

#### `semantic_search(query: str, k: int = 5) -> List[Dict]`

Perform semantic search.

**Returns:**
- List of search results with content and metadata

---

## ScribeService

Tool for note-taking and management.

### Methods

#### `take_note(content: str, tags: Optional[List[str]] = None) -> Dict`

Take a new note.

**Parameters:**
- `content`: Note content
- `tags`: Optional list of tags

**Returns:**
- Note object with id, content, timestamp, and tags

**Example:**
```python
note = scribe.take_note("Meeting reminder", tags=["important", "meeting"])
```

#### `get_notes(tag: Optional[str] = None) -> List[Dict]`

Retrieve notes, optionally filtered by tag.

**Parameters:**
- `tag`: Optional tag to filter by

#### `search_notes(query: str) -> List[Dict]`

Search notes by content.

**Parameters:**
- `query`: Search query string

**Example:**
```python
results = scribe.search_notes("budget")
```

#### `get_recent_notes(limit: int = 5) -> List[Dict]`

Get most recent notes.

**Parameters:**
- `limit`: Number of notes to retrieve

---

## Configuration

### Config Class

```python
from src.config import Config

# Validate configuration
Config.validate()

# Access configuration
api_key = Config.NVIDIA_API_KEY
model = Config.NEMOTRON_MODEL
```

### Environment Variables

- `NVIDIA_API_KEY`: NVIDIA API key (required)
- `NEMOTRON_MODEL`: Model name (default: nvidia/nemotron-nano-9b-instruct)
- `CHROMA_PERSIST_DIRECTORY`: Vector store directory (default: ./chroma_db)

---

## Error Handling

All methods return error messages as strings when exceptions occur. Always check for error indicators in responses:

```python
result = workflow.run("query")
if result.get('error'):
    print(f"Error occurred: {result['error']}")
else:
    print(result['response'])
```

---

## Best Practices

1. **Initialize once**: Create workflow instance once and reuse
2. **Error handling**: Always check for errors in responses
3. **API keys**: Store API keys securely in .env file
4. **Rate limiting**: Be mindful of API rate limits
5. **Context**: Use conversation history for better context
6. **Tags**: Use tags in notes for better organization
7. **Metadata**: Add metadata when archiving documents
