"""
Test imports and basic agent functionality
"""
import sys
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_agents_import():
    """Test that agents can be imported"""
    try:
        from agents import Agent, Runner, function_tool, SQLiteSession
        assert Agent is not None
        assert Runner is not None
        assert function_tool is not None
        assert SQLiteSession is not None
    except ImportError as e:
        pytest.fail(f"Failed to import agents: {e}")


def test_config_import():
    """Test that config module can be imported"""
    try:
        from config import config, Config
        assert config is not None
        assert Config is not None
    except ImportError as e:
        pytest.fail(f"Failed to import config: {e}")


def test_tool_imports():
    """Test that all tool modules can be imported"""
    try:
        from tools import (
            create_calendar_tool,
            create_todoist_tool,
            create_gmail_tool,
            create_nlp_tool
        )
        assert create_calendar_tool is not None
        assert create_todoist_tool is not None
        assert create_gmail_tool is not None
        assert create_nlp_tool is not None
    except ImportError as e:
        pytest.fail(f"Failed to import tools: {e}")


def test_agent_module_imports():
    """Test that agent modules can be imported"""
    try:
        from agent_modules import create_orchestrator_agent
        from agent_modules.handoffs import create_handoff_tools, create_handoff_coordinator
        from agent_modules.smart_planner import create_smart_planning_tool
        
        assert create_orchestrator_agent is not None
        assert create_handoff_tools is not None
        assert create_handoff_coordinator is not None
        assert create_smart_planning_tool is not None
    except ImportError as e:
        pytest.fail(f"Failed to import agent modules: {e}")


def test_model_imports():
    """Test that model classes can be imported"""
    try:
        from models.event import CalendarEvent
        from models.task import Task, TodoistTask
        from models.context import PlanningContext, EntityContext
        from models.calendar_tool import CalendarOperation, CalendarResponse
        from models.tool_error import ToolError
        
        assert CalendarEvent is not None
        assert Task is not None
        assert TodoistTask is not None
        assert PlanningContext is not None
        assert EntityContext is not None
        assert CalendarOperation is not None
        assert CalendarResponse is not None
        assert ToolError is not None
    except ImportError as e:
        pytest.fail(f"Failed to import models: {e}")


@pytest.mark.asyncio
async def test_create_calendar_tool():
    """Test creation of calendar tool"""
    from tools import create_calendar_tool
    from agents import FunctionTool
    
    tool = create_calendar_tool()
    assert tool is not None
    assert isinstance(tool, FunctionTool)


@pytest.mark.asyncio
async def test_create_nlp_tool():
    """Test creation of NLP tool"""
    from tools import create_nlp_tool
    from agents import FunctionTool
    from agents.tool_context import ToolContext
    from tools.nlp_tool import NLPResponse
    
    tool = create_nlp_tool()
    assert tool is not None
    assert isinstance(tool, FunctionTool)
    
    # Test the tool functionality by calling the on_invoke_tool method
    import json
    ctx = ToolContext(context=None, tool_name="nlp", tool_call_id="1")
    args = json.dumps({"operation_input": {"text": "Test text for NLP processing"}})
    result = await tool.on_invoke_tool(ctx, args)
    assert isinstance(result, NLPResponse)
    assert result.intent is not None
    assert isinstance(result.entities, list)


@pytest.mark.asyncio
async def test_create_todoist_tool_stub():
    """Test creation of Todoist tool stub when no API key"""
    from tools import create_todoist_tool
    from agents import FunctionTool
    from agents.tool_context import ToolContext
    from tools.todoist_tool import TodoistResponse
    
    tool = create_todoist_tool(None)
    assert tool is not None
    assert isinstance(tool, FunctionTool)
    
    # Test the stub functionality
    import json
    ctx = ToolContext(context=None, tool_name="todoist", tool_call_id="1")
    args = json.dumps({"operation_input": {"operation": "list"}})
    result = await tool.on_invoke_tool(ctx, args)
    assert isinstance(result, TodoistResponse)
    assert result.status == "error"
    assert "not configured" in (result.message or "").lower()


@pytest.mark.asyncio
async def test_create_gmail_tool_stub():
    """Test creation of Gmail tool stub when not configured"""
    from tools import create_gmail_tool
    from config import Config
    from agents import FunctionTool
    from agents.tool_context import ToolContext
    from tools.gmail_tool import GmailResponse
    
    config = Config()
    config.google_client_id = None
    
    tool = create_gmail_tool(config)
    assert tool is not None
    assert isinstance(tool, FunctionTool)
    
    # Test the stub functionality
    import json
    ctx = ToolContext(context=None, tool_name="gmail", tool_call_id="1")
    args = json.dumps({"operation_input": {"operation": "list"}})
    result = await tool.on_invoke_tool(ctx, args)
    assert isinstance(result, GmailResponse)
    assert result.status == "error"
    assert "not configured" in (result.message or "").lower()


@pytest.mark.asyncio
async def test_handoff_tools():
    """Test handoff tool creation"""
    from agent_modules.handoffs import create_handoff_tools
    from agents import FunctionTool
    
    tools = create_handoff_tools()
    assert tools is not None
    assert len(tools) == 2
    assert all(isinstance(tool, FunctionTool) for tool in tools)


@pytest.mark.asyncio
async def test_handoff_coordinator():
    """Test handoff coordinator creation"""
    from agent_modules.handoffs import create_handoff_coordinator
    from config import Config
    
    config = Config()
    coordinator = create_handoff_coordinator(config)
    assert coordinator is not None
    assert hasattr(coordinator, 'capabilities')
    assert hasattr(coordinator, 'handoff_history')


@pytest.mark.asyncio
async def test_orchestrator_agent_creation():
    """Test that orchestrator agent can be created"""
    from config import Config
    from agent_modules import create_orchestrator_agent
    
    # Mock the openai_agents module
    with patch('agent_modules.orchestrator.Agent') as MockAgent:
        # Setup mock
        mock_agent_instance = MagicMock()
        mock_agent_instance.as_tool = MagicMock(return_value=MagicMock())
        MockAgent.return_value = mock_agent_instance
        
        # Create config
        config = Config()
        config.openai_api_key = "test-key"
        config.openai_model = "gpt-4"
        
        # Create orchestrator
        orchestrator = await create_orchestrator_agent(config)
        
        # Verify it was created
        assert orchestrator is not None
        assert MockAgent.called
        
        # Check that the main orchestrator was created with the right name
        main_agent_call = [call for call in MockAgent.call_args_list 
                          if call[1].get('name') == 'Planning Assistant']
        assert len(main_agent_call) > 0


@pytest.mark.asyncio
async def test_cli_interface_import():
    """Test that CLI interface can be imported"""
    try:
        from cli.interface import PlannerCLI
        assert PlannerCLI is not None
    except ImportError as e:
        pytest.fail(f"Failed to import CLI interface: {e}")


def test_main_module_import():
    """Test that main module can be imported"""
    try:
        from main import setup_logging, initialize_services
        assert setup_logging is not None
        assert initialize_services is not None
    except ImportError as e:
        pytest.fail(f"Failed to import main module: {e}")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])