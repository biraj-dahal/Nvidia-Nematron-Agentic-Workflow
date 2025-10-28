"""Calendar Agent - Handles scheduling and calendar operations."""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain.tools import Tool
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder


class CalendarAgent:
    """Agent responsible for calendar operations and scheduling."""
    
    def __init__(self, llm: ChatNVIDIA):
        """Initialize the Calendar Agent.
        
        Args:
            llm: Language model instance
        """
        self.llm = llm
        self.events: List[Dict] = []
        self.tools = self._create_tools()
        self.agent = self._create_agent()
    
    def _create_tools(self) -> List[Tool]:
        """Create tools for the calendar agent."""
        return [
            Tool(
                name="create_event",
                func=self.create_event,
                description="Create a new calendar event. Input should be a JSON string with 'title', 'start_time', 'end_time', and optional 'description'."
            ),
            Tool(
                name="list_events",
                func=self.list_events,
                description="List all calendar events. Optionally provide a date range."
            ),
            Tool(
                name="check_availability",
                func=self.check_availability,
                description="Check availability for a given time slot. Input should be a JSON string with 'start_time' and 'end_time'."
            ),
            Tool(
                name="delete_event",
                func=self.delete_event,
                description="Delete a calendar event by title."
            )
        ]
    
    def _create_agent(self) -> AgentExecutor:
        """Create the calendar agent executor."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a Calendar Agent responsible for managing schedules and events.
You have access to tools for creating, listing, checking availability, and deleting calendar events.
Always be precise with dates and times, and confirm actions with the user."""),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        agent = create_structured_chat_agent(self.llm, self.tools, prompt)
        return AgentExecutor(agent=agent, tools=self.tools, verbose=True)
    
    def create_event(self, event_data: str) -> str:
        """Create a new calendar event.
        
        Args:
            event_data: JSON string with event details
            
        Returns:
            Confirmation message
        """
        import json
        try:
            data = json.loads(event_data) if isinstance(event_data, str) else event_data
            event = {
                "id": len(self.events) + 1,
                "title": data.get("title", "Untitled Event"),
                "start_time": data.get("start_time"),
                "end_time": data.get("end_time"),
                "description": data.get("description", ""),
                "created_at": datetime.now().isoformat()
            }
            self.events.append(event)
            return f"Event '{event['title']}' created successfully for {event['start_time']} to {event['end_time']}"
        except Exception as e:
            return f"Error creating event: {str(e)}"
    
    def list_events(self, filter_criteria: str = "") -> str:
        """List all calendar events.
        
        Args:
            filter_criteria: Optional filter criteria
            
        Returns:
            List of events as a formatted string
        """
        if not self.events:
            return "No events found."
        
        events_str = "Calendar Events:\n"
        for event in self.events:
            events_str += f"- {event['title']}: {event['start_time']} to {event['end_time']}\n"
            if event['description']:
                events_str += f"  Description: {event['description']}\n"
        return events_str
    
    def check_availability(self, time_slot: str) -> str:
        """Check availability for a time slot.
        
        Args:
            time_slot: JSON string with start_time and end_time
            
        Returns:
            Availability status
        """
        import json
        try:
            data = json.loads(time_slot) if isinstance(time_slot, str) else time_slot
            start = data.get("start_time")
            end = data.get("end_time")
            
            # Simple conflict check
            conflicts = []
            for event in self.events:
                # This is a simplified check
                conflicts.append(event['title'])
            
            if conflicts:
                return f"Time slot has potential conflicts with: {', '.join(conflicts[:3])}"
            return f"Time slot from {start} to {end} is available."
        except Exception as e:
            return f"Error checking availability: {str(e)}"
    
    def delete_event(self, title: str) -> str:
        """Delete an event by title.
        
        Args:
            title: Title of the event to delete
            
        Returns:
            Confirmation message
        """
        initial_count = len(self.events)
        self.events = [e for e in self.events if e['title'] != title]
        
        if len(self.events) < initial_count:
            return f"Event '{title}' deleted successfully."
        return f"No event found with title '{title}'."
    
    def process_request(self, request: str) -> str:
        """Process a calendar-related request.
        
        Args:
            request: User request in natural language
            
        Returns:
            Agent's response
        """
        try:
            result = self.agent.invoke({"input": request})
            return result.get("output", "No response generated.")
        except Exception as e:
            return f"Error processing request: {str(e)}"
