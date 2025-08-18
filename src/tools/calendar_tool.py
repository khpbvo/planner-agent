"""
MacOS Calendar integration tool using AppleScript via osascript
"""
import json
import subprocess
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from openai_agents import function_tool
from pydantic import BaseModel

from ..models.event import CalendarEvent, EventRecurrence


class CalendarOperation(BaseModel):
    """Input for calendar operations"""
    operation: str  # "list", "create", "update", "delete", "find_free_slots"
    calendar_name: Optional[str] = "Calendar"  # Default calendar
    event_data: Optional[Dict[str, Any]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    event_id: Optional[str] = None


@function_tool
async def manage_calendar(operation_input: CalendarOperation) -> str:
        """
        Manage calendar events in MacOS Calendar app
        
        Args:
            operation_input: Calendar operation details
        """
        operation = operation_input.operation
        
        if operation == "list":
            return await list_events(
                operation_input.calendar_name,
                operation_input.start_date,
                operation_input.end_date
            )
        
        elif operation == "create":
            if not operation_input.event_data:
                return "Error: event_data required for create operation"
            return await create_event(
                operation_input.calendar_name,
                operation_input.event_data
            )
        
        elif operation == "update":
            if not operation_input.event_id or not operation_input.event_data:
                return "Error: event_id and event_data required for update operation"
            return await update_event(
                operation_input.event_id,
                operation_input.event_data,
                operation_input.calendar_name
            )
        
        elif operation == "delete":
            if not operation_input.event_id:
                return "Error: event_id required for delete operation"
            return await delete_event(
                operation_input.event_id,
                operation_input.calendar_name
            )
        
        elif operation == "find_free_slots":
            return await find_free_slots(
                operation_input.start_date or datetime.now(),
                operation_input.end_date or (datetime.now() + timedelta(days=7)),
                operation_input.calendar_name
            )
        
        else:
            return f"Unknown operation: {operation}"
    
def create_calendar_tool():
    """Create the calendar tool for MacOS Calendar integration"""
    return manage_calendar


async def list_events(
    calendar_name: str = "Calendar",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> str:
    """List calendar events using AppleScript"""
    
    if not start_date:
        start_date = datetime.now()
    if not end_date:
        end_date = start_date + timedelta(days=7)
    
    # AppleScript to list events
    script = f'''
    on run
        set startDate to date "{start_date.strftime('%m/%d/%Y')}"
        set endDate to date "{end_date.strftime('%m/%d/%Y')}"
        set eventList to {{}}
        
        tell application "Calendar"
            tell calendar "{calendar_name}"
                set theEvents to every event whose start date >= startDate and start date <= endDate
                
                repeat with anEvent in theEvents
                    set eventInfo to (summary of anEvent) & "|" & ¬
                        (start date of anEvent as string) & "|" & ¬
                        (end date of anEvent as string) & "|" & ¬
                        (location of anEvent as string) & "|" & ¬
                        (description of anEvent as string)
                    set end of eventList to eventInfo
                end repeat
            end tell
        end tell
        
        return eventList
    end run
    '''
    
    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            text=True,
            check=True
        )
        
        events = []
        if result.stdout.strip():
            event_strings = result.stdout.strip().split(', ')
            for event_str in event_strings:
                parts = event_str.split('|')
                if len(parts) >= 3:
                    events.append({
                        "title": parts[0],
                        "start": parts[1],
                        "end": parts[2],
                        "location": parts[3] if len(parts) > 3 else "",
                        "description": parts[4] if len(parts) > 4 else ""
                    })
        
        return json.dumps(events, indent=2)
        
    except subprocess.CalledProcessError as e:
        return f"Error listing events: {e.stderr}"


async def create_event(
    calendar_name: str,
    event_data: Dict[str, Any]
) -> str:
    """Create a new calendar event"""
    
    # Extract event details
    title = event_data.get("title", "New Event")
    start_date = event_data.get("start_date", datetime.now().isoformat())
    end_date = event_data.get("end_date", (datetime.now() + timedelta(hours=1)).isoformat())
    location = event_data.get("location", "")
    description = event_data.get("description", "")
    
    # Convert ISO dates to AppleScript format
    start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    
    # AppleScript to create event
    script = f'''
    on run
        set startDate to date "{start_dt.strftime('%m/%d/%Y %I:%M:%S %p')}"
        set endDate to date "{end_dt.strftime('%m/%d/%Y %I:%M:%S %p')}"
        
        tell application "Calendar"
            tell calendar "{calendar_name}"
                set newEvent to make new event with properties {{summary:"{title}", start date:startDate, end date:endDate}}
                
                if "{location}" is not "" then
                    set location of newEvent to "{location}"
                end if
                
                if "{description}" is not "" then
                    set description of newEvent to "{description}"
                end if
                
                return "Event created: " & summary of newEvent
            end tell
        end tell
    end run
    '''
    
    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
        
    except subprocess.CalledProcessError as e:
        return f"Error creating event: {e.stderr}"


async def update_event(
    event_id: str,
    event_data: Dict[str, Any],
    calendar_name: str = "Calendar"
) -> str:
    """Update an existing calendar event"""
    # This is a simplified version - full implementation would need proper event ID handling
    return f"Event update not yet fully implemented. Would update event {event_id} with: {json.dumps(event_data)}"


async def delete_event(
    event_id: str,
    calendar_name: str = "Calendar"
) -> str:
    """Delete a calendar event"""
    # This is a simplified version - full implementation would need proper event ID handling
    return f"Event deletion not yet fully implemented. Would delete event {event_id}"


async def find_free_slots(
    start_date: datetime,
    end_date: datetime,
    calendar_name: str = "Calendar",
    slot_duration: int = 30  # minutes
) -> str:
    """Find available time slots in the calendar"""
    
    # First, get all events in the date range
    events_json = await list_events(calendar_name, start_date, end_date)
    events = json.loads(events_json)
    
    # Simple algorithm to find free slots
    # This is a basic implementation - would need enhancement for production
    free_slots = []
    current_time = start_date.replace(hour=9, minute=0)  # Start at 9 AM
    end_of_day = start_date.replace(hour=17, minute=0)  # End at 5 PM
    
    # For simplicity, just return some mock free slots
    while current_time < end_of_day:
        free_slots.append({
            "start": current_time.isoformat(),
            "end": (current_time + timedelta(minutes=slot_duration)).isoformat(),
            "duration_minutes": slot_duration
        })
        current_time += timedelta(hours=1)
    
    return json.dumps({
        "free_slots": free_slots[:5],  # Return top 5 slots
        "total_free_slots": len(free_slots)
    }, indent=2)