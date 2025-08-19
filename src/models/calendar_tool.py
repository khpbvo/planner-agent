from __future__ import annotations
from typing import Optional, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class CalendarEventData(BaseModel):
    """Minimal event data required for calendar operations"""
    summary: str = Field(..., description="Event title/summary")
    start_date: datetime = Field(..., description="Event start in ISO format")
    end_date: datetime = Field(..., description="Event end in ISO format")
    description: Optional[str] = Field(None, description="Event description")
    location: Optional[str] = Field(None, description="Event location")
    all_day: bool = Field(False, description="Is this an all-day event")

    model_config = {"extra": "forbid"}


class CalendarOperation(BaseModel):
    """Input for calendar operations"""
    operation: str
    calendar_name: Optional[str] = "Calendar"
    event_data: Optional[CalendarEventData] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    event_id: Optional[str] = None


class CalendarResponse(BaseModel):
    """Structured response from calendar operations"""
    status: str
    message: Optional[str] = None
    events: Optional[List[Any]] = None
    event: Optional[Any] = None
    free_slots: Optional[List[Any]] = None
    total_free_slots: Optional[int] = None
    error: Optional[str] = None
