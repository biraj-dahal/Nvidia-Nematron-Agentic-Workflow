"""LangGraph workflow for the multi-agent system."""

from typing import TypedDict, Annotated, List, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from .agents.orchestrator import Orchestrator


class AgentState(TypedDict):
    """State for the agent workflow."""
    user_input: str
    intent: Dict[str, Any]
    agent_response: str
    agent_used: str
    conversation_history: List[Dict]
    error: str


class MultiAgentWorkflow:
    """LangGraph workflow for managing multi-agent interactions."""
    
    def __init__(self, nvidia_api_key: str, model: str = "nvidia/nemotron-nano-9b-instruct"):
        """Initialize the workflow.
        
        Args:
            nvidia_api_key: NVIDIA API key
            model: Model name to use
        """
        # Initialize LLM
        self.llm = ChatNVIDIA(
            api_key=nvidia_api_key,
            model=model
        )
        
        # Initialize orchestrator
        self.orchestrator = Orchestrator(self.llm)
        
        # Build workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow.
        
        Returns:
            Compiled workflow graph
        """
        # Create the graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("classify_intent", self._classify_intent_node)
        workflow.add_node("route_to_calendar", self._route_to_calendar)
        workflow.add_node("route_to_summarizer", self._route_to_summarizer)
        workflow.add_node("route_to_archivist", self._route_to_archivist)
        workflow.add_node("route_to_scribe", self._route_to_scribe)
        workflow.add_node("finalize", self._finalize_node)
        
        # Set entry point
        workflow.set_entry_point("classify_intent")
        
        # Add conditional edges for routing
        workflow.add_conditional_edges(
            "classify_intent",
            self._route_decision,
            {
                "calendar": "route_to_calendar",
                "summarizer": "route_to_summarizer",
                "archivist": "route_to_archivist",
                "scribe": "route_to_scribe",
                "unknown": "finalize"
            }
        )
        
        # All routes lead to finalize
        workflow.add_edge("route_to_calendar", "finalize")
        workflow.add_edge("route_to_summarizer", "finalize")
        workflow.add_edge("route_to_archivist", "finalize")
        workflow.add_edge("route_to_scribe", "finalize")
        
        # Finalize leads to end
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    def _classify_intent_node(self, state: AgentState) -> AgentState:
        """Classify the user's intent.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with intent
        """
        try:
            user_input = state.get("user_input", "")
            result = self.orchestrator.process_input(user_input)
            
            state["intent"] = result.get("intent", {})
            state["agent_used"] = result.get("agent_used", "UNKNOWN")
        except Exception as e:
            state["error"] = str(e)
            state["intent"] = {"agent": "UNKNOWN", "action": "error"}
        
        return state
    
    def _route_decision(self, state: AgentState) -> str:
        """Decide which agent to route to.
        
        Args:
            state: Current workflow state
            
        Returns:
            Agent route name
        """
        agent = state.get("intent", {}).get("agent", "UNKNOWN")
        
        if agent == "CALENDAR":
            return "calendar"
        elif agent == "SUMMARIZER":
            return "summarizer"
        elif agent == "ARCHIVIST":
            return "archivist"
        elif agent == "SCRIBE":
            return "scribe"
        else:
            return "unknown"
    
    def _route_to_calendar(self, state: AgentState) -> AgentState:
        """Route to calendar agent.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with response
        """
        try:
            response = self.orchestrator.calendar_agent.process_request(
                state["user_input"]
            )
            state["agent_response"] = response
        except Exception as e:
            state["agent_response"] = f"Calendar agent error: {str(e)}"
        
        return state
    
    def _route_to_summarizer(self, state: AgentState) -> AgentState:
        """Route to summarizer agent.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with response
        """
        try:
            response = self.orchestrator.summarizer_agent.process_request(
                state["user_input"],
                state["user_input"]
            )
            state["agent_response"] = response
        except Exception as e:
            state["agent_response"] = f"Summarizer agent error: {str(e)}"
        
        return state
    
    def _route_to_archivist(self, state: AgentState) -> AgentState:
        """Route to archivist agent.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with response
        """
        try:
            response = self.orchestrator.archivist_agent.process_request(
                state["user_input"]
            )
            state["agent_response"] = response
        except Exception as e:
            state["agent_response"] = f"Archivist agent error: {str(e)}"
        
        return state
    
    def _route_to_scribe(self, state: AgentState) -> AgentState:
        """Route to scribe service.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with response
        """
        try:
            user_input = state["user_input"]
            
            if "take note" in user_input.lower():
                content = user_input.split("note")[-1].strip(":").strip()
                note = self.orchestrator.scribe.take_note(content)
                response = f"Note taken: {note['content']}"
            elif "search" in user_input.lower():
                query = user_input.split("search")[-1].strip()
                results = self.orchestrator.scribe.search_notes(query)
                if results:
                    response = f"Found {len(results)} notes:\n" + "\n".join([
                        f"- {n['content']}" for n in results[:5]
                    ])
                else:
                    response = "No matching notes found."
            else:
                notes = self.orchestrator.scribe.get_recent_notes()
                if notes:
                    response = "Recent notes:\n" + "\n".join([
                        f"- {n['content']}" for n in notes
                    ])
                else:
                    response = "No notes available."
            
            state["agent_response"] = response
        except Exception as e:
            state["agent_response"] = f"Scribe service error: {str(e)}"
        
        return state
    
    def _finalize_node(self, state: AgentState) -> AgentState:
        """Finalize the response.
        
        Args:
            state: Current workflow state
            
        Returns:
            Final state
        """
        if not state.get("agent_response"):
            state["agent_response"] = "I'm not sure how to help with that. Could you please rephrase?"
        
        return state
    
    def run(self, user_input: str) -> Dict[str, Any]:
        """Run the workflow with user input.
        
        Args:
            user_input: User's input message
            
        Returns:
            Workflow result
        """
        initial_state = {
            "user_input": user_input,
            "intent": {},
            "agent_response": "",
            "agent_used": "",
            "conversation_history": [],
            "error": ""
        }
        
        result = self.workflow.invoke(initial_state)
        
        return {
            "user_input": result.get("user_input"),
            "agent_used": result.get("agent_used"),
            "response": result.get("agent_response"),
            "intent": result.get("intent"),
            "error": result.get("error", "")
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all agents.
        
        Returns:
            Status information
        """
        return self.orchestrator.get_agent_status()
