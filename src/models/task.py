"""
Task models for Todoist and general task management
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, Field, field_validator
import pytz


class TaskPriority(str, Enum):
    """Task priority levels"""
    URGENT = "p1"  # Todoist P1
    HIGH = "p2"    # Todoist P2
    MEDIUM = "p3"  # Todoist P3
    LOW = "p4"     # Todoist P4
    NONE = "p5"    # No priority


class TaskStatus(str, Enum):
    """Task completion status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DEFERRED = "deferred"


class Task(BaseModel):
    """Generic task model"""
    id: Optional[str] = None
    title: str = Field(..., description="Task title/content")
    description: Optional[str] = Field(None, description="Detailed task description")
    due_date: Optional[datetime] = Field(None, description="Task due date and time")
    priority: TaskPriority = Field(TaskPriority.NONE, description="Task priority")
    status: TaskStatus = Field(TaskStatus.PENDING, description="Task status")
    labels: List[str] = Field(default_factory=list, description="Task labels/tags")
    project: Optional[str] = Field(None, description="Associated project")
    estimated_duration: Optional[int] = Field(None, description="Estimated duration in minutes")
    actual_duration: Optional[int] = Field(None, description="Actual duration in minutes")
    created_at: datetime = Field(default_factory=lambda: datetime.now(pytz.UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(pytz.UTC))
    completed_at: Optional[datetime] = None
    
    @field_validator('due_date')
    def validate_due_date(cls, v):
        """Ensure due date is timezone-aware"""
        if v and v.tzinfo is None:
            return v.replace(tzinfo=pytz.UTC)
        return v
    
    def to_natural_language(self) -> str:
        """Convert task to natural language description"""
        parts = [f"Task: {self.title}"]
        
        if self.description:
            parts.append(f"Description: {self.description}")
        
        if self.due_date:
            parts.append(f"Due: {self.due_date.strftime('%Y-%m-%d %H:%M')}")
            
        if self.priority != TaskPriority.NONE:
            parts.append(f"Priority: {self.priority.value}")
            
        if self.labels:
            parts.append(f"Labels: {', '.join(self.labels)}")
            
        return " | ".join(parts)


class TodoistTask(Task):
    """Todoist-specific task model"""
    todoist_id: Optional[str] = Field(None, description="Todoist task ID")
    todoist_project_id: Optional[str] = Field(None, description="Todoist project ID")
    todoist_section_id: Optional[str] = Field(None, description="Todoist section ID")
    todoist_parent_id: Optional[str] = Field(None, description="Parent task ID for subtasks")
    todoist_order: Optional[int] = Field(None, description="Task order in project")
    todoist_comment_count: int = Field(0, description="Number of comments")
    todoist_is_completed: bool = Field(False, description="Completion status in Todoist")
    todoist_url: Optional[str] = Field(None, description="Todoist task URL")
    assignee_id: Optional[str] = Field(None, description="Assigned user ID")
    
    def to_todoist_payload(self) -> Dict[str, Any]:
        """Convert to Todoist API payload"""
        payload = {
            "content": self.title,
            "priority": int(self.priority.value[-1]) if self.priority != TaskPriority.NONE else 1,
        }
        
        if self.description:
            payload["description"] = self.description
            
        if self.due_date:
            payload["due_datetime"] = self.due_date.isoformat()
            
        if self.labels:
            payload["labels"] = self.labels
            
        if self.todoist_project_id:
            payload["project_id"] = self.todoist_project_id
            
        if self.todoist_section_id:
            payload["section_id"] = self.todoist_section_id
            
        if self.todoist_parent_id:
            payload["parent_id"] = self.todoist_parent_id
            
        return payload
    
    @classmethod
    def from_todoist_response(cls, data: Dict[str, Any]) -> "TodoistTask":
        """Create from Todoist API response"""
        priority_map = {
            1: TaskPriority.LOW,
            2: TaskPriority.MEDIUM,
            3: TaskPriority.HIGH,
            4: TaskPriority.URGENT,
        }
        
        due_date = None
        if data.get("due"):
            due_str = data["due"].get("datetime") or data["due"].get("date")
            if due_str:
                due_date = datetime.fromisoformat(due_str.replace("Z", "+00:00"))
        
        return cls(
            todoist_id=data.get("id"),
            title=data.get("content", ""),
            description=data.get("description"),
            due_date=due_date,
            priority=priority_map.get(data.get("priority", 1), TaskPriority.NONE),
            status=TaskStatus.COMPLETED if data.get("is_completed") else TaskStatus.PENDING,
            labels=data.get("labels", []),
            todoist_project_id=data.get("project_id"),
            todoist_section_id=data.get("section_id"),
            todoist_parent_id=data.get("parent_id"),
            todoist_order=data.get("order"),
            todoist_comment_count=data.get("comment_count", 0),
            todoist_is_completed=data.get("is_completed", False),
            todoist_url=data.get("url"),
            assignee_id=data.get("assignee_id"),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now(pytz.UTC).isoformat())),
        )