from __future__ import annotations

"""Pydantic models for calendar tool operations and responses."""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel


class CalendarOperation(BaseModel):
    """Input model for calendar operations."""
    operation: str  # "list", "create", "update", "delete", "find_free_slots"
    calendar_name: Optional[str] = "Calendar"
    event_data: Optional[Dict[str, Any]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    event_id: Optional[str] = None


class CalendarResponse(BaseModel):
    """Standard response wrapper for calendar operations."""
    result: str
