#!/usr/bin/env python3
"""
Simple test script to verify basic functionality.

This file is intended to be run manually and is skipped during automated tests.
"""
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skip("manual verification script")

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Test basic imports
print("Testing basic imports...")

try:
    from agents import Agent, Runner, SQLiteSession
    print("✓ Successfully imported from agents package")
except ImportError as e:
    print(f"✗ Failed to import from agents: {e}")

try:
    import spacy
    nlp = spacy.load("en_core_web_lg")
    print("✓ SpaCy model loaded successfully")
except Exception as e:
    print(f"✗ Failed to load SpaCy model: {e}")

try:
    from config import config
    print(f"✓ Config loaded successfully (OpenAI Model: {config.openai_model})")
except Exception as e:
    print(f"✗ Failed to load config: {e}")

print("\nCreating a simple test agent...")
try:
    from agents import Agent, function_tool
    from pydantic import BaseModel
    
    class TestInput(BaseModel):
        message: str
    
    @function_tool
    async def test_tool(input_data: TestInput) -> str:
        """A simple test tool"""
        return f"Processed: {input_data.message}"
    
    agent = Agent(
        name="Test Agent",
        instructions="You are a test agent that helps verify the system is working.",
        tools=[test_tool],
        model="gpt-5"
    )
    
    print("✓ Test agent created successfully")
    
    # Try a simple run
    import asyncio
    async def test_run():
        from agents import Runner
        result = await Runner.run(
            agent,
            "Hello, this is a test message",
            max_turns=1
        )
        return result
    
    print("\nRunning test agent...")
    result = asyncio.run(test_run())
    print(f"✓ Agent responded: {result.messages[-1].content[:100]}...")
    
except Exception as e:
    print(f"✗ Failed to create/run test agent: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Test Complete ===")