"""Orchestrator - The central Brain that manages all agents."""

from typing import Dict, List, Optional, Any
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain.prompts import ChatPromptTemplate
from .calendar_agent import CalendarAgent
from .summarizer_agent import SummarizerAgent
from .archivist_agent import ArchivistAgent
from ..tools.scribe import ScribeService


class Orchestrator:
    """Central coordinator that manages all specialized agents and tools."""
    
    def __init__(self, llm: ChatNVIDIA):
        """Initialize the Orchestrator with all agents and tools.
        
        Args:
            llm: Language model instance
        """
        self.llm = llm
        
        # Initialize all agents
        self.calendar_agent = CalendarAgent(llm)
        self.summarizer_agent = SummarizerAgent(llm)
        self.archivist_agent = ArchivistAgent(llm)
        
        # Initialize tools
        self.scribe = ScribeService()
        
        # Track conversation history
        self.conversation_history: List[Dict] = []
    
    def _classify_intent(self, user_input: str) -> Dict[str, Any]:
        """Classify user intent to route to appropriate agent.
        
        Args:
            user_input: User's input message
            
        Returns:
            Classification result with agent and action
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an intent classifier for a multi-agent system. 
Analyze the user input and determine which agent should handle it:

1. CALENDAR - for scheduling, events, availability, appointments
2. SUMMARIZER - for summarizing text, extracting key points, meeting notes
3. ARCHIVIST - for storing documents, retrieving information, semantic search, RAG queries
4. SCRIBE - for taking notes, managing notes, searching notes

Respond with ONLY the agent name (CALENDAR, SUMMARIZER, ARCHIVIST, or SCRIBE) and a brief action description.
Format: AGENT_NAME | action_description"""),
            ("user", f"User input: {user_input}")
        ])
        
        try:
            formatted = prompt.format_messages()
            response = self.llm.invoke(formatted)
            content = response.content.strip()
            
            # Parse response
            if "|" in content:
                agent_name, action = content.split("|", 1)
                agent_name = agent_name.strip()
                action = action.strip()
            else:
                agent_name = content.split()[0] if content else "UNKNOWN"
                action = "general request"
            
            return {
                "agent": agent_name.upper(),
                "action": action,
                "raw_response": content
            }
        except Exception as e:
            return {
                "agent": "UNKNOWN",
                "action": "error",
                "error": str(e)
            }
    
    def _route_to_agent(self, intent: Dict, user_input: str) -> str:
        """Route the request to the appropriate agent.
        
        Args:
            intent: Classified intent
            user_input: Original user input
            
        Returns:
            Agent's response
        """
        agent_name = intent.get("agent", "UNKNOWN")
        
        try:
            if agent_name == "CALENDAR":
                return self.calendar_agent.process_request(user_input)
            
            elif agent_name == "SUMMARIZER":
                # For summarizer, we need to extract the content to summarize
                return self.summarizer_agent.process_request(user_input, user_input)
            
            elif agent_name == "ARCHIVIST":
                return self.archivist_agent.process_request(user_input)
            
            elif agent_name == "SCRIBE":
                # Extract action for scribe
                if "take note" in user_input.lower() or "create note" in user_input.lower():
                    # Extract note content (simple extraction)
                    content = user_input.split("note")[-1].strip(":").strip()
                    note = self.scribe.take_note(content)
                    return f"Note taken: {note['content']}"
                elif "search" in user_input.lower():
                    query = user_input.split("search")[-1].strip()
                    results = self.scribe.search_notes(query)
                    if results:
                        return f"Found {len(results)} notes:\n" + "\n".join([f"- {n['content']}" for n in results[:5]])
                    return "No matching notes found."
                elif "recent" in user_input.lower():
                    notes = self.scribe.get_recent_notes()
                    if notes:
                        return f"Recent notes:\n" + "\n".join([f"- {n['content']}" for n in notes])
                    return "No notes available."
                else:
                    return "Please specify what you'd like to do with notes (take, search, or view recent)."
            
            else:
                return f"I'm not sure how to handle that request. Could you please rephrase?"
        
        except Exception as e:
            return f"Error processing request: {str(e)}"
    
    def process_input(self, user_input: str) -> Dict[str, Any]:
        """Process user input through the orchestration system.
        
        Args:
            user_input: User's input message
            
        Returns:
            Response with agent used and output
        """
        # Classify intent
        intent = self._classify_intent(user_input)
        
        # Route to appropriate agent
        response = self._route_to_agent(intent, user_input)
        
        # Store in conversation history
        conversation_entry = {
            "user_input": user_input,
            "intent": intent,
            "agent_used": intent.get("agent"),
            "response": response
        }
        self.conversation_history.append(conversation_entry)
        
        return conversation_entry
    
    def get_conversation_summary(self) -> str:
        """Get a summary of the conversation history.
        
        Returns:
            Summary of all interactions
        """
        if not self.conversation_history:
            return "No conversation history available."
        
        # Use summarizer to create conversation summary
        messages = [
            f"User: {entry['user_input']}\nAgent ({entry['agent_used']}): {entry['response']}"
            for entry in self.conversation_history
        ]
        
        return self.summarizer_agent.summarize_conversation(messages)
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents.
        
        Returns:
            Status information for all agents
        """
        return {
            "calendar_agent": {
                "events_count": len(self.calendar_agent.events)
            },
            "summarizer_agent": {
                "summaries_created": len(self.summarizer_agent.summaries)
            },
            "archivist_agent": {
                "status": "operational",
                "vector_store": "initialized"
            },
            "scribe_service": {
                "notes_count": len(self.scribe.notes)
            },
            "conversation_history": len(self.conversation_history)
        }
