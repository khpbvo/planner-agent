"""
Streaming-enabled CLI interface for real-time agent responses
"""
import asyncio
from typing import Optional
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.markdown import Markdown
from openai_agents import Runner, SQLiteSession
from openai.types.responses import ResponseTextDeltaEvent

console = Console()


class StreamingCLI:
    """CLI with streaming support for real-time agent responses"""
    
    def __init__(self, orchestrator_agent):
        self.orchestrator = orchestrator_agent
        self.session = SQLiteSession(
            session_id="streaming_conversation",
            db_path="data/conversations.db"
        )
    
    async def process_with_streaming(self, message: str):
        """Process message with streaming output"""
        
        # Create a panel for streaming output
        output_text = ""
        panel = Panel(
            "",
            title="🤖 Assistant",
            border_style="green",
            padding=(1, 2)
        )
        
        with Live(panel, console=console, refresh_per_second=10) as live:
            try:
                # Run with streaming
                result = Runner.run_streamed(
                    self.orchestrator,
                    message,
                    session=self.session,
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
                        console.print(f"[dim]→ Delegating to: {event.new_agent.name}[/dim]")
                
                # Final output is available in result
                await result  # Wait for completion
                
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                return None
        
        return output_text
    
    async def run_interactive(self):
        """Run interactive streaming session"""
        console.print(Panel(
            Markdown("# 🚀 Streaming Planning Assistant\n\nWatch responses appear in real-time!"),
            border_style="blue"
        ))
        
        while True:
            try:
                # Get user input
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: console.input("\n[bold cyan]You:[/bold cyan] ")
                )
                
                if user_input.lower() in ['/exit', '/quit']:
                    console.print("[yellow]Goodbye! 👋[/yellow]")
                    break
                
                if not user_input.strip():
                    continue
                
                # Process with streaming
                await self.process_with_streaming(user_input)
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Use /exit to quit[/yellow]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")