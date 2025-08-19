"""
Basic functionality tests for the Planning Assistant
"""
import asyncio
import pytest
from datetime import datetime, timedelta
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Calendar tool will be imported in the test method
from src.tools.nlp_tool import process_language, NLPOperation, NLPResponse
from src.models.calendar_tool import CalendarOperation, CalendarResponse
from src.models.task import Task, TaskPriority
from src.models.event import CalendarEvent
from src.models.context import EntityContext, TemporalReference


class TestCalendarTool:
    """Test calendar tool functionality"""
    
    @pytest.mark.asyncio
    async def test_calendar_tool_structure(self):
        """Test that calendar tool returns proper JSON structure"""
        from tools.calendar_tool import _manage_calendar_impl
        from models.calendar_tool import CalendarResponse as CR
        
        # Test list operation (should handle gracefully even without calendar access)
        operation = CalendarOperation(
            operation="list",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=1)
        )

        result = await _manage_calendar_impl(operation)
        assert isinstance(result, CR)
        assert result.status in {"success", "error"}


class TestNLPTool:
    """Test NLP processing functionality"""
    
    @pytest.mark.asyncio
    async def test_basic_nlp_processing(self):
        """Test basic NLP processing without SpaCy"""
        
        test_texts = [
            "Schedule a meeting tomorrow at 2pm",
            "Add a task to review the report",
            "What's on my calendar today?",
            "Create a reminder for next Monday"
        ]
        
        for text in test_texts:
            result = await process_language(NLPOperation(text=text))
            assert isinstance(result, NLPResponse)
            assert result.raw_text == text
            assert isinstance(result.temporal_references, list)


class TestPydanticModels:
    """Test Pydantic model functionality"""
    
    def test_task_model(self):
        """Test Task model creation and validation"""
        
        task = Task(
            title="Test Task",
            description="A test task",
            priority=TaskPriority.HIGH,
            due_date=datetime.now() + timedelta(days=1)
        )
        
        assert task.title == "Test Task"
        assert task.priority == TaskPriority.HIGH
        assert task.due_date is not None
        
        # Test natural language conversion
        nl_description = task.to_natural_language()
        assert "Test Task" in nl_description
        assert "Priority: p2" in nl_description
    
    def test_calendar_event_model(self):
        """Test CalendarEvent model creation and validation"""
        
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        
        event = CalendarEvent(
            title="Test Meeting",
            start_time=start_time,
            end_time=end_time,
            location="Conference Room A"
        )
        
        assert event.title == "Test Meeting"
        assert event.duration_minutes == 60
        assert not event.all_day
        
        # Test natural language conversion
        nl_description = event.to_natural_language()
        assert "Test Meeting" in nl_description
        assert "Conference Room A" in nl_description
    
    def test_entity_context_model(self):
        """Test EntityContext model"""
        
        context = EntityContext(
            raw_text="Schedule a meeting with John tomorrow at 2pm",
            mentioned_people=["John"],
            temporal_refs=[
                TemporalReference(
                    original_text="tomorrow at 2pm",
                    parsed_datetime=datetime.now() + timedelta(days=1, hours=14),
                    is_relative=True
                )
            ]
        )
        
        assert context.raw_text == "Schedule a meeting with John tomorrow at 2pm"
        assert "John" in context.mentioned_people
        assert len(context.temporal_refs) == 1
        
        # Test context summary
        summary = context.to_context_summary()
        assert "People: John" in summary


class TestIntegration:
    """Integration tests"""
    
    def test_imports_work(self):
        """Test that all imports work correctly"""
        
        # Test that we can import key modules
        from config import config
        from models.task import Task
        from models.event import CalendarEvent
        from models.context import PlanningContext
        
        # Test that config loads
        assert hasattr(config, 'openai_api_key')
        assert hasattr(config, 'openai_model')
    
    def test_directory_structure(self):
        """Test that required directories exist"""
        
        base_path = os.path.join(os.path.dirname(__file__), '..')
        
        required_dirs = [
            'src',
            'src/tools',
            'src/models',
            'src/cli',
            'src/guardrails',
            'data'
        ]
        
        for dir_path in required_dirs:
            full_path = os.path.join(base_path, dir_path)
            assert os.path.exists(full_path), f"Required directory {dir_path} does not exist"


if __name__ == "__main__":
    # Run basic tests
    pytest.main([__file__, "-v"])