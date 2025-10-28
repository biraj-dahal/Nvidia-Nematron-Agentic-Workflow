"""Multi-Agent Agentic Workflow System.

Powered by NVIDIA Nemotron and LangGraph.
"""

__version__ = "1.0.0"
__author__ = "Nvidia Nemotron Agentic Workflow Team"

from .workflow import MultiAgentWorkflow
from .agents import Orchestrator, CalendarAgent, SummarizerAgent, ArchivistAgent
from .tools import ScribeService

__all__ = [
    "MultiAgentWorkflow",
    "Orchestrator",
    "CalendarAgent",
    "SummarizerAgent",
    "ArchivistAgent",
    "ScribeService"
]
