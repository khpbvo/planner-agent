"""
Orchestrator agent that coordinates between all other agents
"""
from typing import Optional, List
from agents import Agent, Runner
from agents.models.openai_responses import ModelSettings
from pydantic import BaseModel

from ..models.context import PlanningContext
from ..tools import (
    create_calendar_tool,
    create_todoist_tool,
    create_gmail_tool,
    create_nlp_tool
)


class OrchestratorOutput(BaseModel):
    """Output from the orchestrator agent"""
    message: str
    actions_taken: List[str] = []
    suggestions: List[str] = []
    requires_confirmation: bool = False


async def create_orchestrator_agent(config) -> Agent:
    """
    Create the main orchestrator agent with all sub-agents and tools
    """
    
    # Create individual agents for each service
    calendar_agent = Agent(
        name="Calendar Manager",
        handoff_description="Manages MacOS Calendar events and scheduling",
        instructions="""You are responsible for managing calendar events. You can:
        - Check calendar availability
        - Create, update, and delete events
        - Find free time slots
        - Handle event conflicts
        Always confirm with the user before making changes.""",
        model_settings=ModelSettings(
            model=config.openai_model,
            temperature=config.agent_temperature
        )
    )
    
    todoist_agent = Agent(
        name="Task Manager", 
        handoff_description="Manages Todoist tasks and projects",
        instructions="""You are responsible for managing tasks in Todoist. You can:
        - Create, update, and complete tasks
        - Organize tasks into projects
        - Set priorities and due dates
        - Add labels and comments
        Always confirm task details with the user.""",
        model_settings=ModelSettings(
            model=config.openai_model,
            temperature=config.agent_temperature
        )
    )
    
    gmail_agent = Agent(
        name="Email Processor",
        handoff_description="Processes Gmail emails and creates tasks from them",
        instructions="""You are responsible for processing emails. You can:
        - Read and summarize emails
        - Extract action items from emails
        - Create tasks from email content
        - Flag important emails
        Focus on extracting actionable items.""",
        model_settings=ModelSettings(
            model=config.openai_model,
            temperature=config.agent_temperature
        )
    )
    
    nlp_agent = Agent(
        name="Language Processor",
        handoff_description="Extracts entities and temporal references from natural language",
        instructions="""You are responsible for understanding natural language. You:
        - Extract dates, times, and durations
        - Identify people, projects, and locations
        - Parse recurring patterns
        - Understand context and intent
        Provide structured data for other agents to use.""",
        model_settings=ModelSettings(
            model=config.openai_model,
            temperature=0.3  # Lower temperature for more consistent extraction
        )
    )
    
    planning_agent = Agent(
        name="Smart Planner",
        handoff_description="Creates intelligent schedules and manages time allocation",
        instructions="""You are responsible for intelligent planning. You:
        - Analyze workload and availability
        - Suggest optimal scheduling
        - Balance tasks and events
        - Respect user preferences and working hours
        - Prevent overcommitment
        Consider the user's energy levels and productivity patterns.""",
        model_settings=ModelSettings(
            model=config.openai_model,
            temperature=config.agent_temperature
        )
    )
    
    # Create the main orchestrator agent
    orchestrator = Agent(
        name="Planning Assistant Orchestrator",
        instructions="""You are the main orchestrator for a planning assistant that helps users manage their:
        - Calendar events (MacOS Calendar)
        - Tasks (Todoist)
        - Emails (Gmail)
        
        Your role is to:
        1. Understand what the user wants to accomplish
        2. Delegate to the appropriate specialized agent
        3. Coordinate between multiple agents when needed
        4. Provide clear, actionable responses
        5. Always confirm before making changes
        
        User preferences and context are maintained across the conversation.
        Be proactive in suggesting improvements to their schedule and task management.
        
        Available agents:
        - Language Processor: For parsing natural language
        - Calendar Manager: For calendar operations
        - Task Manager: For Todoist operations
        - Email Processor: For Gmail operations
        - Smart Planner: For intelligent scheduling suggestions
        
        Always start by using the Language Processor to understand the user's request,
        then delegate to the appropriate agent(s).""",
        handoffs=[
            nlp_agent,
            calendar_agent,
            todoist_agent,
            gmail_agent,
            planning_agent
        ],
        model_settings=ModelSettings(
            model=config.openai_model,
            temperature=config.agent_temperature
        ),
        output_type=OrchestratorOutput
    )
    
    # Add tools to specific agents
    calendar_agent.tools = [create_calendar_tool()]
    todoist_agent.tools = [create_todoist_tool(config.todoist_api_key)]
    gmail_agent.tools = [create_gmail_tool(config)]
    nlp_agent.tools = [create_nlp_tool(config.spacy_model)]
    
    return orchestrator