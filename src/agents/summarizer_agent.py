"""Summarizer Agent - Processes and summarizes information."""

from typing import List, Dict, Optional
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain.prompts import ChatPromptTemplate


class SummarizerAgent:
    """Agent responsible for summarizing text and information."""
    
    def __init__(self, llm: ChatNVIDIA):
        """Initialize the Summarizer Agent.
        
        Args:
            llm: Language model instance
        """
        self.llm = llm
        self.summaries: List[Dict] = []
    
    def summarize_text(self, text: str, max_length: Optional[int] = None) -> str:
        """Summarize a given text.
        
        Args:
            text: Text to summarize
            max_length: Maximum length of summary (optional)
            
        Returns:
            Summary of the text
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert summarizer. Create concise, accurate summaries that capture the key points."),
            ("user", f"Summarize the following text{' in about ' + str(max_length) + ' words' if max_length else ''}:\n\n{text}")
        ])
        
        try:
            messages = prompt.format_messages()
            response = self.llm.invoke(messages)
            summary = response.content
            
            # Store the summary
            self.summaries.append({
                "original_length": len(text),
                "summary": summary,
                "summary_length": len(summary)
            })
            
            return summary
        except Exception as e:
            return f"Error summarizing text: {str(e)}"
    
    def summarize_conversation(self, messages: List[str]) -> str:
        """Summarize a conversation from multiple messages.
        
        Args:
            messages: List of conversation messages
            
        Returns:
            Summary of the conversation
        """
        conversation = "\n".join([f"- {msg}" for msg in messages])
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert at summarizing conversations. Extract key points, decisions, and action items."),
            ("user", f"Summarize this conversation:\n\n{conversation}")
        ])
        
        try:
            formatted = prompt.format_messages()
            response = self.llm.invoke(formatted)
            return response.content
        except Exception as e:
            return f"Error summarizing conversation: {str(e)}"
    
    def extract_key_points(self, text: str, num_points: int = 5) -> List[str]:
        """Extract key points from text.
        
        Args:
            text: Text to extract points from
            num_points: Number of key points to extract
            
        Returns:
            List of key points
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert at extracting key information. Extract the most important points."),
            ("user", f"Extract {num_points} key points from this text:\n\n{text}\n\nFormat each point as a bullet point.")
        ])
        
        try:
            formatted = prompt.format_messages()
            response = self.llm.invoke(formatted)
            # Parse bullet points
            points = [
                line.strip().lstrip('•-*').strip() 
                for line in response.content.split('\n') 
                if line.strip() and (line.strip().startswith(('•', '-', '*')) or line[0].isdigit())
            ]
            return points[:num_points]
        except Exception as e:
            return [f"Error extracting key points: {str(e)}"]
    
    def summarize_meeting_notes(self, notes: str) -> Dict[str, any]:
        """Summarize meeting notes with structured output.
        
        Args:
            notes: Meeting notes to summarize
            
        Returns:
            Structured summary with key sections
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert meeting summarizer. Create a structured summary with:
1. Main Discussion Points
2. Decisions Made
3. Action Items
4. Next Steps"""),
            ("user", f"Summarize these meeting notes:\n\n{notes}")
        ])
        
        try:
            formatted = prompt.format_messages()
            response = self.llm.invoke(formatted)
            
            return {
                "summary": response.content,
                "original_notes": notes,
                "structured": True
            }
        except Exception as e:
            return {
                "error": f"Error summarizing meeting notes: {str(e)}",
                "summary": "",
                "structured": False
            }
    
    def process_request(self, request: str, content: str) -> str:
        """Process a summarization request.
        
        Args:
            request: Type of summarization requested
            content: Content to summarize
            
        Returns:
            Summarized content
        """
        if "key points" in request.lower():
            points = self.extract_key_points(content)
            return "\n".join(f"- {point}" for point in points)
        elif "meeting" in request.lower():
            result = self.summarize_meeting_notes(content)
            return result.get("summary", result.get("error", "No summary available"))
        else:
            return self.summarize_text(content)
