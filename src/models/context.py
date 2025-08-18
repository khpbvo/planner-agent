"""
Context models for managing agent state and extracted entities
"""
from typing import Optional, List, Dict, Any, Set
from datetime import datetime, date, time, timedelta
from pydantic import BaseModel, Field
import pytz


class ExtractedEntity(BaseModel):
    """Entity extracted from natural language"""
    text: str = Field(..., description="Original text")
    label: str = Field(..., description="Entity type (PERSON, DATE, TIME, etc.)")
    normalized_value: Optional[Any] = Field(None, description="Normalized/parsed value")
    confidence: float = Field(1.0, description="Extraction confidence score")
    
    def __hash__(self):
        return hash((self.text, self.label))


class TemporalReference(BaseModel):
    """Temporal reference extracted from text"""
    original_text: str = Field(..., description="Original temporal expression")
    parsed_datetime: Optional[datetime] = Field(None, description="Parsed datetime")
    parsed_date: Optional[date] = Field(None, description="Parsed date (for date-only refs)")
    parsed_time: Optional[time] = Field(None, description="Parsed time (for time-only refs)")
    is_relative: bool = Field(False, description="Is this a relative reference (tomorrow, next week)")
    is_recurring: bool = Field(False, description="Is this a recurring reference")
    recurrence_pattern: Optional[str] = Field(None, description="Recurrence pattern if applicable")


class EntityContext(BaseModel):
    """Context from NLP entity extraction"""
    raw_text: str = Field(..., description="Original user input")
    entities: List[ExtractedEntity] = Field(default_factory=list, description="Extracted entities")
    temporal_refs: List[TemporalReference] = Field(default_factory=list, description="Temporal references")
    mentioned_projects: List[str] = Field(default_factory=list, description="Mentioned project names")
    mentioned_people: List[str] = Field(default_factory=list, description="Mentioned person names")
    mentioned_locations: List[str] = Field(default_factory=list, description="Mentioned locations")
    intent: Optional[str] = Field(None, description="Detected user intent")
    sentiment: Optional[str] = Field(None, description="Message sentiment")
    
    def get_entities_by_label(self, label: str) -> List[ExtractedEntity]:
        """Get all entities with a specific label"""
        return [e for e in self.entities if e.label == label]
    
    def get_primary_datetime(self) -> Optional[datetime]:
        """Get the most relevant datetime from temporal references"""
        for ref in self.temporal_refs:
            if ref.parsed_datetime:
                return ref.parsed_datetime
        return None
    
    def to_context_summary(self) -> str:
        """Generate a summary for agent context"""
        parts = []
        
        if self.intent:
            parts.append(f"Intent: {self.intent}")
            
        if self.temporal_refs:
            times = [ref.original_text for ref in self.temporal_refs]
            parts.append(f"Times mentioned: {', '.join(times)}")
            
        if self.mentioned_people:
            parts.append(f"People: {', '.join(self.mentioned_people)}")
            
        if self.mentioned_projects:
            parts.append(f"Projects: {', '.join(self.mentioned_projects)}")
            
        return " | ".join(parts) if parts else "No specific context extracted"


class UserPreferences(BaseModel):
    """User preferences for planning"""
    working_hours_start: time = Field(default=time(9, 0), description="Start of working hours")
    working_hours_end: time = Field(default=time(17, 0), description="End of working hours")
    preferred_meeting_duration: int = Field(default=30, description="Default meeting duration in minutes")
    buffer_between_events: int = Field(default=15, description="Buffer time between events in minutes")
    timezone: str = Field(default="UTC", description="User's timezone")
    work_days: Set[int] = Field(default_factory=lambda: {0, 1, 2, 3, 4}, description="Working days (0=Monday)")
    preferred_task_times: List[str] = Field(default_factory=list, description="Preferred times for tasks")
    avoid_scheduling_on: List[date] = Field(default_factory=list, description="Dates to avoid scheduling")
    default_calendar: Optional[str] = Field(None, description="Default calendar name")
    default_todoist_project: Optional[str] = Field(None, description="Default Todoist project")
    
    def is_working_hours(self, dt: datetime) -> bool:
        """Check if datetime is within working hours"""
        local_dt = dt.astimezone(pytz.timezone(self.timezone))
        
        # Check if it's a working day
        if local_dt.weekday() not in self.work_days:
            return False
            
        # Check if it's within working hours
        current_time = local_dt.time()
        return self.working_hours_start <= current_time <= self.working_hours_end
    
    def next_available_slot(self, duration_minutes: int, after: datetime) -> datetime:
        """Find next available time slot based on preferences"""
        # This is a simplified version - would need calendar integration for real availability
        local_dt = after.astimezone(pytz.timezone(self.timezone))
        
        # If it's already in working hours and a work day, return it
        if self.is_working_hours(local_dt):
            return local_dt
            
        # Otherwise, find next working day at start of working hours
        while True:
            local_dt = local_dt.replace(
                hour=self.working_hours_start.hour,
                minute=self.working_hours_start.minute,
                second=0,
                microsecond=0
            )
            
            if local_dt.weekday() in self.work_days and local_dt.date() not in self.avoid_scheduling_on:
                return local_dt
                
            local_dt += timedelta(days=1)


class PlanningContext(BaseModel):
    """Overall planning context for the session"""
    session_id: str = Field(..., description="Unique session identifier")
    user_preferences: UserPreferences = Field(default_factory=UserPreferences, description="User preferences")
    entity_context: Optional[EntityContext] = Field(None, description="Current entity context")
    current_focus: Optional[str] = Field(None, description="Current planning focus/goal")
    active_project: Optional[str] = Field(None, description="Currently active project")
    pending_confirmations: List[Dict[str, Any]] = Field(default_factory=list, description="Actions pending confirmation")
    recent_actions: List[Dict[str, Any]] = Field(default_factory=list, description="Recently completed actions")
    conversation_summary: Optional[str] = Field(None, description="Summary of conversation so far")
    last_sync_times: Dict[str, datetime] = Field(default_factory=dict, description="Last sync time per service")
    
    def add_pending_confirmation(self, action_type: str, details: Dict[str, Any]):
        """Add an action that needs user confirmation"""
        self.pending_confirmations.append({
            "type": action_type,
            "details": details,
            "timestamp": datetime.now(pytz.UTC),
            "id": f"{action_type}_{datetime.now().timestamp()}"
        })
    
    def confirm_action(self, action_id: str) -> Optional[Dict[str, Any]]:
        """Confirm and remove a pending action"""
        for i, action in enumerate(self.pending_confirmations):
            if action.get("id") == action_id:
                confirmed = self.pending_confirmations.pop(i)
                self.recent_actions.append(confirmed)
                return confirmed
        return None
    
    def update_sync_time(self, service: str):
        """Update last sync time for a service"""
        self.last_sync_times[service] = datetime.now(pytz.UTC)
    
    def to_agent_context(self) -> str:
        """Convert to context string for agents"""
        parts = [f"Session: {self.session_id}"]
        
        if self.current_focus:
            parts.append(f"Focus: {self.current_focus}")
            
        if self.active_project:
            parts.append(f"Active Project: {self.active_project}")
            
        if self.entity_context:
            parts.append(f"Entities: {self.entity_context.to_context_summary()}")
            
        if self.pending_confirmations:
            parts.append(f"Pending: {len(self.pending_confirmations)} actions")
            
        return " | ".join(parts)