"""
Meeting Orchestrator Agent
Coordinates transcription, calendar management, and intelligent note-taking
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Sequence, Optional, List, Dict
from enum import Enum

from openai import OpenAI
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from typing import List, Dict, Optional, Any
# Import your existing calendar tool
from calender_tool import CalendarAgentTool, CalendarEvent
from email_tool import GmailAgentTool

_LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Initialize NVIDIA Nemotron client
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key="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"
)


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
    reasoning: str = ""


class OrchestratorState(BaseModel):
    """State for the orchestrator agent"""
    audio_transcript: str
    calendar_events: List[CalendarEvent] = []
    related_past_meetings: List[Dict[str, Any]] = []
    planned_actions: List[MeetingAction] = []
    execution_results: List[str] = []
    messages: Annotated[Sequence[Any], add_messages] = []


class MeetingOrchestrator:
    """Main orchestrator that coordinates all agents and tools"""
    
    def __init__(self):
        self.calendar_tool = CalendarAgentTool()
        self.client = client
        self.email_tool = GmailAgentTool()
        
    def _call_nemotron(self, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        """Helper to call Nemotron with proper formatting"""
        # Add JSON formatting instructions to system prompt if needed
        if json_mode:
            system_prompt += "\n\nIMPORTANT: You must respond with ONLY valid JSON. No explanatory text before or after. Start with { or [ and end with } or ]."
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        completion = self.client.chat.completions.create(
            model="nvidia/llama-3.3-nemotron-super-49b-v1.5",
            messages=messages,
            temperature=0.2,
            top_p=0.95,
            max_tokens=4096,
            stream=False
        )
        
        return completion.choices[0].message.content
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from text that might contain markdown or other formatting"""
        # Try to find JSON in code blocks
        import re
        
        # Look for JSON in markdown code blocks
        json_block_match = re.search(r'```json\s*(\{.*?\}|\[.*?\])\s*```', text, re.DOTALL)
        if json_block_match:
            return json_block_match.group(1)
        
        # Look for any code block
        code_block_match = re.search(r'```\s*(\{.*?\}|\[.*?\])\s*```', text, re.DOTALL)
        if code_block_match:
            return code_block_match.group(1)
        
        # Look for JSON object or array
        json_match = re.search(r'(\{.*?\}|\[.*?\])', text, re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        return text
    
    async def analyze_transcript(self, state: OrchestratorState, config: RunnableConfig):
        """Analyze the transcript to understand meeting context"""
        _LOGGER.info("Analyzing transcript for meeting context...")
        
        system_prompt = """You are an expert meeting analyst. Extract key information from meeting transcripts.

Respond ONLY with valid JSON in exactly this format (no other text):
{
    "meeting_title": "string",
    "is_past_meeting": true,
    "mentioned_dates": ["2025-10-30"],
    "participants": ["John", "Sarah"],
    "key_topics": ["Q4 roadmap", "budget"],
    "action_items": ["John: prepare specs", "Sarah: budget analysis"],
    "summary": "Brief summary of the meeting"
}"""
        
        user_prompt = f"Analyze this meeting transcript and return ONLY JSON:\n\n{state.audio_transcript}"
        
        response = self._call_nemotron(system_prompt, user_prompt, json_mode=True)
        _LOGGER.info(f"Raw response from Nemotron:\n{response}\n")
        
        try:
            # Extract JSON from response
            json_str = self._extract_json(response)
            _LOGGER.info(f"Extracted JSON: {json_str[:200]}...")
            analysis = json.loads(json_str)
            
            # Update state directly
            state.messages.append({
                "role": "assistant",
                "content": f"Meeting Analysis: {json.dumps(analysis, indent=2)}"
            })
            # Don't return analysis, just update messages
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
            return state
    
    async def fetch_calendar_context(self, state: OrchestratorState, config: RunnableConfig):
        """Fetch relevant calendar events"""
        _LOGGER.info("Fetching calendar events...")
        
        # Get events from past 30 days and next 30 days
        events = self.calendar_tool.fetch_events(days_ahead=30, days_back=30, max_results=50)
        state.calendar_events = events
        
        _LOGGER.info(f"Found {len(events)} calendar events")
        return state
    
    async def find_related_meetings(self, state: OrchestratorState, config: RunnableConfig):
        """Use Nemotron to find related past meetings"""
        _LOGGER.info("Finding related past meetings...")
        
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
        
        response = self._call_nemotron(system_prompt, user_prompt, json_mode=True)
        _LOGGER.info(f"Raw related meetings response:\n{response}\n")
        
        try:
            json_str = self._extract_json(response)
            _LOGGER.info(f"Related meetings JSON: {json_str[:200]}...")
            related = json.loads(json_str)
            
            # Ensure it's a list
            if not isinstance(related, list):
                related = []
            
            # Update state directly
            state.related_past_meetings = related
            _LOGGER.info(f"Found {len(related)} related meetings")
            return state
        except (json.JSONDecodeError, Exception) as e:
            _LOGGER.error(f"Failed to parse related meetings: {e}")
            _LOGGER.error(f"Raw response: {response[:500]}")
            state.related_past_meetings = []
            return state
    
    async def plan_actions(self, state: OrchestratorState, config: RunnableConfig):
        """Decide what actions to take based on the analysis"""
        _LOGGER.info("Planning actions...")
        
        system_prompt = """You are a meeting action planner. Based on transcript and calendar, decide actions.

Actions available:
- ADD_NOTES: Add notes to existing event
- CREATE_EVENT: Create new event with specific date
- FIND_SLOT: Find available time (9-5) for new event
- UPDATE_EVENT: Update existing event

Return ONLY JSON array (no other text):
[
    {
        "action_type": "ADD_NOTES",
        "calendar_event_id": "event_id_here",
        "notes": "Meeting notes to add",
        "reasoning": "Why this action"
    }
]

If no actions needed, return empty array: []"""
        
        context = {
            "transcript": state.audio_transcript[:800],
            "related_meetings": state.related_past_meetings[:3],
            "calendar_events": [
                {"id": e.id, "title": e.summary, "start": e.start} 
                for e in state.calendar_events[:5]
            ]
        }
        
        user_prompt = f"""Context:
{json.dumps(context, indent=2)}

What actions should be taken? Return ONLY JSON."""
        
        response = self._call_nemotron(system_prompt, user_prompt, json_mode=True)
        _LOGGER.info(f"Raw actions response:\n{response}\n")
        
        try:
            json_str = self._extract_json(response)
            _LOGGER.info(f"Actions JSON: {json_str[:200]}")
            actions_data = json.loads(json_str)
            
            # Ensure it's a list
            if not isinstance(actions_data, list):
                actions_data = []
            
            actions = [MeetingAction(**action) for action in actions_data]
            state.planned_actions = actions
            _LOGGER.info(f"Planned {len(actions)} actions")
            return state
        except (json.JSONDecodeError, Exception) as e:
            _LOGGER.error(f"Failed to parse actions: {e}")
            _LOGGER.error(f"Raw response: {response[:500]}")
            state.planned_actions = []
            return state
    
    async def execute_actions(self, state: OrchestratorState, config: RunnableConfig):
        """Execute the planned actions"""
        _LOGGER.info("Executing planned actions...")
        
        results = []
        
        for action in state.planned_actions:
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
                        result = f"Found {len(slots)} available slots:\n"
                        for slot in slots:
                            result += f"  - {slot.start} ({slot.duration_minutes} min)\n"
                        results.append(result)
                    else:
                        results.append("No available slots found in the next 14 days")
                
                elif action.action_type == ActionType.ADD_NOTES:
                    result = self.calendar_tool.add_notes_to_event(
                        action.calendar_event_id, action.notes
                    )
                    results.append(result)
                
                elif action.action_type == ActionType.CREATE_EVENT:
                    if action.event_date:
                        start_time = f"{action.event_date}T09:00:00Z"
                        end_time = f"{action.event_date}T10:00:00Z"
                    else:
                        # fallback: first available slot
                        slot = self.calendar_tool.find_available_slots(
                            duration_minutes=action.duration_minutes,
                            days_ahead=14,
                            max_slots=1
                        )[0]
                        start_time, end_time = slot.start, slot.end

                    event_id = self.calendar_tool.create_event(
                        title=action.event_title or "New Meeting",
                        start_time=start_time,
                        end_time=end_time,
                        description=action.notes or ""
                    )
                    result = f"Created new event '{action.event_title}' on {start_time} (ID: {event_id})"
                    results.append(result)
                elif action.action_type == ActionType.UPDATE_EVENT:
                    event_id = action.calendar_event_id
                    updates = {"description": action.notes or "Updated notes"}
                    self.calendar_tool.update_event(event_id, updates)
                    result = f"Updated event {event_id} with new notes."
                    results.append(result)
                
            except Exception as e:
                error_msg = f"Error executing {action.action_type}: {str(e)}"
                _LOGGER.error(error_msg)
                results.append(error_msg)
        
        state.execution_results = results
        return state
    
    async def generate_summary(self, state: OrchestratorState, config: RunnableConfig):
        """Generate a final summary of what was done"""
        _LOGGER.info("Generating final summary...")
        
        system_prompt = """You are a meeting assistant. Create a concise summary of what actions 
were taken based on the meeting transcript. Be specific and actionable."""
        
        context = {
            "transcript_preview": state.audio_transcript[:500],
            "actions_taken": [
                {
                    "action": action.action_type,
                    "reasoning": action.reasoning
                }
                for action in state.planned_actions
            ],
            "results": state.execution_results
        }
        
        user_prompt = f"""Generate a summary of the meeting and actions taken:

{json.dumps(context, indent=2)}"""
        
        summary = self._call_nemotron(system_prompt, user_prompt)
        self.email_tool.send_email(
        to_addresses=["rahual.rai@bison.howard.edu", "kritika.pant@bisom.howard.edu", "biraj.dahal@bison.howard.edu"],
        subject="AI Meeting Summary: " + datetime.now().strftime("%Y-%m-%d"),
        body=summary
        )
        _LOGGER.info("Summary email sent successfully.")
        
        state.messages.append({
            "role": "assistant",
            "content": f"Summary:\n{summary}"
        })
        
        return state


# Build the LangGraph workflow
def create_orchestrator_graph():
    """Create the orchestrator workflow graph"""
    
    orchestrator = MeetingOrchestrator()
    workflow = StateGraph(OrchestratorState)
    
    # Add nodes
    workflow.add_node("analyze_transcript", orchestrator.analyze_transcript)
    workflow.add_node("fetch_calendar_context", orchestrator.fetch_calendar_context)
    workflow.add_node("find_related_meetings", orchestrator.find_related_meetings)
    workflow.add_node("plan_actions", orchestrator.plan_actions)
    workflow.add_node("execute_actions", orchestrator.execute_actions)
    workflow.add_node("generate_summary", orchestrator.generate_summary)
    
    # Define the flow
    workflow.add_edge(START, "analyze_transcript")
    workflow.add_edge("analyze_transcript", "fetch_calendar_context")
    workflow.add_edge("fetch_calendar_context", "find_related_meetings")
    workflow.add_edge("find_related_meetings", "plan_actions")
    workflow.add_edge("plan_actions", "execute_actions")
    workflow.add_edge("execute_actions", "generate_summary")
    workflow.add_edge("generate_summary", END)
    
    return workflow.compile()


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
    
    # Print results
    print("\n" + "="*80)
    print("ORCHESTRATOR RESULTS")
    print("="*80)
    
    print(f"\nFound {len(result['calendar_events'])} calendar events")
    print(f"Identified {len(result['related_past_meetings'])} related meetings")
    print(f"Planned {len(result['planned_actions'])} actions")
    
    print("\n--- Planned Actions ---")
    for action in result['planned_actions']:
        print(f"\n{action.action_type}:")
        print(f"  Reasoning: {action.reasoning}")
        if action.event_title:
            print(f"  Event: {action.event_title}")
    
    print("\n--- Execution Results ---")
    for result_msg in result['execution_results']:
        print(f"\n{result_msg}")
    
    print("\n--- Final Summary ---")
    if result.get('messages'):
        last_message = result['messages'][-1]
        # Handle both dict and AIMessage object
        if isinstance(last_message, dict):
            print(last_message.get('content', 'No summary available'))
        else:
            # It's an AIMessage object
            print(getattr(last_message, 'content', 'No summary available'))
    
    print("\n" + "="*80)


if __name__ == "__main__":
    asyncio.run(main())