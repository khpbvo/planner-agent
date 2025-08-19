"""
Advanced tracing and monitoring system for the Planning Assistant

Provides detailed tracking of agent interactions, tool calls, handoffs,
and performance metrics using OpenTelemetry standards.
"""
import time
import json
import uuid
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import threading
import logging
from contextlib import contextmanager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TraceEventType(str, Enum):
    """Types of trace events"""
    CONVERSATION_START = "conversation_start"
    CONVERSATION_END = "conversation_end"
    AGENT_CALL = "agent_call"
    TOOL_CALL = "tool_call"
    HANDOFF = "handoff"
    ERROR = "error"
    PERFORMANCE = "performance"
    USER_INPUT = "user_input"
    SYSTEM_OUTPUT = "system_output"


class TraceLevel(str, Enum):
    """Trace detail levels"""
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


@dataclass
class TraceEvent:
    """A single trace event"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    event_type: TraceEventType = TraceEventType.AGENT_CALL
    level: TraceLevel = TraceLevel.INFO
    agent_name: Optional[str] = None
    tool_name: Optional[str] = None
    session_id: Optional[str] = None
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    duration_ms: Optional[float] = None
    parent_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "level": self.level,
            "agent_name": self.agent_name,
            "tool_name": self.tool_name,
            "session_id": self.session_id,
            "message": self.message,
            "data": self.data,
            "duration_ms": self.duration_ms,
            "parent_id": self.parent_id,
            "tags": self.tags
        }


@dataclass
class ConversationTrace:
    """Complete trace of a conversation"""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    events: List[TraceEvent] = field(default_factory=list)
    user_id: Optional[str] = None
    total_duration_ms: Optional[float] = None
    total_tokens: Optional[int] = None
    success: bool = True
    error_count: int = 0
    
    def add_event(self, event: TraceEvent):
        """Add an event to this conversation trace"""
        event.session_id = self.session_id
        self.events.append(event)
        
        if event.level == TraceLevel.ERROR:
            self.error_count += 1
            self.success = False
    
    def end_conversation(self):
        """Mark conversation as ended"""
        self.end_time = datetime.now()
        self.total_duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
    
    def get_agent_usage(self) -> Dict[str, int]:
        """Get agent usage statistics"""
        usage = {}
        for event in self.events:
            if event.agent_name and event.event_type == TraceEventType.AGENT_CALL:
                usage[event.agent_name] = usage.get(event.agent_name, 0) + 1
        return usage
    
    def get_tool_usage(self) -> Dict[str, int]:
        """Get tool usage statistics"""
        usage = {}
        for event in self.events:
            if event.tool_name and event.event_type == TraceEventType.TOOL_CALL:
                usage[event.tool_name] = usage.get(event.tool_name, 0) + 1
        return usage
    
    def get_handoff_count(self) -> int:
        """Get number of handoffs in this conversation"""
        return len([e for e in self.events if e.event_type == TraceEventType.HANDOFF])


class PerformanceMetrics:
    """Performance metrics collector"""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self.counters: Dict[str, int] = {}
        self.lock = threading.Lock()
    
    def record_duration(self, metric_name: str, duration_ms: float):
        """Record a duration metric"""
        with self.lock:
            if metric_name not in self.metrics:
                self.metrics[metric_name] = []
            self.metrics[metric_name].append(duration_ms)
    
    def increment_counter(self, counter_name: str):
        """Increment a counter metric"""
        with self.lock:
            self.counters[counter_name] = self.counters.get(counter_name, 0) + 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        with self.lock:
            stats = {"counters": self.counters.copy()}
            
            for metric_name, values in self.metrics.items():
                if values:
                    stats[metric_name] = {
                        "count": len(values),
                        "avg_ms": sum(values) / len(values),
                        "min_ms": min(values),
                        "max_ms": max(values),
                        "total_ms": sum(values)
                    }
            
            return stats


class PlanningTracer:
    """Main tracing system for the Planning Assistant"""
    
    def __init__(self, 
                 trace_level: TraceLevel = TraceLevel.INFO,
                 log_to_file: bool = True,
                 trace_dir: str = "data/traces"):
        self.trace_level = trace_level
        self.log_to_file = log_to_file
        self.trace_dir = Path(trace_dir)
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        
        # Storage
        self.active_conversations: Dict[str, ConversationTrace] = {}
        self.completed_conversations: List[ConversationTrace] = []
        self.performance_metrics = PerformanceMetrics()
        
        # Threading
        self.lock = threading.Lock()
        
        # Current context
        self._current_context: Dict[str, Any] = {}
    
    def start_conversation(self, 
                         session_id: str, 
                         user_id: Optional[str] = None) -> ConversationTrace:
        """Start tracing a new conversation"""
        with self.lock:
            conversation = ConversationTrace(
                session_id=session_id,
                start_time=datetime.now(),
                user_id=user_id
            )
            
            self.active_conversations[session_id] = conversation
            
            # Log start event
            start_event = TraceEvent(
                event_type=TraceEventType.CONVERSATION_START,
                level=TraceLevel.INFO,
                session_id=session_id,
                message=f"Started conversation {session_id}",
                data={"user_id": user_id}
            )
            conversation.add_event(start_event)
            
            self._log_event(start_event)
            return conversation
    
    def end_conversation(self, session_id: str):
        """End tracing for a conversation"""
        with self.lock:
            if session_id in self.active_conversations:
                conversation = self.active_conversations[session_id]
                conversation.end_conversation()
                
                # Log end event
                end_event = TraceEvent(
                    event_type=TraceEventType.CONVERSATION_END,
                    level=TraceLevel.INFO,
                    session_id=session_id,
                    message=f"Ended conversation {session_id}",
                    data={
                        "duration_ms": conversation.total_duration_ms,
                        "event_count": len(conversation.events),
                        "success": conversation.success,
                        "error_count": conversation.error_count
                    }
                )
                conversation.add_event(end_event)
                self._log_event(end_event)
                
                # Move to completed
                self.completed_conversations.append(conversation)
                del self.active_conversations[session_id]
                
                # Save trace file
                if self.log_to_file:
                    self._save_conversation_trace(conversation)
    
    def trace_agent_call(self, 
                        agent_name: str, 
                        message: str,
                        session_id: Optional[str] = None,
                        parent_id: Optional[str] = None) -> str:
        """Trace an agent call"""
        event = TraceEvent(
            event_type=TraceEventType.AGENT_CALL,
            level=TraceLevel.INFO,
            agent_name=agent_name,
            session_id=session_id,
            message=f"Agent call: {agent_name}",
            data={"input_message": message},
            parent_id=parent_id
        )
        
        self._add_event(event)
        self.performance_metrics.increment_counter(f"agent_calls_{agent_name}")
        return event.id
    
    def trace_tool_call(self, 
                       tool_name: str, 
                       input_data: Dict[str, Any],
                       session_id: Optional[str] = None,
                       parent_id: Optional[str] = None) -> str:
        """Trace a tool call"""
        event = TraceEvent(
            event_type=TraceEventType.TOOL_CALL,
            level=TraceLevel.DEBUG,
            tool_name=tool_name,
            session_id=session_id,
            message=f"Tool call: {tool_name}",
            data={"input": input_data},
            parent_id=parent_id
        )
        
        self._add_event(event)
        self.performance_metrics.increment_counter(f"tool_calls_{tool_name}")
        return event.id
    
    def trace_handoff(self, 
                     from_agent: str, 
                     to_agent: str, 
                     reason: str,
                     session_id: Optional[str] = None,
                     parent_id: Optional[str] = None) -> str:
        """Trace an agent handoff"""
        event = TraceEvent(
            event_type=TraceEventType.HANDOFF,
            level=TraceLevel.INFO,
            agent_name=to_agent,
            session_id=session_id,
            message=f"Handoff: {from_agent} → {to_agent}",
            data={
                "from_agent": from_agent,
                "to_agent": to_agent,
                "reason": reason
            },
            parent_id=parent_id,
            tags=["handoff"]
        )
        
        self._add_event(event)
        self.performance_metrics.increment_counter("total_handoffs")
        return event.id
    
    def trace_error(self, 
                   error: Exception, 
                   context: Dict[str, Any],
                   session_id: Optional[str] = None,
                   parent_id: Optional[str] = None) -> str:
        """Trace an error"""
        event = TraceEvent(
            event_type=TraceEventType.ERROR,
            level=TraceLevel.ERROR,
            session_id=session_id,
            message=f"Error: {str(error)}",
            data={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context
            },
            parent_id=parent_id,
            tags=["error"]
        )
        
        self._add_event(event)
        self.performance_metrics.increment_counter("total_errors")
        return event.id
    
    @contextmanager
    def trace_operation(self, 
                       operation_name: str, 
                       session_id: Optional[str] = None,
                       parent_id: Optional[str] = None):
        """Context manager for tracing operations with timing"""
        start_time = time.time()
        event_id = None
        
        try:
            event = TraceEvent(
                event_type=TraceEventType.PERFORMANCE,
                level=TraceLevel.DEBUG,
                session_id=session_id,
                message=f"Started: {operation_name}",
                data={"operation": operation_name},
                parent_id=parent_id
            )
            event_id = event.id
            self._add_event(event)
            
            yield event_id
            
        except Exception as e:
            self.trace_error(e, {"operation": operation_name}, session_id, parent_id)
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            
            if event_id:
                # Update the original event with duration
                self._update_event_duration(event_id, duration_ms)
            
            self.performance_metrics.record_duration(operation_name, duration_ms)
    
    def get_conversation_analytics(self, session_id: str) -> Dict[str, Any]:
        """Get analytics for a specific conversation"""
        conversation = None
        
        # Check active conversations
        if session_id in self.active_conversations:
            conversation = self.active_conversations[session_id]
        else:
            # Check completed conversations
            for conv in self.completed_conversations:
                if conv.session_id == session_id:
                    conversation = conv
                    break
        
        if not conversation:
            return {"error": "Conversation not found"}
        
        return {
            "session_id": session_id,
            "start_time": conversation.start_time.isoformat(),
            "end_time": conversation.end_time.isoformat() if conversation.end_time else None,
            "duration_ms": conversation.total_duration_ms,
            "event_count": len(conversation.events),
            "success": conversation.success,
            "error_count": conversation.error_count,
            "agent_usage": conversation.get_agent_usage(),
            "tool_usage": conversation.get_tool_usage(),
            "handoff_count": conversation.get_handoff_count()
        }
    
    def get_system_analytics(self) -> Dict[str, Any]:
        """Get overall system analytics"""
        total_conversations = len(self.completed_conversations) + len(self.active_conversations)
        successful_conversations = len([c for c in self.completed_conversations if c.success])
        
        # Aggregate agent usage across all conversations
        all_agent_usage = {}
        all_tool_usage = {}
        total_handoffs = 0
        
        for conv in self.completed_conversations:
            for agent, count in conv.get_agent_usage().items():
                all_agent_usage[agent] = all_agent_usage.get(agent, 0) + count
            
            for tool, count in conv.get_tool_usage().items():
                all_tool_usage[tool] = all_tool_usage.get(tool, 0) + count
                
            total_handoffs += conv.get_handoff_count()
        
        return {
            "total_conversations": total_conversations,
            "active_conversations": len(self.active_conversations),
            "completed_conversations": len(self.completed_conversations),
            "success_rate": successful_conversations / max(len(self.completed_conversations), 1),
            "agent_usage": all_agent_usage,
            "tool_usage": all_tool_usage,
            "total_handoffs": total_handoffs,
            "performance_metrics": self.performance_metrics.get_stats()
        }
    
    def _add_event(self, event: TraceEvent):
        """Add event to appropriate conversation"""
        if event.session_id and event.session_id in self.active_conversations:
            self.active_conversations[event.session_id].add_event(event)
        
        self._log_event(event)

    # Public factory for creating events (used by monitoring wrappers)
    def create_event(self, **kwargs) -> TraceEvent:
        return TraceEvent(**kwargs)
    
    def _update_event_duration(self, event_id: str, duration_ms: float):
        """Update event with duration"""
        for conversation in self.active_conversations.values():
            for event in conversation.events:
                if event.id == event_id:
                    event.duration_ms = duration_ms
                    event.data["duration_ms"] = duration_ms
                    return
    
    def _log_event(self, event: TraceEvent):
        """Log event to console/file"""
        if self._should_log_level(event.level):
            log_message = f"[{event.timestamp.isoformat()}] {event.level.upper()}: {event.message}"
            
            if event.agent_name:
                log_message += f" (Agent: {event.agent_name})"
            if event.tool_name:
                log_message += f" (Tool: {event.tool_name})"
            
            logger.log(self._get_log_level(event.level), log_message)
    
    def _should_log_level(self, level: TraceLevel) -> bool:
        """Check if should log this level"""
        level_order = {
            TraceLevel.DEBUG: 0,
            TraceLevel.INFO: 1,
            TraceLevel.WARN: 2,
            TraceLevel.ERROR: 3
        }
        return level_order[level] >= level_order[self.trace_level]
    
    def _get_log_level(self, trace_level: TraceLevel) -> int:
        """Convert trace level to logging level"""
        mapping = {
            TraceLevel.DEBUG: logging.DEBUG,
            TraceLevel.INFO: logging.INFO,
            TraceLevel.WARN: logging.WARNING,
            TraceLevel.ERROR: logging.ERROR
        }
        return mapping[trace_level]
    
    def _save_conversation_trace(self, conversation: ConversationTrace):
        """Save conversation trace to file"""
        try:
            trace_file = self.trace_dir / f"trace_{conversation.session_id}_{conversation.start_time.strftime('%Y%m%d_%H%M%S')}.json"
            
            trace_data = {
                "session_id": conversation.session_id,
                "start_time": conversation.start_time.isoformat(),
                "end_time": conversation.end_time.isoformat() if conversation.end_time else None,
                "duration_ms": conversation.total_duration_ms,
                "success": conversation.success,
                "error_count": conversation.error_count,
                "events": [event.to_dict() for event in conversation.events]
            }
            
            with open(trace_file, 'w') as f:
                json.dump(trace_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save trace file: {e}")


# Global tracer instance
_tracer: Optional[PlanningTracer] = None


def get_tracer() -> PlanningTracer:
    """Get the global tracer instance"""
    global _tracer
    if _tracer is None:
        _tracer = PlanningTracer()
    return _tracer


def init_tracer(trace_level: TraceLevel = TraceLevel.INFO, 
               log_to_file: bool = True,
               trace_dir: str = "data/traces") -> PlanningTracer:
    """Initialize the global tracer"""
    global _tracer
    _tracer = PlanningTracer(trace_level, log_to_file, trace_dir)
    return _tracer