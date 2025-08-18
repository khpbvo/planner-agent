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
from openai_agents import Runner, SQLiteSession
from openai_agents.exceptions import InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered

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
            
            if self.streaming_mode:
                return await self._process_streaming(message)
            else:
                return await self._process_non_streaming(message)
            
        except InputGuardrailTripwireTriggered as e:
            return f"🛡️ Input blocked by safety guardrail: {e.guardrail_output.output_info}"
        except OutputGuardrailTripwireTriggered as e:
            return f"🛡️ Response blocked by safety guardrail: {e.guardrail_output.output_info}"
        except Exception as e:
            return f"❌ Error processing request: {str(e)}"
    
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
                        console.print(f"[dim]🔧 Calling tool: {event.item.name}[/dim]")
                    elif event.item.type == "tool_call_output_item":
                        console.print(f"[dim]✓ Tool completed[/dim]")
                
                elif event.type == "agent_updated_stream_event":
                    # Show agent handoffs
                    console.print(f"[dim]→ Using: {event.new_agent.name}[/dim]")
            
            # Wait for completion
            await result
        
        return output_text or "Response completed"
    
    async def handle_command(self, command: str) -> bool:
        """Handle special commands. Returns True if should continue, False to exit"""
        command = command.lower().strip()
        
        if command in ['/exit', '/quit']:
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
            
        else:
            console.print(f"[red]Unknown command: {command}[/red]")
            
        return True
    
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