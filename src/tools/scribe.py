"""Scribe Service - A tool for taking and managing notes."""

from datetime import datetime
from typing import List, Dict, Optional
import json
import os


class ScribeService:
    """Service for managing notes and transcriptions."""
    
    def __init__(self, notes_dir: str = "./notes"):
        """Initialize the Scribe Service.
        
        Args:
            notes_dir: Directory to store notes
        """
        self.notes_dir = notes_dir
        os.makedirs(notes_dir, exist_ok=True)
        self.notes: List[Dict] = []
        self._load_notes()
    
    def _load_notes(self) -> None:
        """Load existing notes from storage."""
        notes_file = os.path.join(self.notes_dir, "notes.json")
        if os.path.exists(notes_file):
            with open(notes_file, 'r') as f:
                self.notes = json.load(f)
    
    def _save_notes(self) -> None:
        """Save notes to storage."""
        notes_file = os.path.join(self.notes_dir, "notes.json")
        with open(notes_file, 'w') as f:
            json.dump(self.notes, f, indent=2)
    
    def take_note(self, content: str, tags: Optional[List[str]] = None) -> Dict:
        """Take a new note.
        
        Args:
            content: The note content
            tags: Optional tags for categorization
            
        Returns:
            The created note with metadata
        """
        note = {
            "id": len(self.notes) + 1,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "tags": tags or []
        }
        self.notes.append(note)
        self._save_notes()
        return note
    
    def get_notes(self, tag: Optional[str] = None) -> List[Dict]:
        """Retrieve notes, optionally filtered by tag.
        
        Args:
            tag: Optional tag to filter by
            
        Returns:
            List of notes matching the criteria
        """
        if tag:
            return [note for note in self.notes if tag in note.get("tags", [])]
        return self.notes
    
    def search_notes(self, query: str) -> List[Dict]:
        """Search notes by content.
        
        Args:
            query: Search query string
            
        Returns:
            List of notes containing the query
        """
        query_lower = query.lower()
        return [
            note for note in self.notes 
            if query_lower in note["content"].lower()
        ]
    
    def get_recent_notes(self, limit: int = 5) -> List[Dict]:
        """Get most recent notes.
        
        Args:
            limit: Number of recent notes to retrieve
            
        Returns:
            List of most recent notes
        """
        return sorted(
            self.notes, 
            key=lambda x: x["timestamp"], 
            reverse=True
        )[:limit]
