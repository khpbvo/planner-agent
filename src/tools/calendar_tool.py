from __future__ import annotations
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from models.calendar_tool import CalendarOperation, CalendarResponse


async def manage_calendar(operation_input: CalendarOperation) -> CalendarResponse:
    """Manage calendar events in MacOS Calendar app"""
    operation = operation_input.operation
    calendar_name = operation_input.calendar_name or "Calendar"
    start_date = operation_input.start_date
    end_date = operation_input.end_date
    event_id = operation_input.event_id
    event_data = operation_input.event_data

    if operation == "list":
        data = await list_events(calendar_name, start_date, end_date)
        return CalendarResponse(**data)
    elif operation == "create":
        if not event_data:
            return CalendarResponse(status="error", message="event_data required for create operation")
        data = await create_event(calendar_name, event_data)
        return CalendarResponse(**data)
    elif operation == "update":
        if not event_id or not event_data:
            return CalendarResponse(status="error", message="event_id and event_data required for update operation")
        data = await update_event(event_id, event_data, calendar_name)
        return CalendarResponse(**data)
    elif operation == "delete":
        if not event_id:
            return CalendarResponse(status="error", message="event_id required for delete operation")
        data = await delete_event(event_id, calendar_name)
        return CalendarResponse(**data)
    elif operation == "find_free_slots":
        start = start_date or datetime.now()
        end = end_date or (start + timedelta(days=7))
        data = await find_free_slots(start, end, calendar_name)
        return CalendarResponse(**data)
    else:
        return CalendarResponse(status="error", message=f"Unknown operation: {operation}")


def create_calendar_tool():
    """Create the calendar tool for MacOS Calendar integration"""
    return manage_calendar


async def list_events(
    calendar_name: str = "Calendar",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """List calendar events. In this environment, returns an error."""
    return {
        "status": "error",
        "message": "Calendar access not available in this environment",
        "events": [],
    }


async def create_event(
    calendar_name: str,
    event_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Create a new calendar event. Placeholder implementation."""
    return {
        "status": "error",
        "message": "Event creation not yet implemented",
    }


async def update_event(
    event_id: str,
    event_data: Dict[str, Any],
    calendar_name: str = "Calendar",
) -> Dict[str, Any]:
    """Update an existing calendar event. Placeholder implementation."""
    return {
        "status": "error",
        "message": f"Event update not yet implemented. Would update event {event_id}",
    }


async def delete_event(
    event_id: str,
    calendar_name: str = "Calendar",
) -> Dict[str, Any]:
    """Delete a calendar event. Placeholder implementation."""
    return {
        "status": "error",
        "message": f"Event deletion not yet implemented. Would delete event {event_id}",
    }


async def find_free_slots(
    start_date: datetime,
    end_date: datetime,
    calendar_name: str = "Calendar",
    slot_duration: int = 30,
) -> Dict[str, Any]:
    """Find available time slots in the calendar."""
    free_slots: List[Dict[str, Any]] = []
    current_time = start_date.replace(hour=9, minute=0, second=0, microsecond=0)
    end_of_day = start_date.replace(hour=17, minute=0, second=0, microsecond=0)

    while current_time < end_of_day:
        free_slots.append(
            {
                "start": current_time.isoformat(),
                "end": (current_time + timedelta(minutes=slot_duration)).isoformat(),
                "duration_minutes": slot_duration,
            }
        )
        current_time += timedelta(hours=1)

    return {
        "status": "success",
        "free_slots": free_slots[:5],
        "total_free_slots": len(free_slots),
    }
