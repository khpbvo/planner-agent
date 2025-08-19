"""
CLI Chat Interface for the Planning Assistant
"""
import asyncio
from typing import Optional
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner
from rich.table import Table
from openai.types.responses import ResponseTextDeltaEvent
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
import os
from pathlib import Path
from agents import Runner, SQLiteSession
from agents import InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered
from monitoring.tracer import get_tracer, init_tracer
from monitoring.dashboard import get_dashboard

console = Console()


class PlannerCLI:
    """Interactive CLI for the Planning Assistant"""
    
    def __init__(self, orchestrator_agent=None):
        self.orchestrator = orchestrator_agent
        self.prompt_session = PromptSession(
            history=FileHistory(str(Path.home() / '.planner_history')),
            auto_suggest=AutoSuggestFromHistory(),
        )
        self.running = False
        # SQLite session for conversation memory
        self.agent_session = None
        self.streaming_mode = True
        
        # Initialize monitoring
        self.tracer = init_tracer()
        self.dashboard = get_dashboard()
        self.conversation_trace = None
        
    def display_welcome(self):
        """Display welcome message and instructions"""
        welcome_text = """
# 🗓️ AI Planning Assistant

Welcome to your intelligent planning assistant that integrates:
- 📅 MacOS Calendar
- ✅ Todoist
- 📧 Gmail
- ☁️ iCloud

## Commands:
- Type your request naturally (e.g., "Schedule a meeting tomorrow at 2pm")
- `/help` - Show available commands
- `/status` - Show current integrations status
- `/sync` - Force sync all services
- `/stream` - Toggle streaming mode
- `/handoffs` - Show agent handoff analytics
- `/monitor` - Open monitoring dashboard
- `/analytics` - Show system analytics
- `/clear` - Clear the screen
- `/exit` or `/quit` - Exit the application

## Examples:
- "What's on my calendar today?"
- "Add a task to buy groceries with high priority"
- "Schedule time to work on the presentation tomorrow"
- "Check my emails and create tasks for important ones"
        """
        console.print(Panel(Markdown(welcome_text), title="Welcome", border_style="blue"))
    
    def display_status(self):
        """Display current service connection status"""
        table = Table(title="Service Status", show_header=True, header_style="bold magenta")
        table.add_column("Service", style="cyan", no_wrap=True)
        table.add_column("Status", justify="center")
        table.add_column("Last Sync", justify="right")
        
        # TODO: Get actual status from agents
        services = [
            ("MacOS Calendar", "🟢 Connected", "2 min ago"),
            ("Todoist", "🟢 Connected", "1 min ago"),
            ("Gmail", "🟡 Authenticating", "N/A"),
            ("iCloud", "🔴 Not configured", "N/A"),
        ]
        
        for service, status, last_sync in services:
            table.add_row(service, status, last_sync)
        
        console.print(table)
    
    async def process_message(self, message: str) -> str:
        """Process user message through the orchestrator agent"""
        if not self.orchestrator:
            return "⚠️ Orchestrator agent not initialized. Please check your configuration."
        
        try:
            # Initialize session if not exists
            if not self.agent_session:
                self.agent_session = SQLiteSession(
                    session_id="main_conversation",
                    db_path="data/conversations.db"
                )
            
            # Start conversation tracing if not already started
            if not self.conversation_trace:
                self.conversation_trace = self.tracer.start_conversation(
                    session_id=self.agent_session.session_id
                )
            
            # Trace user input
            self.tracer._add_event(self.tracer.create_event(
                event_type="user_input",
                level="info", 
                session_id=self.conversation_trace.session_id,
                message=f"User input: {message[:100]}...",
                data={"input_length": len(message)}
            ))
            
            if self.streaming_mode:
                result = await self._process_streaming(message)
            else:
                result = await self._process_non_streaming(message)
            
            # Trace system output
            self.tracer._add_event(self.tracer.create_event(
                event_type="system_output",
                level="info",
                session_id=self.conversation_trace.session_id,
                message=f"System output: {result[:100]}...",
                data={"output_length": len(result)}
            ))
            
            return result
            
        except InputGuardrailTripwireTriggered as e:
            error_msg = f"🛡️ Input blocked by safety guardrail: {e.guardrail_output.output_info}"
            if self.conversation_trace:
                self.tracer.trace_error(
                    error=e,
                    context={"type": "input_guardrail", "message": message},
                    session_id=self.conversation_trace.session_id
                )
            return error_msg
        except OutputGuardrailTripwireTriggered as e:
            error_msg = f"🛡️ Response blocked by safety guardrail: {e.guardrail_output.output_info}"
            if self.conversation_trace:
                self.tracer.trace_error(
                    error=e,
                    context={"type": "output_guardrail", "message": message},
                    session_id=self.conversation_trace.session_id
                )
            return error_msg
        except Exception as e:
            error_msg = f"❌ Error processing request: {str(e)}"
            if self.conversation_trace:
                self.tracer.trace_error(
                    error=e,
                    context={"message": message},
                    session_id=self.conversation_trace.session_id
                )
            return error_msg
    
    async def _process_non_streaming(self, message: str) -> str:
        """Process message without streaming"""
        with console.status("[bold green]Processing your request...", spinner="dots"):
            result = await Runner.run(
                self.orchestrator, 
                message,
                session=self.agent_session,
                max_turns=10
            )
        return str(result.final_output)
    
    async def _process_streaming(self, message: str) -> str:
        """Process message with streaming output"""
        output_text = ""
        panel = Panel(
            "",
            title="🤖 Assistant (Streaming)",
            border_style="green",
            padding=(1, 2)
        )
        
        with Live(panel, console=console, refresh_per_second=10) as live:
            # Run with streaming
            result = Runner.run_streamed(
                self.orchestrator,
                message,
                session=self.agent_session,
                max_turns=10
            )
            
            # Stream events
            async for event in result.stream_events():
                if event.type == "raw_response_event":
                    # Handle text deltas for streaming output
                    if isinstance(event.data, ResponseTextDeltaEvent):
                        output_text += event.data.delta
                        panel.renderable = Markdown(output_text)
                        live.update(panel)
                
                elif event.type == "run_item_stream_event":
                    # Handle completed items
                    if event.item.type == "tool_call_item":
                        # Get tool name from raw_item - handle different tool call types
                        tool_name = "Unknown tool"
                        raw_item = event.item.raw_item

                        # Try different ways to get the tool name in priority order
                        if hasattr(raw_item, 'tool_name'):
                            tool_name = raw_item.tool_name
                        elif hasattr(raw_item, 'id'):
                            tool_name = raw_item.id
                        elif hasattr(raw_item, 'function') and hasattr(raw_item.function, 'name'):
                            tool_name = raw_item.function.name
                        elif hasattr(raw_item, 'name'):
                            tool_name = raw_item.name
                        elif hasattr(raw_item, 'type'):
                            tool_name = f"{raw_item.type} tool"
                        else:
                            console.log("Debug: tool call missing name or identifier")

                        console.print(f"[dim]🔧 Calling tool: {tool_name}[/dim]")
                    elif event.item.type == "tool_call_output_item":
                        console.print(f"[dim]✓ Tool completed[/dim]")
                
                elif event.type == "agent_updated_stream_event":
                    # Show agent handoffs
                    console.print(f"[blue]→ Handoff to: {event.new_agent.name}[/blue]")
                    
                elif event.type == "handoff_stream_event":
                    # Show detailed handoff information
                    if hasattr(event, 'handoff_reason'):
                        console.print(f"[cyan]🔄 Handoff: {event.handoff_reason}[/cyan]")
            
            # Stream events are already handled above
            # RunResultStreaming doesn't support direct await
            
        return output_text or "Response completed"
    
    async def handle_command(self, command: str) -> bool:
        """Handle special commands. Returns True if should continue, False to exit"""
        command = command.lower().strip()
        
        if command in ['/exit', '/quit']:
            # End conversation trace
            if self.conversation_trace:
                self.tracer.end_conversation(self.conversation_trace.session_id)
                console.print(f"[dim]💾 Conversation trace saved[/dim]")
            console.print("[yellow]Goodbye! 👋[/yellow]")
            return False
            
        elif command == '/help':
            self.display_welcome()
            
        elif command == '/status':
            self.display_status()
            
        elif command == '/clear':
            console.clear()
            
        elif command == '/sync':
            with console.status("[bold green]Syncing all services...", spinner="dots"):
                await asyncio.sleep(2)  # TODO: Actual sync
            console.print("[green]✓ All services synced successfully[/green]")
            
        elif command == '/stream':
            self.streaming_mode = not self.streaming_mode
            mode = "enabled" if self.streaming_mode else "disabled"
            console.print(f"[cyan]Streaming mode {mode}[/cyan]")
            
        elif command == '/handoffs':
            await self.show_handoff_analytics()
            
        elif command == '/monitor':
            console.print("[cyan]Starting monitoring dashboard...[/cyan]")
            await self.dashboard.run_dashboard()
            
        elif command == '/analytics':
            await self.show_system_analytics()
            
        else:
            console.print(f"[red]Unknown command: {command}[/red]")
            
        return True
    
    async def show_handoff_analytics(self):
        """Display handoff analytics using the orchestrator"""
        try:
            if not self.orchestrator:
                console.print("[red]❌ Orchestrator not available[/red]")
                return
                
            with console.status("[bold green]Analyzing handoff patterns...", spinner="dots"):
                # Use the orchestrator to analyze handoff patterns
                response = await self.process_message("analyze handoff patterns")
                
            console.print(Panel(
                response,
                title="🔄 Handoff Analytics",
                border_style="cyan",
                padding=(1, 2)
            ))
            
        except Exception as e:
            console.print(f"[red]❌ Error getting handoff analytics: {str(e)}[/red]")
    
    async def show_system_analytics(self):
        """Display comprehensive system analytics"""
        try:
            analytics = self.tracer.get_system_analytics()
            
            # Overview table
            overview_table = Table(title="📊 System Overview")
            overview_table.add_column("Metric", style="cyan")
            overview_table.add_column("Value", style="white")
            
            overview_table.add_row("Total Conversations", str(analytics["total_conversations"]))
            overview_table.add_row("Active Conversations", str(analytics["active_conversations"]))
            overview_table.add_row("Completed Conversations", str(analytics["completed_conversations"]))
            overview_table.add_row("Success Rate", f"{analytics['success_rate']:.1%}")
            overview_table.add_row("Total Handoffs", str(analytics["total_handoffs"]))
            
            console.print(overview_table)
            
            # Agent usage table
            agent_usage = analytics.get("agent_usage", {})
            if agent_usage:
                agent_table = Table(title="🤖 Agent Usage")
                agent_table.add_column("Agent", style="green")
                agent_table.add_column("Calls", justify="right", style="cyan")
                
                for agent, calls in sorted(agent_usage.items(), key=lambda x: x[1], reverse=True):
                    agent_table.add_row(agent, str(calls))
                
                console.print(agent_table)
            
            # Tool usage table
            tool_usage = analytics.get("tool_usage", {})
            if tool_usage:
                tool_table = Table(title="🔧 Tool Usage")
                tool_table.add_column("Tool", style="magenta")
                tool_table.add_column("Calls", justify="right", style="cyan")
                
                for tool, calls in sorted(tool_usage.items(), key=lambda x: x[1], reverse=True):
                    tool_table.add_row(tool, str(calls))
                
                console.print(tool_table)
            
            # Performance metrics
            perf_metrics = analytics.get("performance_metrics", {})
            if perf_metrics.get("counters") or any(k != "counters" for k in perf_metrics.keys()):
                perf_table = Table(title="🚀 Performance Metrics")
                perf_table.add_column("Metric", style="yellow")
                perf_table.add_column("Value", style="white")
                
                # Add counters
                for counter, value in perf_metrics.get("counters", {}).items():
                    perf_table.add_row(counter, str(value))
                
                # Add duration metrics
                for metric, stats in perf_metrics.items():
                    if metric != "counters" and isinstance(stats, dict):
                        perf_table.add_row(f"{metric} (avg)", f"{stats['avg_ms']:.1f}ms")
                
                console.print(perf_table)
            
            # Export option
            console.print("\n💾 Export analytics with: /export <filename>")
            
        except Exception as e:
            console.print(f"[red]❌ Error getting system analytics: {str(e)}[/red]")
    
    async def run(self):
        """Main CLI loop"""
        self.running = True
        self.display_welcome()
        
        while self.running:
            try:
                # Get user input
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.prompt_session.prompt(
                        "\n💭 You: ",
                        multiline=False,
                    )
                )
                
                if not user_input.strip():
                    continue
                
                # Check for commands
                if user_input.startswith('/'):
                    self.running = await self.handle_command(user_input)
                    continue
                
                # Process with agent
                response = await self.process_message(user_input)
                
                # Display response (only if not streaming, since streaming displays live)
                if not self.streaming_mode and response:
                    console.print(Panel(
                        Markdown(response),
                        title="🤖 Assistant",
                        border_style="green",
                        padding=(1, 2)
                    ))
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Use /exit to quit[/yellow]")
                continue
                
            except EOFError:
                self.running = False
                console.print("\n[yellow]Goodbye! 👋[/yellow]")
                
            except Exception as e:
                console.print(f"[red]Unexpected error: {e}[/red]")
                

async def main():
    """Entry point for the CLI"""
    cli = PlannerCLI()
    await cli.run()


if __name__ == "__main__":
    asyncio.run(main())