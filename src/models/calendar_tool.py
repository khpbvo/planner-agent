from __future__ import annotations
from typing import Optional, Any, List
from datetime import datetime
from pydantic import BaseModel


class CalendarOperation(BaseModel):
    """Input for calendar operations"""
    operation: str
    calendar_name: Optional[str] = "Calendar"
    event_data: Optional[Any] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    event_id: Optional[str] = None


class CalendarResponse(BaseModel):
    """Structured response from calendar operations"""
    result: str
