"""
Orchestrator agent that coordinates between all other agents
"""
from typing import Optional, List
from openai_agents import Agent
from pydantic import BaseModel

from ..tools import (
    create_calendar_tool,
    create_todoist_tool,
    create_gmail_tool,
    create_nlp_tool
)
from ..guardrails import create_input_guardrails, create_output_guardrails


class OrchestratorOutput(BaseModel):
    """Output from the orchestrator agent"""
    message: str
    actions_taken: List[str] = []
    suggestions: List[str] = []
    requires_confirmation: bool = False


async def create_orchestrator_agent(config) -> Agent:
    """
    Create the main orchestrator agent with all sub-agents and tools
    
    Using the pattern where specialized agents are tools of the orchestrator
    """
    
    # Initialize all tools first
    calendar_tool = create_calendar_tool()
    todoist_tool = create_todoist_tool(config.todoist_api_key)
    gmail_tool = create_gmail_tool(config)
    nlp_tool = create_nlp_tool(config.spacy_model)
    
    # Create specialized agents that will be used as tools
    calendar_agent = Agent(
        name="Calendar Manager",
        instructions="""You are responsible for managing calendar events. You can:
        - Check calendar availability
        - Create, update, and delete events
        - Find free time slots
        - Handle event conflicts
        Always confirm with the user before making changes.""",
        tools=[calendar_tool],
        model=config.openai_model
    )
    
    todoist_agent = Agent(
        name="Task Manager", 
        instructions="""You are responsible for managing tasks in Todoist. You can:
        - Create, update, and complete tasks
        - Organize tasks into projects
        - Set priorities and due dates
        - Add labels and comments
        Always confirm task details with the user.""",
        tools=[todoist_tool],
        model=config.openai_model
    )
    
    gmail_agent = Agent(
        name="Email Processor",
        instructions="""You are responsible for processing emails. You can:
        - Read and summarize emails
        - Extract action items from emails
        - Create tasks from email content
        - Flag important emails
        Focus on extracting actionable items.""",
        tools=[gmail_tool],
        model=config.openai_model
    )
    
    nlp_agent = Agent(
        name="Language Processor",
        instructions="""You are responsible for understanding natural language. You:
        - Extract dates, times, and durations
        - Identify people, projects, and locations
        - Parse recurring patterns
        - Understand context and intent
        Provide structured data for other agents to use.""",
        tools=[nlp_tool],
        model=config.openai_model
    )
    
    planning_agent = Agent(
        name="Smart Planner",
        instructions="""You are responsible for intelligent planning. You:
        - Analyze workload and availability
        - Suggest optimal scheduling
        - Balance tasks and events
        - Respect user preferences and working hours
        - Prevent overcommitment
        Consider the user's energy levels and productivity patterns.""",
        model=config.openai_model
    )
    
    # Create guardrails for safety and validation
    input_guardrails = create_input_guardrails()
    output_guardrails = create_output_guardrails()
    
    # Create the main orchestrator agent using agents-as-tools pattern
    orchestrator = Agent(
        name="Planning Assistant",
        instructions="""You are the main planning assistant that helps users manage their:
        - Calendar events (MacOS Calendar)
        - Tasks (Todoist)
        - Emails (Gmail)
        
        Your role is to:
        1. First understand what the user wants using the language processor
        2. Then use the appropriate specialized tool to accomplish the task
        3. Coordinate between multiple tools when needed
        4. Provide clear, actionable responses
        5. Always confirm before making changes that affect user data
        
        Available tools:
        - process_language: For parsing natural language and extracting entities
        - manage_calendar: For all calendar operations
        - manage_tasks: For all Todoist operations
        - manage_emails: For Gmail operations
        - get_planning_advice: For intelligent scheduling suggestions
        
        IMPORTANT GUIDELINES:
        - Always prioritize user privacy and data security
        - Confirm before creating, modifying, or deleting important items
        - Provide helpful, accurate, and relevant planning assistance
        - Stay focused on planning-related tasks
        - Be transparent about what actions you're taking
        
        User preferences and context are maintained across the conversation.
        Be proactive in suggesting improvements to their schedule and task management.""",
        tools=[
            nlp_agent.as_tool(
                tool_name="process_language",
                tool_description="Extract entities, dates, and intent from natural language"
            ),
            calendar_agent.as_tool(
                tool_name="manage_calendar",
                tool_description="Manage calendar events and find available time slots"
            ),
            todoist_agent.as_tool(
                tool_name="manage_tasks",
                tool_description="Create and manage tasks in Todoist"
            ),
            gmail_agent.as_tool(
                tool_name="manage_emails",
                tool_description="Process emails and extract action items"
            ),
            planning_agent.as_tool(
                tool_name="get_planning_advice",
                tool_description="Get intelligent scheduling and planning suggestions"
            )
        ],
        input_guardrails=input_guardrails,
        output_guardrails=output_guardrails,
        model=config.openai_model
    )
    
    return orchestrator