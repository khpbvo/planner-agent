"""
Input validation guardrails for the planning assistant
"""
from typing import List
from openai_agents import Agent, Runner, InputGuardrail, GuardrailFunctionOutput
from pydantic import BaseModel


class SafetyCheckOutput(BaseModel):
    """Output from safety validation"""
    is_safe: bool
    risk_level: str  # "low", "medium", "high"
    concerns: List[str]
    reasoning: str


class PlanningRequestValidation(BaseModel):
    """Output from planning request validation"""
    is_valid_planning_request: bool
    request_type: str  # "calendar", "task", "email", "general", "invalid"
    confidence: float
    reasoning: str


# Safety validation agent
safety_agent = Agent(
    name="Safety Validator",
    instructions="""You are a safety validator for a planning assistant.
    
    Evaluate user input for:
    - Inappropriate or harmful content
    - Requests to create misleading or fraudulent calendar events
    - Attempts to manipulate or spam email/task systems
    - Privacy violations or sensitive data exposure
    - Malicious automation attempts
    
    Mark as unsafe if the request:
    - Contains personal attacks, harassment, or threats
    - Attempts to create fake meetings or impersonate others
    - Tries to access unauthorized data or systems
    - Contains spam or malicious content
    - Violates basic privacy or security principles
    
    Most legitimate planning requests should be safe.""",
    output_type=SafetyCheckOutput,
    model="gpt-4o"
)

# Planning request validation agent
planning_agent = Agent(
    name="Planning Request Validator", 
    instructions="""You are a request validator for a planning assistant.
    
    Determine if the user input is a valid planning-related request:
    
    VALID request types:
    - "calendar": Scheduling, viewing, or managing calendar events
    - "task": Creating, updating, or managing tasks/todos
    - "email": Reading, processing, or managing emails
    - "general": General planning advice or coordination
    
    INVALID requests:
    - Off-topic conversations unrelated to planning
    - Requests for information outside the planning domain
    - Technical support or general assistance requests
    - Attempts to use the system for non-planning purposes
    
    Be helpful but focused on the planning assistant's purpose.""",
    output_type=PlanningRequestValidation,
    model="gpt-4o"
)


async def safety_guardrail(ctx, agent, input_data: str):
    """Validate input for safety and appropriateness"""
    try:
        result = await Runner.run(
            safety_agent, 
            f"Evaluate this user input for safety: {input_data}",
            max_turns=1
        )
        
        safety_output = result.final_output_as(SafetyCheckOutput)
        
        return GuardrailFunctionOutput(
            output_info=safety_output,
            tripwire_triggered=not safety_output.is_safe
        )
        
    except Exception as e:
        # Fail safe: block if validation fails
        return GuardrailFunctionOutput(
            output_info=SafetyCheckOutput(
                is_safe=False,
                risk_level="high", 
                concerns=["Validation system error"],
                reasoning=f"Safety validation failed: {str(e)}"
            ),
            tripwire_triggered=True
        )


async def planning_request_guardrail(ctx, agent, input_data: str):
    """Validate that input is a legitimate planning request"""
    try:
        result = await Runner.run(
            planning_agent,
            f"Validate this planning request: {input_data}",
            max_turns=1
        )
        
        validation_output = result.final_output_as(PlanningRequestValidation)
        
        # Only trigger tripwire for clearly invalid requests with high confidence
        should_block = (
            not validation_output.is_valid_planning_request and 
            validation_output.confidence > 0.8 and
            validation_output.request_type == "invalid"
        )
        
        return GuardrailFunctionOutput(
            output_info=validation_output,
            tripwire_triggered=should_block
        )
        
    except Exception as e:
        # Fail open: allow request if validation fails (just log the error)
        return GuardrailFunctionOutput(
            output_info=PlanningRequestValidation(
                is_valid_planning_request=True,
                request_type="general",
                confidence=0.0,
                reasoning=f"Validation failed, allowing request: {str(e)}"
            ),
            tripwire_triggered=False
        )


def create_input_guardrails() -> List[InputGuardrail]:
    """Create list of input guardrails for the planning assistant"""
    return [
        InputGuardrail(
            name="safety_check",
            guardrail_function=safety_guardrail
        ),
        InputGuardrail(
            name="planning_validation", 
            guardrail_function=planning_request_guardrail
        )
    ]