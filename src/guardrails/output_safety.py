"""
Output safety guardrails for the planning assistant
"""
from typing import List
from openai_agents import Agent, Runner, OutputGuardrail, GuardrailFunctionOutput
from pydantic import BaseModel


class OutputSafetyCheck(BaseModel):
    """Output from response safety validation"""
    is_safe: bool
    contains_sensitive_data: bool
    is_helpful: bool
    concerns: List[str]
    reasoning: str


class ResponseQualityCheck(BaseModel):
    """Output from response quality validation"""
    is_relevant_to_planning: bool
    is_actionable: bool
    is_clear: bool
    quality_score: float  # 0.0 to 1.0
    suggestions: List[str]
    reasoning: str


# Output safety validation agent
output_safety_agent = Agent(
    name="Output Safety Validator",
    instructions="""You are validating assistant responses for safety and appropriateness.
    
    Check for:
    - Exposure of sensitive personal information (emails, phone numbers, private details)
    - Inappropriate or harmful content in responses
    - Misleading or incorrect information about calendar events or tasks
    - Responses that could enable harmful automation
    - Privacy violations in shared calendar/task information
    
    Mark as unsafe if the response:
    - Contains or exposes personal/private information inappropriately
    - Provides misleading scheduling or task information
    - Could enable spam, harassment, or misuse
    - Contains inappropriate content or recommendations
    
    Most helpful planning responses should be safe.""",
    output_type=OutputSafetyCheck,
    model="gpt-4o"
)

# Response quality validation agent  
quality_agent = Agent(
    name="Response Quality Validator",
    instructions="""You are evaluating the quality of planning assistant responses.
    
    A good planning response should be:
    - Relevant to calendar, task, or email management
    - Actionable with clear next steps
    - Clear and easy to understand
    - Helpful for the user's planning needs
    
    Rate quality based on:
    - Relevance to planning domain (0.3 weight)
    - Actionability and usefulness (0.4 weight) 
    - Clarity and coherence (0.3 weight)
    
    Provide specific suggestions for improvement when quality is low.""",
    output_type=ResponseQualityCheck,
    model="gpt-4o"
)


async def output_safety_guardrail(ctx, agent, output_data: str):
    """Validate output for safety and privacy"""
    try:
        result = await Runner.run(
            output_safety_agent,
            f"Evaluate this assistant response for safety: {output_data}",
            max_turns=1
        )
        
        safety_output = result.final_output_as(OutputSafetyCheck)
        
        # Block if unsafe or contains sensitive data
        should_block = not safety_output.is_safe or safety_output.contains_sensitive_data
        
        return GuardrailFunctionOutput(
            output_info=safety_output,
            tripwire_triggered=should_block
        )
        
    except Exception as e:
        # Fail safe: block output if validation fails
        return GuardrailFunctionOutput(
            output_info=OutputSafetyCheck(
                is_safe=False,
                contains_sensitive_data=True,
                is_helpful=False,
                concerns=["Safety validation system error"],
                reasoning=f"Output safety check failed: {str(e)}"
            ),
            tripwire_triggered=True
        )


async def response_quality_guardrail(ctx, agent, output_data: str):
    """Validate response quality and relevance"""
    try:
        result = await Runner.run(
            quality_agent,
            f"Evaluate this planning assistant response quality: {output_data}",
            max_turns=1
        )
        
        quality_output = result.final_output_as(ResponseQualityCheck)
        
        # Only flag for very low quality responses
        should_flag = quality_output.quality_score < 0.3
        
        return GuardrailFunctionOutput(
            output_info=quality_output,
            tripwire_triggered=should_flag
        )
        
    except Exception as e:
        # Fail open: allow output if quality check fails
        return GuardrailFunctionOutput(
            output_info=ResponseQualityCheck(
                is_relevant_to_planning=True,
                is_actionable=True,
                is_clear=True,
                quality_score=0.5,
                suggestions=[],
                reasoning=f"Quality check failed, allowing response: {str(e)}"
            ),
            tripwire_triggered=False
        )


def create_output_guardrails() -> List[OutputGuardrail]:
    """Create list of output guardrails for the planning assistant"""
    return [
        OutputGuardrail(
            name="output_safety",
            guardrail_function=output_safety_guardrail
        ),
        OutputGuardrail(
            name="response_quality",
            guardrail_function=response_quality_guardrail
        )
    ]