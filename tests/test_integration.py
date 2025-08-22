"""
Integration tests for the Planning Assistant
"""
import sys
import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.mark.asyncio
async def test_calendar_tool_list_events():
    """Test calendar tool listing events"""
    from tools.calendar_tool import manage_calendar, _manage_calendar_impl
    from models.calendar_tool import CalendarOperation
    from agents import RunContextWrapper
    
    # Create operation input
    operation = CalendarOperation(
        operation="list",
        calendar_name="Calendar",
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(days=7)
    )
    
    # Mock subprocess to avoid actual AppleScript execution
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout='[]',
            stderr=''
        )
        
        # Call the tool implementation directly
        result = await _manage_calendar_impl(operation)
        
        # Check result
        assert result is not None
        assert hasattr(result, 'status')
        assert mock_run.called


@pytest.mark.asyncio
async def test_nlp_tool_processing():
    """Test NLP tool text processing"""
    from tools import create_nlp_tool
    from agents.tool_context import ToolContext
    from tools.nlp_tool import NLPResponse

    tool = create_nlp_tool()
    ctx = ToolContext(context=None, tool_name="nlp", tool_call_id="1")
    
    # Test different text inputs
    test_cases = [
        ("Schedule a meeting tomorrow", "schedule_event"),
        ("Add a task to my todo list", "create_task"),
        ("What's on my calendar today?", "query_schedule"),
        ("Hello, how are you?", "general_query")
    ]
    
    for text, expected_intent in test_cases:
        args = json.dumps({"operation_input": {"text": text}})
        result = await tool.on_invoke_tool(ctx, args)

        assert isinstance(result, NLPResponse)
        assert result.intent == expected_intent
        assert result.raw_text == text


@pytest.mark.asyncio
async def test_handoff_coordinator_functionality():
    """Test handoff coordinator determines correct agent"""
    from agent_modules.handoffs import HandoffCoordinator
    from models.context import PlanningContext, EntityContext
    from config import Config
    
    config = Config()
    coordinator = HandoffCoordinator(config)
    
    # Create test context
    context = PlanningContext(
        session_id="test_session",
        entity_context=EntityContext(raw_text="test input")
    )
    
    # Test calendar-related request
    request = coordinator.analyze_handoff_need(
        context,
        "Schedule a meeting tomorrow at 2pm",
        "orchestrator"
    )
    
    assert request is not None
    assert request.target_agent == "calendar_manager"
    assert request.urgency in ["normal", "high"]
    
    # Test task-related request
    request = coordinator.analyze_handoff_need(
        context,
        "Add a task to review the report",
        "orchestrator"
    )
    
    assert request is not None
    assert request.target_agent == "task_manager"
    
    # Test email-related request
    request = coordinator.analyze_handoff_need(
        context,
        "Check my emails for action items",
        "orchestrator"
    )
    
    assert request is not None
    assert request.target_agent == "email_processor"
    
    # Test planning request
    request = coordinator.analyze_handoff_need(
        context,
        "Help me plan and optimize my day",
        "orchestrator"
    )
    
    assert request is not None
    assert request.target_agent == "smart_planner"


@pytest.mark.asyncio
async def test_orchestrator_agent_workflow():
    """Test orchestrator agent workflow with mocked agents"""
    from agent_modules import create_orchestrator_agent
    from config import Config
    from agents import Agent, Runner, RunResult
    
    config = Config()
    config.openai_api_key = "test-key"
    config.openai_model = "gpt-4"
    
    # Mock Agent class and Runner
    with patch('agent_modules.orchestrator.Agent') as MockAgent, \
         patch('agents.Runner') as MockRunner:
        
        # Setup mock agent instance
        mock_agent_instance = MagicMock()
        mock_agent_instance.name = "Planning Assistant"
        
        # Mock as_tool method
        def mock_as_tool(tool_name, tool_description):
            mock_tool = MagicMock()
            mock_tool.name = tool_name
            mock_tool.description = tool_description
            return mock_tool
        
        mock_agent_instance.as_tool = mock_as_tool
        MockAgent.return_value = mock_agent_instance
        
        # Create orchestrator
        orchestrator = await create_orchestrator_agent(config)
        
        assert orchestrator is not None
        assert MockAgent.called
        
        # Verify all agents were created
        call_names = [call[1].get('name') for call in MockAgent.call_args_list]
        assert "Planning Assistant" in call_names
        assert "Calendar Manager" in call_names
        assert "Task Manager" in call_names
        assert "Email Processor" in call_names
        assert "Language Processor" in call_names
        assert "Smart Planner" in call_names


@pytest.mark.asyncio
async def test_error_handling_in_tools():
    """Test error handling in tool execution"""
    from tools import create_todoist_tool, create_gmail_tool
    from config import Config
    from agents.tool_context import ToolContext
    from tools.todoist_tool import TodoistResponse
    from tools.gmail_tool import GmailResponse
    
    # Test Todoist tool without API key
    todoist_tool = create_todoist_tool(None)
    ctx = ToolContext(context=None, tool_name="todoist", tool_call_id="1")
    args = json.dumps({"operation_input": {"operation": "create", "task_data": {"title": "Test task"}}})

    result = await todoist_tool.on_invoke_tool(ctx, args)
    assert isinstance(result, TodoistResponse)
    assert result.status == "error"
    assert "not configured" in (result.message or "").lower()
    
    # Test Gmail tool without configuration
    config = Config()
    config.google_client_id = None
    
    gmail_tool = create_gmail_tool(config)
    args = json.dumps({"operation_input": {"operation": "list"}})

    result = await gmail_tool.on_invoke_tool(ctx, args)
    assert isinstance(result, GmailResponse)
    assert result.status == "error"
    assert "not configured" in (result.message or "").lower()


@pytest.mark.asyncio
async def test_calendar_tool_create_event():
    """Test calendar tool creating an event"""
    from tools.calendar_tool import manage_calendar, _manage_calendar_impl
    from models.calendar_tool import CalendarOperation
    
    # Create operation input for creating an event
    operation = CalendarOperation(
        operation="create",
        calendar_name="Calendar",
        event_data={
            "summary": "Test Meeting",
            "start_date": datetime.now().isoformat(),
            "end_date": (datetime.now() + timedelta(hours=1)).isoformat(),
            "description": "Test meeting description"
        }
    )
    
    # Mock subprocess to avoid actual AppleScript execution
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout='Event created successfully',
            stderr=''
        )
        
        # Call the tool implementation directly
        result = await _manage_calendar_impl(operation)
        
        # Check result
        assert result is not None
        assert hasattr(result, 'status')
        assert result.status == "success"
        assert mock_run.called


@pytest.mark.asyncio
async def test_handoff_analytics():
    """Test handoff analytics and recommendations"""
    from agent_modules.handoffs import HandoffCoordinator, _generate_handoff_recommendations
    from config import Config
    
    coordinator = HandoffCoordinator(Config())
    
    # Get initial analytics (should be empty)
    analytics = coordinator.get_handoff_analytics()
    assert analytics["message"] == "No handoffs recorded yet"
    
    # Generate recommendations for empty analytics
    recommendations = _generate_handoff_recommendations(analytics)
    assert len(recommendations) == 1
    assert "No handoffs recorded yet" in recommendations[0]
    
    # Simulate some handoffs
    coordinator.handoff_history = [
        {
            "id": "handoff_1",
            "timestamp": datetime.now().isoformat(),
            "target_agent": "calendar_manager",
            "reason": "Calendar operation",
            "urgency": "normal",
            "context_size": 100,
            "expected_outcome": "Event created"
        },
        {
            "id": "handoff_2",
            "timestamp": datetime.now().isoformat(),
            "target_agent": "calendar_manager",
            "reason": "Calendar query",
            "urgency": "high",
            "context_size": 50,
            "expected_outcome": "Events listed"
        }
    ]
    
    coordinator.agent_workload = {
        "calendar_manager": 2,
        "task_manager": 0
    }
    
    # Get analytics with data
    analytics = coordinator.get_handoff_analytics()
    assert analytics["total_handoffs"] == 2
    assert analytics["agent_usage_distribution"]["calendar_manager"] == 2
    assert analytics["urgency_distribution"]["normal"] == 1
    assert analytics["urgency_distribution"]["high"] == 1
    
    # Generate recommendations
    recommendations = _generate_handoff_recommendations(analytics)
    assert len(recommendations) > 0


@pytest.mark.asyncio
async def test_session_management():
    """Test session management with SQLiteSession"""
    from agents import SQLiteSession
    import tempfile
    import os
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Create session
        session = SQLiteSession(
            session_id="test_session",
            db_path=db_path
        )
        
        assert session is not None
        assert session.session_id == "test_session"
        
    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])