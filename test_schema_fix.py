#!/usr/bin/env python3
"""
Test script to verify the schema fix for calendar and todoist tools
"""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("Testing schema generation for fixed tools...")

try:
    from agents import Agent
    from tools import create_calendar_tool, create_todoist_tool, create_gmail_tool
    from config import config
    
    # Create the tools
    calendar_tool = create_calendar_tool()
    todoist_tool = create_todoist_tool(config.todoist_api_key)
    gmail_tool = create_gmail_tool(config)
    
    # Create test agents to trigger schema generation
    print("\n1. Testing Calendar Agent...")
    calendar_agent = Agent(
        name="Calendar Manager",
        instructions="Test calendar agent",
        tools=[calendar_tool],
        model=config.openai_model
    )
    print("✓ Calendar agent created successfully")
    
    print("\n2. Testing Todoist Agent...")
    todoist_agent = Agent(
        name="Task Manager",
        instructions="Test todoist agent",
        tools=[todoist_tool],
        model=config.openai_model
    )
    print("✓ Todoist agent created successfully")
    
    print("\n3. Testing Gmail Agent...")
    gmail_agent = Agent(
        name="Email Processor",
        instructions="Test gmail agent",
        tools=[gmail_tool],
        model=config.openai_model
    )
    print("✓ Gmail agent created successfully")
    
    print("\n✅ All tools passed schema validation!")
    
except Exception as e:
    print(f"\n❌ Schema validation failed: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Test Complete ===")
