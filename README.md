# 🗓️ AI Planning Assistant

An intelligent planning assistant that integrates MacOS Calendar, Todoist, and Gmail using the OpenAI Agents SDK. Manage your schedule, tasks, and emails through natural language conversations.

## Features

- **📅 MacOS Calendar Integration**: Create, update, and manage calendar events
- **✅ Todoist Integration**: Manage tasks, projects, and priorities
- **📧 Gmail Integration**: Process emails and extract action items
- **🧠 Natural Language Processing**: Understand temporal references and entities using SpaCy
- **🤖 Multi-Agent System**: Specialized agents for each service, coordinated by an orchestrator
- **💬 Interactive CLI**: Rich terminal interface with conversation history

## Architecture

The system uses a multi-agent architecture where each tool has its own specialized agent:

```
Orchestrator Agent
├── Language Processor Agent (SpaCy NLP)
├── Calendar Manager Agent (MacOS Calendar)
├── Task Manager Agent (Todoist)
├── Email Processor Agent (Gmail)
└── Smart Planner Agent (Scheduling Intelligence)
```

## Installation

### Prerequisites

- Python 3.9+
- MacOS (for Calendar integration)
- OpenAI API key
- Todoist API key (optional)
- Google OAuth credentials (optional for Gmail)

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd planner-agent
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On MacOS/Linux
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Download SpaCy language model:
```bash
python -m spacy download en_core_web_lg
```

5. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

## Configuration

Edit the `.env` file with your credentials:

```env
# Required
OPENAI_API_KEY=sk-...

# Optional (but recommended)
TODOIST_API_KEY=your_todoist_api_key

# For Gmail integration
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret
```

## Usage

### Start the CLI

```bash
python src/main.py
```

### Example Commands

```
💭 You: Schedule a meeting with John tomorrow at 2pm
🤖 Assistant: I'll schedule a meeting with John for tomorrow at 2:00 PM.

💭 You: What's on my calendar today?
🤖 Assistant: Here are your events for today...

💭 You: Add a task to review the quarterly report by Friday
🤖 Assistant: I've added "Review quarterly report" to your tasks with a due date of Friday.

💭 You: Check my emails and create tasks for important items
🤖 Assistant: I found 3 emails with action items...
```

### CLI Commands

- `/help` - Show available commands
- `/status` - Show service connection status
- `/sync` - Force sync all services
- `/clear` - Clear the screen
- `/exit` or `/quit` - Exit the application

## Project Structure

```
planner-agent/
├── src/
│   ├── agents/          # Agent definitions
│   │   └── orchestrator.py
│   ├── tools/           # Tool implementations
│   │   ├── calendar_tool.py
│   │   ├── todoist_tool.py
│   │   ├── gmail_tool.py
│   │   └── nlp_tool.py
│   ├── models/          # Pydantic data models
│   │   ├── task.py
│   │   ├── event.py
│   │   └── context.py
│   ├── cli/             # CLI interface
│   │   └── interface.py
│   ├── config.py        # Configuration management
│   └── main.py          # Entry point
├── data/                # Session storage
├── logs/                # Application logs
└── credentials/         # OAuth tokens (gitignored)
```

## Development

### Adding New Tools

1. Create a new tool in `src/tools/`
2. Create a corresponding agent in `src/agents/`
3. Add the agent to the orchestrator's handoffs
4. Update the tool initialization in the orchestrator

### Running Tests

```bash
pytest tests/
```

## Context Management

The system maintains three levels of context:

1. **Global Context**: Conversation history via SQLite sessions
2. **Planning Context**: Current planning state and preferences
3. **Entity Context**: Extracted entities and temporal references per message

## Security Notes

- Never commit `.env` or credential files
- API keys are stored in environment variables
- OAuth tokens are stored locally in the `credentials/` directory
- All sensitive directories are gitignored

## Troubleshooting

### SpaCy Model Not Found
```bash
python -m spacy download en_core_web_lg
```

### Calendar Access Issues
Ensure Terminal/your IDE has calendar access in:
System Preferences > Security & Privacy > Privacy > Calendar

### Todoist Connection Failed
Verify your API key at: https://todoist.com/app/settings/integrations

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Built with [OpenAI Agents SDK](https://github.com/openai/openai-agents-python)
- Uses [SpaCy](https://spacy.io/) for NLP
- Integrates with [Todoist API](https://developer.todoist.com/)
- Gmail integration via [Google API](https://developers.google.com/gmail/api)