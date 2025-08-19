"""
Agent monitoring integration for the Planning Assistant

Provides decorators and utilities to automatically trace agent operations,
tool calls, and system performance without code changes to existing agents.
"""
import functools
import asyncio
from typing import Any, Callable, Dict, Optional, TypeVar, Union
from datetime import datetime
import inspect
import json

from tracer import get_tracer, TraceEventType, TraceLevel

F = TypeVar('F', bound=Callable[..., Any])


class AgentMonitor:
    """Monitoring wrapper for agents and tools"""
    
    def __init__(self, tracer=None):
        self.tracer = tracer or get_tracer()
        self.active_operations: Dict[str, str] = {}  # operation_name -> trace_id
    
    def trace_agent(self, agent_name: str, session_id: Optional[str] = None):
        """Decorator to trace agent method calls"""
        def decorator(func: F) -> F:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Extract message if it's the first argument
                message = str(args[0]) if args else "Unknown message"
                
                with self.tracer.trace_operation(f"agent_{agent_name}", session_id) as trace_id:
                    agent_trace_id = self.tracer.trace_agent_call(
                        agent_name=agent_name,
                        message=message,
                        session_id=session_id,
                        parent_id=trace_id
                    )
                    
                    try:
                        result = await func(*args, **kwargs)
                        
                        # Log successful completion
                        self.tracer._add_event(self.tracer.create_event(
                            event_type=TraceEventType.AGENT_CALL,
                            level=TraceLevel.INFO,
                            agent_name=agent_name,
                            session_id=session_id,
                            message=f"Agent {agent_name} completed successfully",
                            data={"result_length": len(str(result))},
                            parent_id=agent_trace_id
                        ))
                        
                        return result
                        
                    except Exception as e:
                        self.tracer.trace_error(
                            error=e,
                            context={"agent": agent_name, "message": message},
                            session_id=session_id,
                            parent_id=agent_trace_id
                        )
                        raise
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Extract message if it's the first argument
                message = str(args[0]) if args else "Unknown message"
                
                with self.tracer.trace_operation(f"agent_{agent_name}", session_id) as trace_id:
                    agent_trace_id = self.tracer.trace_agent_call(
                        agent_name=agent_name,
                        message=message,
                        session_id=session_id,
                        parent_id=trace_id
                    )
                    
                    try:
                        result = func(*args, **kwargs)
                        
                        # Log successful completion
                        self.tracer._add_event(self.tracer.create_event(
                            event_type=TraceEventType.AGENT_CALL,
                            level=TraceLevel.INFO,
                            agent_name=agent_name,
                            session_id=session_id,
                            message=f"Agent {agent_name} completed successfully",
                            data={"result_length": len(str(result))},
                            parent_id=agent_trace_id
                        ))
                        
                        return result
                        
                    except Exception as e:
                        self.tracer.trace_error(
                            error=e,
                            context={"agent": agent_name, "message": message},
                            session_id=session_id,
                            parent_id=agent_trace_id
                        )
                        raise
            
            # Return appropriate wrapper based on function type
            if inspect.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    def trace_tool(self, tool_name: str, session_id: Optional[str] = None):
        """Decorator to trace tool function calls"""
        def decorator(func: F) -> F:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Extract input data from first argument if it's a Pydantic model
                input_data = {}
                if args:
                    first_arg = args[0]
                    if hasattr(first_arg, 'model_dump'):
                        input_data = first_arg.model_dump()
                    elif hasattr(first_arg, 'dict'):
                        input_data = first_arg.dict()
                    else:
                        input_data = {"input": str(first_arg)}
                
                with self.tracer.trace_operation(f"tool_{tool_name}", session_id) as trace_id:
                    tool_trace_id = self.tracer.trace_tool_call(
                        tool_name=tool_name,
                        input_data=input_data,
                        session_id=session_id,
                        parent_id=trace_id
                    )
                    
                    try:
                        result = await func(*args, **kwargs)
                        
                        # Parse result if it's JSON
                        result_data = {}
                        try:
                            if isinstance(result, str):
                                parsed = json.loads(result)
                                result_data = {
                                    "status": parsed.get("status", "unknown"),
                                    "message": parsed.get("message", "")[:100]  # First 100 chars
                                }
                        except:
                            result_data = {"result_length": len(str(result))}
                        
                        # Log successful completion
                        self.tracer._add_event(self.tracer.create_event(
                            event_type=TraceEventType.TOOL_CALL,
                            level=TraceLevel.DEBUG,
                            tool_name=tool_name,
                            session_id=session_id,
                            message=f"Tool {tool_name} completed successfully",
                            data=result_data,
                            parent_id=tool_trace_id
                        ))
                        
                        return result
                        
                    except Exception as e:
                        self.tracer.trace_error(
                            error=e,
                            context={"tool": tool_name, "input": input_data},
                            session_id=session_id,
                            parent_id=tool_trace_id
                        )
                        raise
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Extract input data from first argument if it's a Pydantic model
                input_data = {}
                if args:
                    first_arg = args[0]
                    if hasattr(first_arg, 'model_dump'):
                        input_data = first_arg.model_dump()
                    elif hasattr(first_arg, 'dict'):
                        input_data = first_arg.dict()
                    else:
                        input_data = {"input": str(first_arg)}
                
                with self.tracer.trace_operation(f"tool_{tool_name}", session_id) as trace_id:
                    tool_trace_id = self.tracer.trace_tool_call(
                        tool_name=tool_name,
                        input_data=input_data,
                        session_id=session_id,
                        parent_id=trace_id
                    )
                    
                    try:
                        result = func(*args, **kwargs)
                        
                        # Parse result if it's JSON
                        result_data = {}
                        try:
                            if isinstance(result, str):
                                parsed = json.loads(result)
                                result_data = {
                                    "status": parsed.get("status", "unknown"),
                                    "message": parsed.get("message", "")[:100]  # First 100 chars
                                }
                        except:
                            result_data = {"result_length": len(str(result))}
                        
                        # Log successful completion
                        self.tracer._add_event(self.tracer.create_event(
                            event_type=TraceEventType.TOOL_CALL,
                            level=TraceLevel.DEBUG,
                            tool_name=tool_name,
                            session_id=session_id,
                            message=f"Tool {tool_name} completed successfully",
                            data=result_data,
                            parent_id=tool_trace_id
                        ))
                        
                        return result
                        
                    except Exception as e:
                        self.tracer.trace_error(
                            error=e,
                            context={"tool": tool_name, "input": input_data},
                            session_id=session_id,
                            parent_id=tool_trace_id
                        )
                        raise
            
            # Return appropriate wrapper based on function type
            if inspect.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    def trace_handoff(self, from_agent: str, to_agent: str, reason: str, session_id: Optional[str] = None) -> str:
        """Trace an agent handoff"""
        return self.tracer.trace_handoff(from_agent, to_agent, reason, session_id)
    
    def get_active_operations(self) -> Dict[str, Any]:
        """Get currently active operations"""
        return {
            "active_count": len(self.active_operations),
            "operations": list(self.active_operations.keys())
        }


# Global monitor instance
_monitor: Optional[AgentMonitor] = None


def get_monitor() -> AgentMonitor:
    """Get the global agent monitor instance"""
    global _monitor
    if _monitor is None:
        _monitor = AgentMonitor()
    return _monitor


def init_monitor(tracer=None) -> AgentMonitor:
    """Initialize the global agent monitor"""
    global _monitor
    _monitor = AgentMonitor(tracer)
    return _monitor


# Convenience decorators using global monitor
def trace_agent(agent_name: str, session_id: Optional[str] = None):
    """Convenience decorator for tracing agent calls"""
    return get_monitor().trace_agent(agent_name, session_id)


def trace_tool(tool_name: str, session_id: Optional[str] = None):
    """Convenience decorator for tracing tool calls"""
    return get_monitor().trace_tool(tool_name, session_id)


class MonitoringMixin:
    """Mixin class to add monitoring to any class"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.monitor = get_monitor()
        self.session_id = kwargs.get('session_id')
    
    def trace_method(self, method_name: str, *args, **kwargs):
        """Trace a method call"""
        with self.monitor.tracer.trace_operation(f"{self.__class__.__name__}.{method_name}", self.session_id):
            return getattr(super(), method_name)(*args, **kwargs)


# Ensure tracer instances have a helper to create TraceEvent instances
try:
    tracer_cls = get_tracer().__class__
    if not hasattr(tracer_cls, "_create_event"):
        from tracer import TraceEvent as _TraceEvent

        def _create_event(self, **kwargs):
            return _TraceEvent(**kwargs)

        setattr(tracer_cls, "_create_event", _create_event)
except Exception:
    # Non-fatal; creating events is best-effort for richer logs
    pass