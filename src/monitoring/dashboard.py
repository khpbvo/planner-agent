"""
Monitoring dashboard for the Planning Assistant

Provides real-time monitoring views and analytics for system performance,
agent usage, and conversation patterns.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text
from rich.tree import Tree
import asyncio
import json

from tracer import get_tracer, TraceEventType, TraceLevel
from agent_monitor import get_monitor

console = Console()


class MonitoringDashboard:
    """Real-time monitoring dashboard"""
    
    def __init__(self):
        self.tracer = get_tracer()
        self.monitor = get_monitor()
        self.running = False
        self.refresh_rate = 2.0  # seconds
    
    def create_overview_panel(self) -> Panel:
        """Create system overview panel"""
        analytics = self.tracer.get_system_analytics()
        
        overview_text = f"""
🔍 **System Overview**

📊 **Conversations**
• Total: {analytics['total_conversations']}
• Active: {analytics['active_conversations']}
• Completed: {analytics['completed_conversations']}
• Success Rate: {analytics['success_rate']:.1%}

🤖 **Agent Activity** 
• Total Handoffs: {analytics['total_handoffs']}
• Active Operations: {len(self.monitor.get_active_operations().get('operations', []))}
        """
        
        return Panel(
            overview_text.strip(),
            title="📊 System Overview",
            border_style="green",
            padding=(1, 2)
        )
    
    def create_agent_usage_table(self) -> Table:
        """Create agent usage statistics table"""
        analytics = self.tracer.get_system_analytics()
        agent_usage = analytics.get('agent_usage', {})
        
        table = Table(title="🤖 Agent Usage Statistics")
        table.add_column("Agent", style="cyan", no_wrap=True)
        table.add_column("Calls", justify="right", style="green")
        table.add_column("Percentage", justify="right", style="yellow")
        
        total_calls = sum(agent_usage.values()) if agent_usage else 1
        
        for agent, calls in sorted(agent_usage.items(), key=lambda x: x[1], reverse=True):
            percentage = (calls / total_calls) * 100
            table.add_row(
                agent,
                str(calls),
                f"{percentage:.1f}%"
            )
        
        if not agent_usage:
            table.add_row("No data", "0", "0%")
        
        return table
    
    def create_tool_usage_table(self) -> Table:
        """Create tool usage statistics table"""
        analytics = self.tracer.get_system_analytics()
        tool_usage = analytics.get('tool_usage', {})
        
        table = Table(title="🔧 Tool Usage Statistics")
        table.add_column("Tool", style="magenta", no_wrap=True)
        table.add_column("Calls", justify="right", style="green")
        table.add_column("Percentage", justify="right", style="yellow")
        
        total_calls = sum(tool_usage.values()) if tool_usage else 1
        
        for tool, calls in sorted(tool_usage.items(), key=lambda x: x[1], reverse=True):
            percentage = (calls / total_calls) * 100
            table.add_row(
                tool,
                str(calls),
                f"{percentage:.1f}%"
            )
        
        if not tool_usage:
            table.add_row("No data", "0", "0%")
        
        return table
    
    def create_performance_panel(self) -> Panel:
        """Create performance metrics panel"""
        analytics = self.tracer.get_system_analytics()
        perf_metrics = analytics.get('performance_metrics', {})
        
        performance_text = "🚀 **Performance Metrics**\n\n"
        
        # Counters
        counters = perf_metrics.get('counters', {})
        if counters:
            performance_text += "📊 **Counters:**\n"
            for counter, value in counters.items():
                performance_text += f"• {counter}: {value}\n"
            performance_text += "\n"
        
        # Duration metrics
        duration_metrics = {k: v for k, v in perf_metrics.items() if k != 'counters'}
        if duration_metrics:
            performance_text += "⏱️ **Response Times:**\n"
            for metric, stats in duration_metrics.items():
                performance_text += f"• {metric}: {stats['avg_ms']:.1f}ms avg ({stats['count']} calls)\n"
        
        if not counters and not duration_metrics:
            performance_text += "No performance data available yet."
        
        return Panel(
            performance_text.strip(),
            title="🚀 Performance",
            border_style="blue",
            padding=(1, 2)
        )
    
    def create_recent_activity_panel(self) -> Panel:
        """Create recent activity panel"""
        activity_text = "📝 **Recent Activity**\n\n"
        
        # Get recent events from active conversations
        recent_events = []
        for conversation in self.tracer.active_conversations.values():
            recent_events.extend(conversation.events[-5:])  # Last 5 events per conversation
        
        # Sort by timestamp
        recent_events.sort(key=lambda e: e.timestamp, reverse=True)
        recent_events = recent_events[:10]  # Top 10 most recent
        
        if recent_events:
            for event in recent_events:
                time_str = event.timestamp.strftime("%H:%M:%S")
                icon = self._get_event_icon(event.event_type)
                activity_text += f"{icon} {time_str} - {event.message}\n"
        else:
            activity_text += "No recent activity."
        
        return Panel(
            activity_text.strip(),
            title="📝 Recent Activity",
            border_style="yellow",
            padding=(1, 2),
            height=15
        )
    
    def create_error_panel(self) -> Panel:
        """Create error tracking panel"""
        error_text = "🚨 **Error Tracking**\n\n"
        
        # Count errors by type
        error_counts = {}
        recent_errors = []
        
        for conversation in self.tracer.completed_conversations + list(self.tracer.active_conversations.values()):
            for event in conversation.events:
                if event.event_type == TraceEventType.ERROR:
                    error_type = event.data.get('error_type', 'Unknown')
                    error_counts[error_type] = error_counts.get(error_type, 0) + 1
                    recent_errors.append(event)
        
        # Show error counts
        if error_counts:
            error_text += "📊 **Error Types:**\n"
            for error_type, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
                error_text += f"• {error_type}: {count}\n"
            
            # Show recent errors
            recent_errors.sort(key=lambda e: e.timestamp, reverse=True)
            if recent_errors:
                error_text += f"\n🕐 **Recent Errors:**\n"
                for event in recent_errors[:3]:  # Last 3 errors
                    time_str = event.timestamp.strftime("%H:%M:%S")
                    error_msg = event.data.get('error_message', 'Unknown error')[:50]
                    error_text += f"• {time_str}: {error_msg}...\n"
        else:
            error_text += "✅ No errors recorded!"
        
        return Panel(
            error_text.strip(),
            title="🚨 Errors",
            border_style="red",
            padding=(1, 2)
        )
    
    def _get_event_icon(self, event_type: TraceEventType) -> str:
        """Get icon for event type"""
        icons = {
            TraceEventType.CONVERSATION_START: "🆕",
            TraceEventType.CONVERSATION_END: "✅",
            TraceEventType.AGENT_CALL: "🤖",
            TraceEventType.TOOL_CALL: "🔧",
            TraceEventType.HANDOFF: "🔄",
            TraceEventType.ERROR: "🚨",
            TraceEventType.PERFORMANCE: "⏱️",
            TraceEventType.USER_INPUT: "👤",
            TraceEventType.SYSTEM_OUTPUT: "💬"
        }
        return icons.get(event_type, "📋")
    
    def create_dashboard_layout(self) -> Layout:
        """Create the complete dashboard layout"""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        layout["body"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        layout["left"].split_column(
            Layout(name="overview"),
            Layout(name="performance")
        )
        
        layout["right"].split_column(
            Layout(name="tables"),
            Layout(name="activity")
        )
        
        layout["tables"].split_row(
            Layout(name="agents"),
            Layout(name="tools")
        )
        
        # Header
        header_text = Text(
            "🔍 Planning Assistant - Monitoring Dashboard", 
            style="bold white on blue",
            justify="center"
        )
        layout["header"].update(Panel(header_text))
        
        # Footer
        footer_text = Text(
            f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Press Ctrl+C to exit",
            style="dim",
            justify="center"
        )
        layout["footer"].update(Panel(footer_text))
        
        return layout
    
    def update_dashboard(self, layout: Layout):
        """Update dashboard content"""
        try:
            # Update all panels
            layout["overview"].update(self.create_overview_panel())
            layout["performance"].update(self.create_performance_panel())
            layout["agents"].update(self.create_agent_usage_table())
            layout["tools"].update(self.create_tool_usage_table())
            layout["activity"].update(self.create_recent_activity_panel())
            
            # Update footer with current time
            footer_text = Text(
                f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Press Ctrl+C to exit",
                style="dim",
                justify="center"
            )
            layout["footer"].update(Panel(footer_text))
            
        except Exception as e:
            console.print(f"[red]Error updating dashboard: {e}[/red]")
    
    async def run_dashboard(self):
        """Run the live dashboard"""
        console.print("🚀 Starting monitoring dashboard...", style="green")
        
        layout = self.create_dashboard_layout()
        
        try:
            with Live(layout, console=console, refresh_per_second=1/self.refresh_rate, screen=True):
                self.running = True
                while self.running:
                    self.update_dashboard(layout)
                    await asyncio.sleep(self.refresh_rate)
                    
        except KeyboardInterrupt:
            console.print("\n👋 Dashboard stopped by user", style="yellow")
        except Exception as e:
            console.print(f"\n❌ Dashboard error: {e}", style="red")
        finally:
            self.running = False
    
    def show_conversation_details(self, session_id: str):
        """Show detailed information about a specific conversation"""
        analytics = self.tracer.get_conversation_analytics(session_id)
        
        if "error" in analytics:
            console.print(f"[red]{analytics['error']}[/red]")
            return
        
        # Create detailed view
        details_table = Table(title=f"📋 Conversation Details: {session_id}")
        details_table.add_column("Metric", style="cyan")
        details_table.add_column("Value", style="white")
        
        details_table.add_row("Session ID", analytics["session_id"])
        details_table.add_row("Start Time", analytics["start_time"])
        details_table.add_row("End Time", analytics["end_time"] or "Active")
        details_table.add_row("Duration", f"{analytics['duration_ms']:.1f}ms" if analytics["duration_ms"] else "N/A")
        details_table.add_row("Event Count", str(analytics["event_count"]))
        details_table.add_row("Success", "✅ Yes" if analytics["success"] else "❌ No")
        details_table.add_row("Error Count", str(analytics["error_count"]))
        details_table.add_row("Handoff Count", str(analytics["handoff_count"]))
        
        console.print(details_table)
        
        # Show agent usage for this conversation
        if analytics["agent_usage"]:
            agent_table = Table(title="🤖 Agent Usage")
            agent_table.add_column("Agent", style="cyan")
            agent_table.add_column("Calls", style="green")
            
            for agent, calls in analytics["agent_usage"].items():
                agent_table.add_row(agent, str(calls))
            
            console.print(agent_table)
        
        # Show tool usage for this conversation
        if analytics["tool_usage"]:
            tool_table = Table(title="🔧 Tool Usage")
            tool_table.add_column("Tool", style="magenta")
            tool_table.add_column("Calls", style="green")
            
            for tool, calls in analytics["tool_usage"].items():
                tool_table.add_row(tool, str(calls))
            
            console.print(tool_table)
    
    def export_analytics(self, filepath: str):
        """Export system analytics to JSON file"""
        try:
            analytics = self.tracer.get_system_analytics()
            
            with open(filepath, 'w') as f:
                json.dump(analytics, f, indent=2, default=str)
            
            console.print(f"[green]✅ Analytics exported to {filepath}[/green]")
            
        except Exception as e:
            console.print(f"[red]❌ Export failed: {e}[/red]")


# Global dashboard instance
_dashboard: Optional[MonitoringDashboard] = None


def get_dashboard() -> MonitoringDashboard:
    """Get the global dashboard instance"""
    global _dashboard
    if _dashboard is None:
        _dashboard = MonitoringDashboard()
    return _dashboard