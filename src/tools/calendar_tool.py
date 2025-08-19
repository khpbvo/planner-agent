import subprocess
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from pydantic import BaseModel
from agents import function_tool

from models.event import CalendarEvent, EventRecurrence
from models.calendar_tool import CalendarOperation, CalendarResponse
from models import ToolError


class CalendarOperationLegacy(BaseModel):
    operation: str
    calendar_name: Optional[str] = "Calendar"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    event_id: Optional[str] = None
    event_data_json: Optional[str] = None


async def _manage_calendar_impl(operation_input: CalendarOperation) -> CalendarResponse:
    """Internal implementation of calendar management"""
    operation = operation_input.operation
    calendar_name = operation_input.calendar_name or "Calendar"
    start_date = operation_input.start_date
    end_date = operation_input.end_date
    event_id = operation_input.event_id
    event_data = operation_input.event_data

    try:
        if operation == "list":
            data = await list_events_structured(calendar_name, start_date, end_date)
            return CalendarResponse(**data)
        elif operation == "create":
            if not event_data:
                return CalendarResponse(status="error", message="event_data required for create operation")
            data = await create_event_structured(calendar_name, event_data)
            return CalendarResponse(**data)
        elif operation == "update":
            if not event_id or not event_data:
                return CalendarResponse(status="error", message="event_id and event_data required for update operation")
            data = await update_event_structured(event_id, event_data, calendar_name)
            return CalendarResponse(**data)
        elif operation == "delete":
            if not event_id:
                return CalendarResponse(status="error", message="event_id required for delete operation")
            data = await delete_event_structured(event_id, calendar_name)
            return CalendarResponse(**data)
        elif operation == "find_free_slots":
            start = start_date or datetime.now()
            end = end_date or (start + timedelta(days=7))
            data = await find_free_slots_structured(start, end, calendar_name)
            return CalendarResponse(**data)
        else:
            return CalendarResponse(status="error", message=f"Unknown operation: {operation}")
    except Exception as e:
        return CalendarResponse(status="error", message=f"Unexpected error: {str(e)}")


@function_tool
async def manage_calendar(operation_input: CalendarOperation) -> CalendarResponse:
    """Manage calendar events in MacOS Calendar app"""
    return await _manage_calendar_impl(operation_input)


# Remove the legacy function content for now since it's creating syntax issues
# async def manage_calendar_legacy(operation: str, calendar_name: str = "Calendar") -> str:
#     pass


def create_calendar_tool():
    """Create the calendar tool for MacOS Calendar integration"""
    return manage_calendar


async def list_events(
    calendar_name: str = "Calendar",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> str:
    """List calendar events using AppleScript."""
    try:
        # Default date range if not provided
        if not start_date:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if not end_date:
            end_date = start_date + timedelta(days=7)
        
        start_str = start_date.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_date.strftime("%Y-%m-%d %H:%M:%S")
        
        # AppleScript to list events
        applescript = f'''
        tell application "Calendar"
            set targetCalendar to calendar "{calendar_name}"
            set startDate to date "{start_str}"
            set endDate to date "{end_str}"
            set eventList to every event of targetCalendar whose start date ≥ startDate and start date ≤ endDate
            
            set eventData to {{}}
            repeat with anEvent in eventList
                set eventInfo to "{{" & ¬
                    "\\"summary\\": \\"" & (summary of anEvent) & "\\", " & ¬
                    "\\"start_date\\": \\"" & (start date of anEvent) & "\\", " & ¬
                    "\\"end_date\\": \\"" & (end date of anEvent) & "\\", " & ¬
                    "\\"description\\": \\"" & (description of anEvent) & "\\"" & ¬
                    "}}"
                set eventData to eventData & {{eventInfo}}
            end repeat
            
            return "[" & (my joinList(eventData, ",")) & "]"
        end tell
        
        on joinList(lst, delimiter)
            set oldDelims to AppleScript's text item delimiters
            set AppleScript's text item delimiters to delimiter
            set result to lst as text
            set AppleScript's text item delimiters to oldDelims
            return result
        end joinList
        '''
        
        result = subprocess.run(
            ["osascript", "-e", applescript],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = result.stdout.strip()
        
        if result.returncode == 0 and output:
            try:
                # Try to parse the JSON response
                events = json.loads(output)
                return json.dumps({
                    "status": "success",
                    "events": events,
                    "total": len(events)
                }, indent=2)
            except json.JSONDecodeError:
                # If JSON parsing fails, return the raw output
                return json.dumps({
                    "status": "partial_success",
                    "events": [],
                    "message": f"Found events but could not parse: {output[:200]}..."
                }, indent=2)
        
        # Fallback: return structured data
        if output.startswith("Error:") or output.startswith("AppleScript Error:"):
            return ToolError(message=output).model_dump_json(indent=2)

        return json.dumps({
            "status": "success",
            "events": [],
            "message": f"No events found or could not parse: {output[:200]}..."
        }, indent=2)

    except subprocess.TimeoutExpired:
        return ToolError(message="Calendar operation timed out").model_dump_json(indent=2)
    except subprocess.CalledProcessError as e:
        return json.dumps({
            **ToolError(message=f"AppleScript execution failed: {e.stderr}").model_dump(),
            "suggestion": "Make sure Calendar app is accessible and the calendar name is correct"
        }, indent=2)
    except Exception as e:
        return ToolError(message=f"Unexpected error: {str(e)}").model_dump_json(indent=2)


async def list_events_structured(
    calendar_name: str = "Calendar",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """List calendar events returning structured data."""
    result_str = await list_events(calendar_name, start_date, end_date)
    try:
        result = json.loads(result_str)
        return result
    except json.JSONDecodeError:
        return {"status": "error", "message": "Failed to parse calendar response", "events": []}


async def create_event(
    calendar_name: str,
    event_data: Dict[str, Any],
) -> str:
    """Create a new calendar event using AppleScript."""
    try:
        summary = event_data.get("summary", "New Event")
        start_date = event_data.get("start_date", datetime.now().isoformat())
        end_date = event_data.get("end_date", (datetime.now() + timedelta(hours=1)).isoformat())
        description = event_data.get("description", "")
        
        # Convert ISO dates to AppleScript format
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        start_str = start_dt.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_dt.strftime("%Y-%m-%d %H:%M:%S")
        
        applescript = f'''
        tell application "Calendar"
            set targetCalendar to calendar "{calendar_name}"
            set newEvent to make new event at end of events of targetCalendar
            set summary of newEvent to "{summary}"
            set start date of newEvent to date "{start_str}"
            set end date of newEvent to date "{end_str}"
            set description of newEvent to "{description}"
            return "Event created successfully"
        end tell
        '''
        
        result = subprocess.run(
            ["osascript", "-e", applescript],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return json.dumps({
                "status": "success",
                "message": "Event created successfully",
                "event": event_data
            }, indent=2)
        else:
            return ToolError(message=f"Failed to create event: {result.stderr}").model_dump_json(indent=2)
            
    except Exception as e:
        return ToolError(message=f"Error creating event: {str(e)}").model_dump_json(indent=2)


async def create_event_structured(
    calendar_name: str,
    event_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Create event returning structured data."""
    result_str = await create_event(calendar_name, event_data)
    try:
        return json.loads(result_str)
    except json.JSONDecodeError:
        return {"status": "error", "message": "Failed to parse create event response"}


async def update_event(
    event_id: str,
    event_data: Dict[str, Any],
    calendar_name: str = "Calendar",
) -> str:
    """Update an existing calendar event"""
    return ToolError(
        message=f"Event update not yet implemented for {event_id}",
        code="not_implemented",
    ).model_dump_json(indent=2)


async def update_event_structured(
    event_id: str,
    event_data: Dict[str, Any],
    calendar_name: str = "Calendar",
) -> Dict[str, Any]:
    """Update event returning structured data."""
    return {
        "status": "error",
        "message": f"Event update not yet implemented for {event_id}",
    }


async def delete_event(
    event_id: str,
    calendar_name: str = "Calendar",
) -> str:
    """Delete a calendar event"""
    return ToolError(
        message=f"Event deletion not yet implemented for {event_id}",
        code="not_implemented",
    ).model_dump_json(indent=2)


async def delete_event_structured(
    event_id: str,
    calendar_name: str = "Calendar",
) -> Dict[str, Any]:
    """Delete event returning structured data."""
    return {
        "status": "error",
        "message": f"Event deletion not yet implemented for {event_id}",
    }


async def find_free_slots(
    start_date: datetime,
    end_date: datetime,
    calendar_name: str = "Calendar",
    slot_duration: int = 30,
) -> str:
    """Find available time slots in the calendar."""
    # First, get all events in the date range
    events_json = await list_events(calendar_name, start_date, end_date)
    events = json.loads(events_json)

    if isinstance(events, dict) and events.get("status") == "error":
        return ToolError(message=events.get("message", "Failed to list events"), code=events.get("code")).model_dump_json(indent=2)
    
    # Simple algorithm to find free slots
    # This is a basic implementation - would need enhancement for production
    free_slots: List[Dict[str, Any]] = []
    current_time = start_date.replace(hour=9, minute=0, second=0, microsecond=0)
    end_of_day = start_date.replace(hour=17, minute=0, second=0, microsecond=0)

    while current_time < end_of_day:
        free_slots.append({
            "start": current_time.isoformat(),
            "end": (current_time + timedelta(minutes=slot_duration)).isoformat(),
            "duration_minutes": slot_duration,
        })
        current_time += timedelta(hours=1)

    return json.dumps({
        "status": "success",
        "free_slots": free_slots[:5],
        "total_free_slots": len(free_slots),
    }, indent=2)


async def find_free_slots_structured(
    start_date: datetime,
    end_date: datetime,
    calendar_name: str = "Calendar",
    slot_duration: int = 30,
) -> Dict[str, Any]:
    """Find free slots returning structured data."""
    result_str = await find_free_slots(start_date, end_date, calendar_name, slot_duration)
    try:
        return json.loads(result_str)
    except json.JSONDecodeError:
        return {"status": "error", "message": "Failed to parse free slots response", "free_slots": []}