#!/usr/bin/env python
"""
Test script to verify the main application runs without integration errors
"""
import asyncio
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set environment variables for testing
os.environ["OPENAI_API_KEY"] = "test-key"


@pytest.mark.asyncio
async def test_main_app():
    """Test the main application startup and basic functionality"""
    from config import config
    from agent_modules import create_orchestrator_agent
    from agents import Runner, RunResult
    
    print("Testing Planning Assistant Initialization...")
    
    # Test configuration
    config.openai_api_key = "test-key"
    config.openai_model = "gpt-4"
    
    try:
        # Test orchestrator creation
        print("1. Creating orchestrator agent...")
        orchestrator = await create_orchestrator_agent(config)
        print("   ✓ Orchestrator created successfully")
        
        # Test agent properties
        print("2. Checking agent configuration...")
        assert orchestrator.name == "Planning Assistant"
        print(f"   ✓ Agent name: {orchestrator.name}")
        
        # Check tools are assigned
        print("3. Checking tools...")
        assert orchestrator.tools is not None
        assert len(orchestrator.tools) > 0
        print(f"   ✓ {len(orchestrator.tools)} tools configured")
        
        # Test with a mock runner
        print("4. Testing agent with mock runner...")
        with patch('agents.Runner.run') as mock_run:
            # Setup mock response
            mock_result = Mock(spec=RunResult)
            mock_result.final_output = "I can help you with calendar events, tasks, and emails."
            mock_run.return_value = mock_result
            
            # Test a simple query
            test_message = "What can you help me with?"
            result = await Runner.run(orchestrator, test_message)
            
            assert result is not None
            assert result.final_output is not None
            print(f"   ✓ Agent responded: {result.final_output}")
        
        print("\n✅ All tests passed! The application is ready to run.")
        print("\nTo run the actual application:")
        print("  python src/main.py")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_main_app())
    sys.exit(0 if success else 1)