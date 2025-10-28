"""Configuration module for the multi-agent system."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration settings for the agentic workflow."""
    
    # NVIDIA API Configuration
    NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
    NEMOTRON_MODEL = os.getenv("NEMOTRON_MODEL", "nvidia/nemotron-nano-9b-instruct")
    
    # Google Calendar Configuration
    GOOGLE_CALENDAR_CREDENTIALS_PATH = os.getenv(
        "GOOGLE_CALENDAR_CREDENTIALS_PATH", "credentials.json"
    )
    
    # Vector Store Configuration
    CHROMA_PERSIST_DIRECTORY = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that required configuration is present."""
        if not cls.NVIDIA_API_KEY:
            raise ValueError("NVIDIA_API_KEY is required. Please set it in .env file.")
        return True
