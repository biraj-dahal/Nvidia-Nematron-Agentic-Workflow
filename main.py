"""Main entry point for the multi-agent workflow system."""

import os
import sys
from typing import Optional
from src.config import Config
from src.workflow import MultiAgentWorkflow


def main():
    """Main function to run the multi-agent system."""
    print("=" * 60)
    print("Multi-Agent Agentic Workflow System")
    print("Powered by: Nemotron-nano-9b-v2 + LangGraph")
    print("=" * 60)
    print()
    
    # Load configuration
    try:
        Config.validate()
    except ValueError as e:
        print(f"Configuration Error: {e}")
        print("\nPlease create a .env file with your NVIDIA_API_KEY")
        print("You can copy .env.example to .env and fill in your API key")
        return
    
    # Initialize workflow
    print("Initializing multi-agent workflow...")
    workflow = MultiAgentWorkflow(
        nvidia_api_key=Config.NVIDIA_API_KEY,
        model=Config.NEMOTRON_MODEL
    )
    print("✓ Workflow initialized successfully!")
    print()
    
    # Display available agents
    print("Available Agents:")
    print("  • Calendar Agent - Scheduling and calendar management")
    print("  • Summarizer Agent - Text summarization and key point extraction")
    print("  • Archivist Agent - Document storage and retrieval (RAG)")
    print("  • Scribe Service - Note-taking and management")
    print()
    
    # Interactive loop
    print("Type your requests below (or 'quit' to exit, 'status' for agent status):")
    print("-" * 60)
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye!")
                break
            
            if user_input.lower() == 'status':
                status = workflow.get_status()
                print("\n📊 Agent Status:")
                for agent_name, agent_status in status.items():
                    print(f"  {agent_name}: {agent_status}")
                continue
            
            # Process user input through workflow
            result = workflow.run(user_input)
            
            # Display result
            print(f"\n🤖 {result['agent_used']} Agent:")
            print(f"{result['response']}")
            
            if result.get('error'):
                print(f"\n⚠️  Error: {result['error']}")
        
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")


if __name__ == "__main__":
    main()
