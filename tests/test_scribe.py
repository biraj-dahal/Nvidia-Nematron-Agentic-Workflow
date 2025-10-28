"""Tests for the Scribe Service."""

import os
import sys
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.tools.scribe import ScribeService


def test_scribe_take_note():
    """Test taking a note."""
    # Create temporary directory for notes
    with tempfile.TemporaryDirectory() as tmpdir:
        scribe = ScribeService(notes_dir=tmpdir)
        
        # Take a note
        note = scribe.take_note("Test note content", tags=["test"])
        
        # Verify note was created
        assert note["content"] == "Test note content"
        assert "test" in note["tags"]
        assert note["id"] == 1
        assert "timestamp" in note


def test_scribe_search_notes():
    """Test searching notes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        scribe = ScribeService(notes_dir=tmpdir)
        
        # Add some notes
        scribe.take_note("Meeting with team about project")
        scribe.take_note("Review budget proposals")
        scribe.take_note("Team building event planning")
        
        # Search for notes
        results = scribe.search_notes("team")
        
        # Should find 2 notes containing "team"
        assert len(results) == 2


def test_scribe_get_recent_notes():
    """Test getting recent notes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        scribe = ScribeService(notes_dir=tmpdir)
        
        # Add notes
        for i in range(10):
            scribe.take_note(f"Note {i}")
        
        # Get recent notes
        recent = scribe.get_recent_notes(limit=5)
        
        # Should return 5 most recent
        assert len(recent) == 5


def test_scribe_get_notes_by_tag():
    """Test filtering notes by tag."""
    with tempfile.TemporaryDirectory() as tmpdir:
        scribe = ScribeService(notes_dir=tmpdir)
        
        # Add notes with different tags
        scribe.take_note("Work note", tags=["work"])
        scribe.take_note("Personal note", tags=["personal"])
        scribe.take_note("Work meeting", tags=["work", "meeting"])
        
        # Get notes by tag
        work_notes = scribe.get_notes(tag="work")
        
        # Should find 2 work notes
        assert len(work_notes) == 2


if __name__ == "__main__":
    print("Running Scribe Service tests...")
    
    test_scribe_take_note()
    print("✓ test_scribe_take_note passed")
    
    test_scribe_search_notes()
    print("✓ test_scribe_search_notes passed")
    
    test_scribe_get_recent_notes()
    print("✓ test_scribe_get_recent_notes passed")
    
    test_scribe_get_notes_by_tag()
    print("✓ test_scribe_get_notes_by_tag passed")
    
    print("\nAll tests passed!")
