"""
Google Calendar Agent Tool
A comprehensive tool for interacting with Google Calendar API using OAuth 2.0
Supports fetching events, finding available slots, and date range queries
"""

import os
import pickle
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import pytz

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Scopes required for calendar and Gmail access
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.send'
]

# Timezone configuration - Auto-handles EST/EDT
TIMEZONE = pytz.timezone('America/New_York')

CALEN_ID = '1e48c44c1ad2d312b31ee14323a2fc98c71147e7d43450be5210b88638c75384@group.calendar.google.com'
@dataclass
class CalendarEvent:
    """Represents a calendar event"""
    id: str
    summary: str
    start: str
    end: str
    description: Optional[str] = None
    location: Optional[str] = None
    attendees: Optional[List[str]] = None
    
    def to_dict(self):
        return {
            'id': self.id,
            'summary': self.summary,
            'start': self.start,
            'end': self.end,
            'description': self.description,
            'location': self.location,
            'attendees': self.attendees
        }


@dataclass
class TimeSlot:
    """Represents an available time slot"""
    start: str
    end: str
    duration_minutes: int
    
    def to_dict(self):
        return {
            'start': self.start,
            'end': self.end,
            'duration_minutes': self.duration_minutes
        }


class CalendarAgentTool:
    def __init__(self):
        """Initialize the calendar agent with OAuth 2.0 authentication"""
        self.service = self._get_calendar_service()
    
    def _get_calendar_service(self):
        """Authenticate and return calendar service"""
        creds = None
        
        # Token file stores the user's access and refresh tokens
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, let user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'client_secret_175568546829-c0dm1uj4mhr0k36vb1t12qp6hgmst5hb.apps.googleusercontent.com.json', SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        
        return build('calendar', 'v3', credentials=creds)
    
    def fetch_events(
        self,
        days_ahead: int = 7,
        days_back: int = 0,
        max_results: int = 10,
        date_range_start: Optional[str] = None,
        date_range_end: Optional[str] = None,
        search_query: Optional[str] = None,
        single_events: bool = True,
        order_by: str = 'startTime'
    ) -> List[CalendarEvent]:
        """
        Fetch events from Google Calendar
        
        Args:
            days_ahead: Number of days to look ahead from today
            days_back: Number of days to look back from today
            max_results: Maximum number of events to return
            date_range_start: Specific start date (ISO format: YYYY-MM-DD)
            date_range_end: Specific end date (ISO format: YYYY-MM-DD)
            search_query: Search for events containing this text
            single_events: Expand recurring events into instances
            order_by: Order results by 'startTime' or 'updated'
            
        Returns:
            List of CalendarEvent objects
        """
        now = datetime.now(timezone.utc)
        
        # Calculate time range
        if date_range_start:
            time_min = datetime.fromisoformat(date_range_start).replace(tzinfo=timezone.utc).isoformat()
        else:
            time_min = (now - timedelta(days=days_back)).isoformat()
        
        if date_range_end:
            time_max = datetime.fromisoformat(date_range_end).replace(tzinfo=timezone.utc).isoformat()
        else:
            time_max = (now + timedelta(days=days_ahead)).isoformat()
        
        # Build API parameters
        params = {
            'calendarId': CALEN_ID,
            'timeMin': time_min,
            'timeMax': time_max,
            'maxResults': max_results,
            'singleEvents': single_events,
            'orderBy': order_by
        }
        
        if search_query:
            params['q'] = search_query
        
        # Make API request
        events_result = self.service.events().list(**params).execute()
        
        # Parse events
        events = []
        for item in events_result.get('items', []):
            event = CalendarEvent(
                id=item['id'],
                summary=item.get('summary', 'No Title'),
                start=item['start'].get('dateTime', item['start'].get('date')),
                end=item['end'].get('dateTime', item['end'].get('date')),
                description=item.get('description'),
                location=item.get('location'),
                attendees=[a['email'] for a in item.get('attendees', [])]
            )
            events.append(event)
        
        return events
    
    def create_event(self, title: str, start_time: str, end_time: str,
                     description: str = "", attendees: Optional[List[str]] = None) -> str:
        """Create a new calendar event and return its event ID"""
        event = {
            'summary': title,
            'description': description,
            'start': {'dateTime': start_time, 'timeZone': 'America/New_York'},
            'end': {'dateTime': end_time, 'timeZone': 'America/New_York'},
        }
        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]

        created_event = self.service.events().insert(
            calendarId=CALEN_ID,
            body=event
        ).execute()

        return created_event.get('id', 'unknown_id')
    
    def add_notes_to_event(self, event_id: str, notes: str) -> str:
        """Append notes to an existing event's description."""
        try:
            event = self.service.events().get(calendarId=CALEN_ID, eventId=event_id).execute()
            existing_description = event.get('description', '')
            updated_description = (existing_description + '\n\nNotes:\n' + notes).strip()
            event['description'] = updated_description

            updated_event = self.service.events().update(
                calendarId=CALEN_ID, eventId=event_id, body=event
            ).execute()

            return f"Notes added to event '{updated_event.get('summary', 'unknown')}'"
        except Exception as e:
            return f"Failed to add notes: {e}"

    def update_event(self, event_id: str, updates: Dict[str, Any]) -> str:
        """Update existing calendar event"""
        event = self.service.events().get(calendarId=CALEN_ID, eventId=event_id).execute()
        event.update(updates)
        updated_event = self.service.events().update(
            calendarId=CALEN_ID, eventId=event_id, body=event
        ).execute()
        return updated_event.get('id', 'unknown_id')
    
    def find_available_slots(
        self,
        duration_minutes: int = 60,
        days_ahead: int = 7,
        working_hours_start: str = '09:00',
        working_hours_end: str = '17:00',
        max_slots: int = 5,
        skip_weekends: bool = True
    ) -> List[TimeSlot]:
        """
        Find available time slots based on existing calendar events
        
        Args:
            duration_minutes: Required meeting duration in minutes
            days_ahead: Number of days to search ahead
            working_hours_start: Start of working hours (HH:MM format)
            working_hours_end: End of working hours (HH:MM format)
            max_slots: Maximum number of slots to return
            skip_weekends: Whether to skip Saturday and Sunday
            
        Returns:
            List of TimeSlot objects
        """
        # Fetch all events in the range
        events = self.fetch_events(days_ahead=days_ahead, max_results=250)
        
        # Parse working hours
        work_start_hour, work_start_min = map(int, working_hours_start.split(':'))
        work_end_hour, work_end_min = map(int, working_hours_end.split(':'))
        
        available_slots = []
        current_date = datetime.now(TIMEZONE).date()

        for day_offset in range(days_ahead):
            check_date = current_date + timedelta(days=day_offset)

            # Skip weekends if requested
            if skip_weekends and check_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
                continue

            # Create working day boundaries
            day_start = TIMEZONE.localize(datetime.combine(
                check_date,
                datetime.min.time().replace(hour=work_start_hour, minute=work_start_min)
            ))
            day_end = TIMEZONE.localize(datetime.combine(
                check_date,
                datetime.min.time().replace(hour=work_end_hour, minute=work_end_min)
            ))
            
            # Get events for this day
            day_events = []
            for e in events:
                try:
                    event_start_str = e.start.replace('Z', '+00:00')
                    event_date = datetime.fromisoformat(event_start_str).date()
                    if event_date == check_date:
                        day_events.append(e)
                except:
                    continue
            
            # Sort events by start time
            day_events.sort(key=lambda e: e.start)
            
            # Find gaps between events
            current_time = day_start
            
            for event in day_events:
                event_start_str = event.start.replace('Z', '+00:00')
                event_end_str = event.end.replace('Z', '+00:00')
                event_start = datetime.fromisoformat(event_start_str)
                event_end = datetime.fromisoformat(event_end_str)
                
                # Check if there's a gap before this event
                gap_minutes = (event_start - current_time).total_seconds() / 60
                
                if gap_minutes >= duration_minutes:
                    slot_end = current_time + timedelta(minutes=duration_minutes)
                    available_slots.append(TimeSlot(
                        start=current_time.isoformat(),
                        end=slot_end.isoformat(),
                        duration_minutes=duration_minutes
                    ))
                    
                    if len(available_slots) >= max_slots:
                        return available_slots
                
                current_time = max(current_time, event_end)
            
            # Check for slot at end of day
            remaining_minutes = (day_end - current_time).total_seconds() / 60
            if remaining_minutes >= duration_minutes:
                slot_end = current_time + timedelta(minutes=duration_minutes)
                available_slots.append(TimeSlot(
                    start=current_time.isoformat(),
                    end=slot_end.isoformat(),
                    duration_minutes=duration_minutes
                ))
                
                if len(available_slots) >= max_slots:
                    return available_slots
        
        return available_slots
    
    def get_events_by_date_range(
        self,
        start_date: str,
        end_date: str,
        search_query: Optional[str] = None
    ) -> List[CalendarEvent]:
        """
        Get events within a specific date range
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            search_query: Optional search query
            
        Returns:
            List of CalendarEvent objects
        """
        return self.fetch_events(
            date_range_start=start_date,
            date_range_end=end_date,
            search_query=search_query,
            max_results=250
        )
    
    def get_today_events(self) -> List[CalendarEvent]:
        """Get all events for today"""
        today = datetime.now(timezone.utc).date().isoformat()
        tomorrow = (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat()
        return self.get_events_by_date_range(today, tomorrow)
    
    def get_this_week_events(self) -> List[CalendarEvent]:
        """Get all events for the current week"""
        today = datetime.now(timezone.utc).date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=7)
        return self.get_events_by_date_range(
            week_start.isoformat(),
            week_end.isoformat()
        )
    
    def search_events(self, query: str, max_results: int = 10) -> List[CalendarEvent]:
        """
        Search for events matching a query
        
        Args:
            query: Search term
            max_results: Maximum results to return
            
        Returns:
            List of matching CalendarEvent objects
        """
        return self.fetch_events(
            days_ahead=365,  # Search a year ahead
            days_back=30,    # Search a month back
            search_query=query,
            max_results=max_results
        )


# Example usage and testing
def main():
    """
    Example usage of the Calendar Agent Tool
    """
    
    agent = CalendarAgentTool()
    
    print("=" * 80)
    print("Google Calendar Agent Tool - Demo")
    print("=" * 80)
    
    # Example 1: Fetch upcoming events
    print("\n1. Fetching events for the next 30 days...")
    try:
        events = agent.fetch_events(days_ahead=30, max_results=5)
        print(f"Found {len(events)} events:")
        for event in events:
            print(f"  - {event.summary}")
            print(f"    Start: {event.start}")
            print(f"    End: {event.end}")
            if event.location:
                print(f"    Location: {event.location}")
            print()
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 2: Get today's events
    print("\n2. Getting today's events...")
    try:
        events = agent.get_today_events()
        print(f"Found {len(events)} events today:")
        for event in events:
            print(f"  - {event.summary} ({event.start})")
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 3: Search for specific events
    print("\n3. Searching for events with 'meeting' in title...")
    try:
        events = agent.search_events("meeting", max_results=3)
        print(f"Found {len(events)} matching events:")
        for event in events:
            print(f"  - {event.summary} ({event.start})")
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 4: Get events in specific date range
    print("\n4. Getting events in next week...")
    try:
        today = datetime.now(timezone.utc).date()
        next_week = today + timedelta(days=7)
        events = agent.get_events_by_date_range(today.isoformat(), next_week.isoformat())
        print(f"Found {len(events)} events:")
        for event in events[:5]:  # Show first 5
            print(f"  - {event.summary} ({event.start})")
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 5: Find available slots
    print("\n5. Finding available time slots...")
    try:
        slots = agent.find_available_slots(
            duration_minutes=60,
            days_ahead=7,
            max_slots=3
        )
        print(f"Found {len(slots)} available slots:")
        for slot in slots:
            print(f"  - {slot.start} to {slot.end} ({slot.duration_minutes} minutes)")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 80)
    print("Demo complete!")
    print("=" * 80)

main()