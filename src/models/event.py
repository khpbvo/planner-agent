"""
Calendar event models for MacOS Calendar and general event management
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, field_validator
import pytz


class EventRecurrence(str, Enum):
    """Event recurrence patterns"""
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    WEEKDAYS = "weekdays"
    CUSTOM = "custom"


class EventReminder(BaseModel):
    """Event reminder configuration"""
    minutes_before: int = Field(..., description="Minutes before event to remind")
    method: str = Field("alert", description="Reminder method (alert, email, etc.)")
    
    def to_natural_language(self) -> str:
        """Convert reminder to natural language"""
        if self.minutes_before < 60:
            return f"{self.minutes_before} minutes before"
        elif self.minutes_before < 1440:
            hours = self.minutes_before // 60
            return f"{hours} hour{'s' if hours > 1 else ''} before"
        else:
            days = self.minutes_before // 1440
            return f"{days} day{'s' if days > 1 else ''} before"


class CalendarEvent(BaseModel):
    """Calendar event model"""
    id: Optional[str] = None
    title: str = Field(..., description="Event title")
    description: Optional[str] = Field(None, description="Event description/notes")
    location: Optional[str] = Field(None, description="Event location")
    start_time: datetime = Field(..., description="Event start time")
    end_time: datetime = Field(..., description="Event end time")
    all_day: bool = Field(False, description="Is this an all-day event")
    calendar_name: Optional[str] = Field(None, description="Calendar name")
    attendees: List[str] = Field(default_factory=list, description="List of attendee emails")
    reminders: List[EventReminder] = Field(default_factory=list, description="Event reminders")
    recurrence: EventRecurrence = Field(EventRecurrence.NONE, description="Recurrence pattern")
    recurrence_end: Optional[datetime] = Field(None, description="End date for recurring events")
    color: Optional[str] = Field(None, description="Event color/category")
    url: Optional[str] = Field(None, description="Associated URL")
    busy_status: str = Field("busy", description="Free/busy status")
    created_at: datetime = Field(default_factory=lambda: datetime.now(pytz.UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(pytz.UTC))
    
    @field_validator('start_time', 'end_time')
    def validate_times(cls, v):
        """Ensure times are timezone-aware"""
        if v and v.tzinfo is None:
            return v.replace(tzinfo=pytz.UTC)
        return v
    
    @field_validator('end_time')
    def validate_end_after_start(cls, v, values):
        """Ensure end time is after start time"""
        if 'start_time' in values.data and v <= values.data['start_time']:
            raise ValueError("End time must be after start time")
        return v
    
    @property
    def duration(self) -> timedelta:
        """Calculate event duration"""
        return self.end_time - self.start_time
    
    @property
    def duration_minutes(self) -> int:
        """Get duration in minutes"""
        return int(self.duration.total_seconds() / 60)
    
    def to_natural_language(self) -> str:
        """Convert event to natural language description"""
        parts = [f"Event: {self.title}"]
        
        if self.all_day:
            parts.append(f"Date: {self.start_time.strftime('%Y-%m-%d')} (all day)")
        else:
            parts.append(f"Time: {self.start_time.strftime('%Y-%m-%d %H:%M')} - {self.end_time.strftime('%H:%M')}")
        
        if self.location:
            parts.append(f"Location: {self.location}")
            
        if self.attendees:
            parts.append(f"Attendees: {', '.join(self.attendees)}")
            
        if self.recurrence != EventRecurrence.NONE:
            parts.append(f"Recurrence: {self.recurrence.value}")
            
        return " | ".join(parts)
    
    def to_ics_format(self) -> str:
        """Convert to basic ICS format for calendar apps"""
        ics_lines = [
            "BEGIN:VEVENT",
            f"UID:{self.id or datetime.now().timestamp()}",
            f"DTSTART:{self.start_time.strftime('%Y%m%dT%H%M%SZ')}",
            f"DTEND:{self.end_time.strftime('%Y%m%dT%H%M%SZ')}",
            f"SUMMARY:{self.title}",
        ]
        
        if self.description:
            ics_lines.append(f"DESCRIPTION:{self.description}")
            
        if self.location:
            ics_lines.append(f"LOCATION:{self.location}")
            
        for attendee in self.attendees:
            ics_lines.append(f"ATTENDEE:mailto:{attendee}")
            
        ics_lines.append("END:VEVENT")
        
        return "\n".join(ics_lines)
    
    def to_applescript_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for AppleScript creation"""
        return {
            "summary": self.title,
            "start_date": self.start_time.isoformat(),
            "end_date": self.end_time.isoformat(),
            "description": self.description or "",
            "location": self.location or "",
            "all_day": self.all_day,
        }
    
    def conflicts_with(self, other: "CalendarEvent") -> bool:
        """Check if this event conflicts with another event"""
        if self.all_day or other.all_day:
            # For all-day events, check if they're on the same day
            return self.start_time.date() == other.start_time.date()
        
        # Check for time overlap
        return not (self.end_time <= other.start_time or self.start_time >= other.end_time)