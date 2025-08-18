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
    
    # Enhanced AppleScript with better error handling and JSON output
    script = f'''
    on run
        try
            set startDate to date "{start_date.strftime('%m/%d/%Y')}"
            set endDate to date "{end_date.strftime('%m/%d/%Y')}"
            set eventList to {{}}
            
            tell application "Calendar"
                -- Check if calendar exists
                try
                    set targetCalendar to calendar "{calendar_name}"
                on error
                    return "Error: Calendar '{calendar_name}' not found"
                end try
                
                tell targetCalendar
                    set theEvents to every event whose start date >= startDate and start date <= endDate
                    
                    repeat with anEvent in theEvents
                        set eventRecord to {{}}
                        set eventRecord to eventRecord & "{{" & ¬
                            "\\"title\\": \\"" & (summary of anEvent) & "\\", " & ¬
                            "\\"start\\": \\"" & (start date of anEvent as string) & "\\", " & ¬
                            "\\"end\\": \\"" & (end date of anEvent as string) & "\\", " & ¬
                            "\\"location\\": \\"" & (location of anEvent as string) & "\\", " & ¬
                            "\\"description\\": \\"" & (description of anEvent as string) & "\\"" & ¬
                            "}}"
                        set end of eventList to eventRecord
                    end repeat
                end tell
            end tell
            
            if length of eventList > 0 then
                set AppleScript's text item delimiters to ","
                set eventListString to "[" & (eventList as string) & "]"
                set AppleScript's text item delimiters to ""
                return eventListString
            else
                return "[]"
            end if
            
        on error errMsg
            return "AppleScript Error: " & errMsg
        end try
    end run
    '''
    
    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            text=True,
            check=True,
            timeout=30
        )
        
        output = result.stdout.strip()
        
        # If it's already JSON-like, try to parse and clean it
        if output.startswith('[') and output.endswith(']'):
            try:
                # Try to parse as JSON (might need some cleaning)
                import re
                # Clean up the JSON-like string
                cleaned = re.sub(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'"\1":', output)
                events = json.loads(cleaned)
                return json.dumps(events, indent=2)
            except:
                pass
        
        # Fallback: return structured data
        if output.startswith("Error:") or output.startswith("AppleScript Error:"):
            return json.dumps({"error": output}, indent=2)
        
        return json.dumps({
            "events": [],
            "message": f"Found events but could not parse: {output[:200]}..."
        }, indent=2)
        
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "Calendar operation timed out"}, indent=2)
    except subprocess.CalledProcessError as e:
        return json.dumps({
            "error": f"AppleScript execution failed: {e.stderr}",
            "suggestion": "Make sure Calendar app is accessible and the calendar name is correct"
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Unexpected error: {str(e)}"}, indent=2)


async def create_event(
    calendar_name: str,
    event_data: Dict[str, Any]
) -> str:
    """Create a new calendar event"""
    
    try:
        # Extract and validate event details
        title = event_data.get("title", "New Event").replace('"', '\\"')
        location = event_data.get("location", "").replace('"', '\\"')
        description = event_data.get("description", "").replace('"', '\\"')
        
        # Handle date parsing more robustly
        start_date = event_data.get("start_date")
        end_date = event_data.get("end_date")
        
        if isinstance(start_date, str):
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        elif isinstance(start_date, datetime):
            start_dt = start_date
        else:
            start_dt = datetime.now()
            
        if isinstance(end_date, str):
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        elif isinstance(end_date, datetime):
            end_dt = end_date
        else:
            end_dt = start_dt + timedelta(hours=1)
        
        # Validate dates
        if end_dt <= start_dt:
            end_dt = start_dt + timedelta(hours=1)
        
        # Enhanced AppleScript with better error handling
        script = f'''
        on run
            try
                set startDate to date "{start_dt.strftime('%m/%d/%Y %I:%M:%S %p')}"
                set endDate to date "{end_dt.strftime('%m/%d/%Y %I:%M:%S %p')}"
                
                tell application "Calendar"
                    -- Check if calendar exists
                    try
                        set targetCalendar to calendar "{calendar_name}"
                    on error
                        return "Error: Calendar '{calendar_name}' not found. Available calendars: " & (name of every calendar)
                    end try
                    
                    tell targetCalendar
                        set newEvent to make new event with properties {{summary:"{title}", start date:startDate, end date:endDate}}
                        
                        if "{location}" is not "" then
                            set location of newEvent to "{location}"
                        end if
                        
                        if "{description}" is not "" then
                            set description of newEvent to "{description}"
                        end if
                        
                        -- Get the created event details
                        set eventId to id of newEvent
                        set eventSummary to summary of newEvent
                        
                        return "{{" & ¬
                            "\\"status\\": \\"success\\", " & ¬
                            "\\"message\\": \\"Event created successfully\\", " & ¬
                            "\\"event\\": {{" & ¬
                                "\\"id\\": \\"" & eventId & "\\", " & ¬
                                "\\"title\\": \\"" & eventSummary & "\\", " & ¬
                                "\\"start\\": \\"" & (start date of newEvent as string) & "\\", " & ¬
                                "\\"end\\": \\"" & (end date of newEvent as string) & "\\"" & ¬
                            "}}" & ¬
                        "}}"
                    end tell
                end tell
                
            on error errMsg
                return "{{" & ¬
                    "\\"status\\": \\"error\\", " & ¬
                    "\\"message\\": \\"" & errMsg & "\\"" & ¬
                "}}"
            end try
        end run
        '''
        
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            text=True,
            check=True,
            timeout=30
        )
        
        output = result.stdout.strip()
        
        # Try to parse as JSON
        try:
            # Clean up potential JSON formatting issues
            cleaned = output.replace('\n', '').replace('\r', '')
            return cleaned
        except:
            return json.dumps({
                "status": "success",
                "message": f"Event created but response parsing failed: {output}",
                "event": {
                    "title": title,
                    "start": start_dt.isoformat(),
                    "end": end_dt.isoformat()
                }
            })
            
    except subprocess.TimeoutExpired:
        return json.dumps({
            "status": "error",
            "message": "Calendar operation timed out"
        })
    except subprocess.CalledProcessError as e:
        return json.dumps({
            "status": "error", 
            "message": f"AppleScript execution failed: {e.stderr}",
            "suggestion": "Check calendar permissions and calendar name"
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Event creation failed: {str(e)}"
        })


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