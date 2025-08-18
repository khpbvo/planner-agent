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
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
import os
from pathlib import Path

console = Console()


class PlannerCLI:
    """Interactive CLI for the Planning Assistant"""
    
    def __init__(self, orchestrator_agent=None):
        self.orchestrator = orchestrator_agent
        self.session = PromptSession(
            history=FileHistory(str(Path.home() / '.planner_history')),
            auto_suggest=AutoSuggestFromHistory(),
        )
        self.running = False
        
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
            # This will be replaced with actual agent processing
            with console.status("[bold green]Processing your request...", spinner="dots"):
                # Simulate processing
                await asyncio.sleep(1)
                
            # TODO: Actual agent processing here
            # result = await Runner.run(self.orchestrator, message)
            # return result.final_output
            
            return f"🤖 Received: '{message}' (Agent processing not yet implemented)"
            
        except Exception as e:
            return f"❌ Error processing request: {str(e)}"
    
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
                    lambda: self.session.prompt(
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
                
                # Display response
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