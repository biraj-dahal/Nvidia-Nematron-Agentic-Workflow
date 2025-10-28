"""Example usage of the multi-agent workflow system."""

import os
from dotenv import load_dotenv
from src.workflow import MultiAgentWorkflow

# Load environment variables
load_dotenv()


def run_examples():
    """Run example interactions with the multi-agent system."""
    
    # Initialize the workflow
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        print("Please set NVIDIA_API_KEY in your .env file")
        return
    
    workflow = MultiAgentWorkflow(
        nvidia_api_key=api_key,
        model="nvidia/nemotron-nano-9b-instruct"
    )
    
    print("=" * 70)
    print("Multi-Agent Workflow - Example Usage")
    print("=" * 70)
    print()
    
    # Example 1: Calendar Agent
    print("Example 1: Using Calendar Agent")
    print("-" * 70)
    result = workflow.run("Create a meeting for tomorrow at 2 PM with the team")
    print(f"User: Create a meeting for tomorrow at 2 PM with the team")
    print(f"Agent Used: {result['agent_used']}")
    print(f"Response: {result['response']}")
    print()
    
    # Example 2: Scribe Service
    print("Example 2: Using Scribe Service")
    print("-" * 70)
    result = workflow.run("Take note: Need to review the Q4 budget proposals")
    print(f"User: Take note: Need to review the Q4 budget proposals")
    print(f"Agent Used: {result['agent_used']}")
    print(f"Response: {result['response']}")
    print()
    
    # Example 3: Summarizer Agent
    print("Example 3: Using Summarizer Agent")
    print("-" * 70)
    long_text = """
    The quarterly business review meeting covered several important topics.
    First, we discussed the revenue growth which exceeded expectations by 15%.
    The marketing team presented their new campaign strategy focusing on digital channels.
    Engineering reported successful completion of the platform upgrade with minimal downtime.
    Customer satisfaction scores improved by 8 points this quarter.
    Action items include: schedule follow-up meetings with key clients,
    finalize the budget for next quarter, and prepare for the annual conference.
    """
    result = workflow.run(f"Summarize this text: {long_text}")
    print(f"User: Summarize the quarterly review text")
    print(f"Agent Used: {result['agent_used']}")
    print(f"Response: {result['response']}")
    print()
    
    # Example 4: Archivist Agent
    print("Example 4: Using Archivist Agent")
    print("-" * 70)
    result = workflow.run("Archive this document: Company policy on remote work updated 2024")
    print(f"User: Archive document about remote work policy")
    print(f"Agent Used: {result['agent_used']}")
    print(f"Response: {result['response']}")
    print()
    
    # Check status
    print("System Status:")
    print("-" * 70)
    status = workflow.get_status()
    for agent_name, agent_status in status.items():
        print(f"{agent_name}: {agent_status}")
    print()
    
    print("=" * 70)
    print("Examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    run_examples()
