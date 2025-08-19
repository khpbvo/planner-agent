"""
Monitoring package for the Planning Assistant

Provides comprehensive tracing, monitoring, and analytics capabilities
for the multi-agent planning system.
"""
from tracer import (
    PlanningTracer,
    TraceEvent,
    TraceEventType,
    TraceLevel,
    ConversationTrace,
    PerformanceMetrics,
    get_tracer,
    init_tracer
)

from agent_monitor import (
    AgentMonitor,
    MonitoringMixin,
    get_monitor,
    init_monitor,
    trace_agent,
    trace_tool
)

from dashboard import (
    MonitoringDashboard,
    get_dashboard
)

__all__ = [
    # Tracer components
    'PlanningTracer',
    'TraceEvent', 
    'TraceEventType',
    'TraceLevel',
    'ConversationTrace',
    'PerformanceMetrics',
    'get_tracer',
    'init_tracer',
    
    # Monitor components
    'AgentMonitor',
    'MonitoringMixin',
    'get_monitor',
    'init_monitor',
    'trace_agent',
    'trace_tool',
    
    # Dashboard
    'MonitoringDashboard',
    'get_dashboard'
]


def setup_monitoring(trace_level: str = "INFO", 
                    log_to_file: bool = True,
                    trace_dir: str = "data/traces") -> tuple:
    """
    Setup complete monitoring system
    
    Returns:
        tuple: (tracer, monitor, dashboard) instances
    """
    from tracer import TraceLevel
    
    # Convert string level to enum
    level_map = {
        "DEBUG": TraceLevel.DEBUG,
        "INFO": TraceLevel.INFO, 
        "WARN": TraceLevel.WARN,
        "ERROR": TraceLevel.ERROR
    }
    trace_level_enum = level_map.get(trace_level.upper(), TraceLevel.INFO)
    
    # Initialize components
    tracer = init_tracer(trace_level_enum, log_to_file, trace_dir)
    monitor = init_monitor(tracer)
    dashboard = get_dashboard()
    
    return tracer, monitor, dashboard


def get_monitoring_status() -> dict:
    """Get current monitoring system status"""
    tracer = get_tracer()
    monitor = get_monitor()
    
    return {
        "tracer_initialized": tracer is not None,
        "active_conversations": len(tracer.active_conversations) if tracer else 0,
        "completed_conversations": len(tracer.completed_conversations) if tracer else 0,
        "monitor_initialized": monitor is not None,
        "active_operations": len(monitor.get_active_operations().get('operations', [])) if monitor else 0
    }