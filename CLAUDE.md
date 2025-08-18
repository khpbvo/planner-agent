# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI Planning Assistant that uses the OpenAI Agents SDK to integrate MacOS Calendar, Todoist, and Gmail through natural language conversations. The system uses a multi-agent architecture where specialized agents work as tools under an orchestrator agent.

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On MacOS/Linux

# Install dependencies
pip install -r requirements.txt

# Download SpaCy model
python -m spacy download en_core_web_lg

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Running the Application
```bash
# Run the CLI interface
python src/main.py

# Debug mode
DEBUG=True python src/main.py
```

### CLI Commands
```
/help     - Show help
/status   - Show service status
/stream   - Toggle streaming mode (default: enabled)
/sync     - Force sync all services
/clear    - Clear screen
/exit     - Exit application
```

## Architecture

### Multi-Agent Pattern
Uses the "agents-as-tools" pattern from the OpenAI Agents SDK:

**Orchestrator Agent** (main) coordinates specialized agents:
- **Language Processor Agent**: SpaCy NLP for entity extraction
- **Calendar Manager Agent**: MacOS Calendar via AppleScript
- **Task Manager Agent**: Todoist API integration
- **Email Processor Agent**: Gmail API integration
- **Smart Planner Agent**: Intelligent scheduling logic

### Key Components

**Function Tools**: Each service integration is a `@function_tool`:
- `manage_calendar`: Calendar operations (list, create, update, delete, find slots)
- `manage_tasks`: Todoist operations (CRUD, priorities, projects)
- `manage_emails`: Gmail operations (read, send, extract tasks)
- `process_language`: NLP processing (entities, temporal parsing, intent)

**Session Management**: Uses `SQLiteSession` for conversation memory:
- Persistent conversation history across runs
- Automatic context management
- Session-based state preservation

**Streaming Interface**: Real-time response streaming:
- Live token-by-token output display
- Tool call progress indicators
- Agent handoff notifications

### Data Models (Pydantic V2)

**Task Models** (`models/task.py`):
- `Task`: Generic task model
- `TodoistTask`: Todoist-specific with API payload conversion
- `TaskPriority`, `TaskStatus`: Enums

**Event Models** (`models/event.py`):
- `CalendarEvent`: Calendar events with temporal logic
- `EventRecurrence`, `EventReminder`: Supporting models

**Context Models** (`models/context.py`):
- `PlanningContext`: Session-level context management
- `EntityContext`: NLP extracted entities
- `UserPreferences`: User settings and preferences

## SDK Implementation Details

### Correct Imports
```python
from openai_agents import Agent, Runner, function_tool, SQLiteSession
from openai.types.responses import ResponseTextDeltaEvent
```

### Agent Creation Pattern
```python
# Create tool first
@function_tool
async def my_tool(input_data: MyModel) -> str:
    # Tool implementation
    return result

# Create agent with tools
agent = Agent(
    name="Agent Name",
    instructions="Agent instructions",
    tools=[my_tool],
    model="gpt-4o"
)

# Use agent as tool in orchestrator
orchestrator = Agent(
    name="Orchestrator",
    instructions="Orchestrator instructions",
    tools=[
        agent.as_tool(
            tool_name="my_agent",
            tool_description="What this agent does"
        )
    ]
)
```

### Session Usage
```python
# Create session
session = SQLiteSession(
    session_id="conversation_id",
    db_path="data/conversations.db"
)

# Use with Runner
result = await Runner.run(
    agent,
    message,
    session=session,
    max_turns=10
)
```

### Streaming Implementation
```python
# Streaming runner
result = Runner.run_streamed(agent, message, session=session)

# Process stream events
async for event in result.stream_events():
    if event.type == "raw_response_event":
        if isinstance(event.data, ResponseTextDeltaEvent):
            # Handle token delta
            text += event.data.delta
    elif event.type == "run_item_stream_event":
        # Handle tool calls, completions
        pass
    elif event.type == "agent_updated_stream_event":
        # Handle agent handoffs
        pass
```

## Configuration

### Required Environment Variables
- `OPENAI_API_KEY`: OpenAI API key
- `TODOIST_API_KEY`: Todoist API key (optional)
- `GOOGLE_CLIENT_ID`: Google OAuth client ID (optional)
- `GOOGLE_CLIENT_SECRET`: Google OAuth secret (optional)

### Optional Settings
- `OPENAI_MODEL`: Default "gpt-4o"
- `SPACY_MODEL`: Default "en_core_web_lg"
- `SESSION_DB_PATH`: Default "data/sessions.db"
- `DEBUG`: Enable debug logging

## Testing Approach

Run the CLI and test with natural language:
- "What's on my calendar today?"
- "Add a task to review the report by Friday"
- "Schedule a meeting with John tomorrow at 2pm"
- "Check my emails and create tasks for important items"

Monitor agent handoffs and tool calls in streaming mode to verify proper SDK usage.

## Common Issues

### Calendar Access
macOS requires calendar permissions. Grant in:
System Preferences > Security & Privacy > Privacy > Calendar

### SpaCy Model Not Found
```bash
python -m spacy download en_core_web_lg
```

### Agent Tool Assignment
Tools must be assigned during Agent creation, not after:
```python
# Correct
agent = Agent(name="Agent", tools=[tool1, tool2])

# Incorrect
agent = Agent(name="Agent")
agent.tools = [tool1, tool2]  # This doesn't work
```