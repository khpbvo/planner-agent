"""
Intelligent agent handoff system for the Planning Assistant

Implements the OpenAI Agents SDK handoff pattern for seamless delegation
between specialized agents based on context and task complexity.
"""
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from agents import Agent, function_tool, Handoff
from pydantic import BaseModel
import json

from models.context import PlanningContext, EntityContext
from config import Config


class HandoffRequest(BaseModel):
    """Request for agent handoff"""
    reason: str  # Why handoff is needed
    target_agent: str  # Which agent to hand off to
    context: Dict[str, Any]  # Context to pass along
    urgency: str = "normal"  # "low", "normal", "high", "critical"
    expected_outcome: Optional[str] = None


class HandoffResponse(BaseModel):
    """Response from handoff system"""
    success: bool
    target_agent: str
    handoff_id: str
    message: str
    context_preserved: bool
    estimated_completion: Optional[str] = None


class AgentCapabilities(BaseModel):
    """Defines what each agent can handle"""
    agent_name: str
    primary_functions: List[str]
    data_sources: List[str]
    complexity_level: str  # "simple", "moderate", "complex", "expert"
    typical_duration: str  # "seconds", "minutes", "extended"
    prerequisites: List[str] = []


class HandoffCoordinator:
    """Coordinates intelligent handoffs between agents"""
    
    def __init__(self, config: Config):
        self.config = config
        self.handoff_history: List[Dict[str, Any]] = []
        self.agent_workload: Dict[str, int] = {}
        
        # Define agent capabilities
        self.capabilities = {
            "nlp_processor": AgentCapabilities(
                agent_name="Language Processor",
                primary_functions=["entity_extraction", "intent_analysis", "temporal_parsing"],
                data_sources=["user_input", "text_content"],
                complexity_level="simple",
                typical_duration="seconds"
            ),
            "calendar_manager": AgentCapabilities(
                agent_name="Calendar Manager",
                primary_functions=["event_management", "scheduling", "availability_check"],
                data_sources=["macos_calendar"],
                complexity_level="moderate",
                typical_duration="minutes",
                prerequisites=["calendar_access"]
            ),
            "task_manager": AgentCapabilities(
                agent_name="Task Manager", 
                primary_functions=["task_crud", "project_management", "priority_setting"],
                data_sources=["todoist_api"],
                complexity_level="moderate",
                typical_duration="minutes",
                prerequisites=["todoist_auth"]
            ),
            "email_processor": AgentCapabilities(
                agent_name="Email Processor",
                primary_functions=["email_reading", "action_extraction", "email_sending"],
                data_sources=["gmail_api"],
                complexity_level="moderate", 
                typical_duration="minutes",
                prerequisites=["gmail_oauth"]
            ),
            "smart_planner": AgentCapabilities(
                agent_name="Smart Planner",
                primary_functions=["optimal_scheduling", "workload_analysis", "conflict_resolution"],
                data_sources=["calendar", "tasks", "preferences"],
                complexity_level="complex",
                typical_duration="extended",
                prerequisites=["calendar_access", "task_data"]
            )
        }
    
    def analyze_handoff_need(self, 
                           current_context: PlanningContext, 
                           user_request: str,
                           current_agent: str = "orchestrator") -> Optional[HandoffRequest]:
        """Analyze if a handoff is needed based on context"""
        
        # Extract key entities and intents
        entities = current_context.entities
        
        # Determine if specialized agent is needed
        target_agent = self._determine_target_agent(user_request, entities, current_agent)
        
        if target_agent and target_agent != current_agent:
            # Calculate urgency
            urgency = self._calculate_urgency(user_request, entities)
            
            # Prepare context for handoff
            handoff_context = {
                "original_request": user_request,
                "extracted_entities": entities.model_dump() if entities else {},
                "user_preferences": current_context.preferences.model_dump() if current_context.preferences else {},
                "session_id": current_context.session_id,
                "timestamp": datetime.now().isoformat()
            }
            
            return HandoffRequest(
                reason=f"Request requires specialized {target_agent} capabilities",
                target_agent=target_agent,
                context=handoff_context,
                urgency=urgency,
                expected_outcome=f"Handled by {target_agent} specialist"
            )
        
        return None
    
    def _determine_target_agent(self, 
                              request: str, 
                              entities: Optional[EntityContext],
                              current_agent: str) -> Optional[str]:
        """Determine which agent should handle the request"""
        
        request_lower = request.lower()
        
        # Calendar-related requests
        if any(word in request_lower for word in [
            "calendar", "schedule", "meeting", "appointment", "event",
            "available", "free time", "book", "tomorrow", "today", "next week"
        ]):
            return "calendar_manager"
        
        # Task management requests
        elif any(word in request_lower for word in [
            "task", "todo", "project", "deadline", "priority", "complete",
            "assign", "todoist", "work", "finish", "due"
        ]):
            return "task_manager"
        
        # Email-related requests
        elif any(word in request_lower for word in [
            "email", "mail", "inbox", "send", "reply", "gmail", 
            "message", "unread", "action items"
        ]):
            return "email_processor"
        
        # Complex planning requests
        elif any(word in request_lower for word in [
            "plan", "optimize", "best time", "schedule everything",
            "workload", "organize", "distribute", "balance"
        ]):
            return "smart_planner"
        
        # NLP processing requests
        elif any(word in request_lower for word in [
            "extract", "analyze", "understand", "parse", "interpret"
        ]):
            return "nlp_processor"
        
        return None
    
    def _calculate_urgency(self, request: str, entities: Optional[EntityContext]) -> str:
        """Calculate urgency level for the handoff"""
        
        request_lower = request.lower()
        
        # High urgency indicators
        if any(word in request_lower for word in [
            "urgent", "asap", "immediately", "now", "emergency", "critical"
        ]):
            return "critical"
        
        # Time-sensitive indicators
        elif any(word in request_lower for word in [
            "today", "deadline", "due", "overdue", "soon"
        ]):
            return "high"
        
        # Future planning
        elif any(word in request_lower for word in [
            "next week", "later", "eventually", "someday"
        ]):
            return "low"
        
        return "normal"
    
    def create_handoff(self, request: HandoffRequest) -> Handoff:
        """Create an OpenAI Agents SDK Handoff object"""
        
        capabilities = self.capabilities.get(request.target_agent)
        if not capabilities:
            raise ValueError(f"Unknown agent: {request.target_agent}")
        
        # Create handoff instructions
        instructions = self._generate_handoff_instructions(request, capabilities)
        
        # Create the handoff
        handoff = Handoff(
            agent=request.target_agent,
            instructions=instructions,
            context=request.context
        )
        
        # Record handoff
        self._record_handoff(request, handoff)
        
        return handoff
    
    def _generate_handoff_instructions(self, 
                                     request: HandoffRequest, 
                                     capabilities: AgentCapabilities) -> str:
        """Generate specific instructions for the target agent"""
        
        base_instruction = f"""
You are being handed off to handle a {request.urgency} priority request.

CONTEXT:
- Original request: {request.context.get('original_request', 'N/A')}
- Handoff reason: {request.reason}
- Your capabilities: {', '.join(capabilities.primary_functions)}
- Expected duration: {capabilities.typical_duration}

TASK:
Please handle this request using your specialized capabilities. Focus on:
1. Addressing the specific user need
2. Utilizing your primary functions: {', '.join(capabilities.primary_functions)}
3. Returning clear, actionable results

CONTEXT DATA:
{json.dumps(request.context, indent=2)}
"""
        
        # Add urgency-specific instructions
        if request.urgency == "critical":
            base_instruction += "\n⚠️ CRITICAL PRIORITY: Handle immediately with minimal delay."
        elif request.urgency == "high":
            base_instruction += "\n🔥 HIGH PRIORITY: Prioritize this request."
        
        # Add expected outcome if specified
        if request.expected_outcome:
            base_instruction += f"\n\nEXPECTED OUTCOME: {request.expected_outcome}"
        
        return base_instruction.strip()
    
    def _record_handoff(self, request: HandoffRequest, handoff: Handoff):
        """Record handoff for tracking and analysis"""
        
        handoff_record = {
            "id": f"handoff_{len(self.handoff_history) + 1}",
            "timestamp": datetime.now().isoformat(),
            "target_agent": request.target_agent,
            "reason": request.reason,
            "urgency": request.urgency,
            "context_size": len(str(request.context)),
            "expected_outcome": request.expected_outcome
        }
        
        self.handoff_history.append(handoff_record)
        
        # Update agent workload
        self.agent_workload[request.target_agent] = self.agent_workload.get(request.target_agent, 0) + 1
    
    def get_handoff_analytics(self) -> Dict[str, Any]:
        """Get analytics on handoff patterns"""
        
        if not self.handoff_history:
            return {"message": "No handoffs recorded yet"}
        
        # Agent usage distribution
        agent_usage = {}
        urgency_distribution = {}
        
        for handoff in self.handoff_history:
            agent = handoff["target_agent"]
            urgency = handoff["urgency"]
            
            agent_usage[agent] = agent_usage.get(agent, 0) + 1
            urgency_distribution[urgency] = urgency_distribution.get(urgency, 0) + 1
        
        # Most efficient handoffs (quick resolution)
        recent_handoffs = self.handoff_history[-10:] if len(self.handoff_history) > 10 else self.handoff_history
        
        return {
            "total_handoffs": len(self.handoff_history),
            "agent_usage_distribution": agent_usage,
            "urgency_distribution": urgency_distribution,
            "current_workload": self.agent_workload,
            "recent_handoff_count": len(recent_handoffs),
            "most_used_agent": max(agent_usage.items(), key=lambda x: x[1])[0] if agent_usage else None
        }


# Function tools for handoff management
@function_tool(strict_json_schema=False)
async def request_agent_handoff(handoff_request: HandoffRequest) -> str:
    """Request a handoff to a specialized agent"""
    
    coordinator = HandoffCoordinator(Config())
    
    try:
        # Validate target agent exists
        if handoff_request.target_agent not in coordinator.capabilities:
            return json.dumps({
                "status": "error",
                "message": f"Unknown target agent: {handoff_request.target_agent}",
                "available_agents": list(coordinator.capabilities.keys())
            }, indent=2)
        
        # Create the handoff
        handoff = coordinator.create_handoff(handoff_request)
        
        # Return handoff information
        return json.dumps({
            "status": "success", 
            "message": f"Handoff created to {handoff_request.target_agent}",
            "handoff_details": {
                "target_agent": handoff_request.target_agent,
                "reason": handoff_request.reason,
                "urgency": handoff_request.urgency,
                "context_preserved": True,
                "instructions_length": len(handoff.instructions)
            }
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Handoff creation failed: {str(e)}",
            "target_agent": handoff_request.target_agent
        }, indent=2)


@function_tool(strict_json_schema=False)
async def analyze_handoff_patterns() -> str:
    """Analyze handoff patterns and efficiency"""
    
    coordinator = HandoffCoordinator(Config())
    analytics = coordinator.get_handoff_analytics()
    
    return json.dumps({
        "status": "success",
        "analytics": analytics,
        "recommendations": _generate_handoff_recommendations(analytics)
    }, indent=2)


def _generate_handoff_recommendations(analytics: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on handoff analytics"""
    
    recommendations = []
    
    if analytics.get("total_handoffs", 0) == 0:
        recommendations.append("No handoffs recorded yet - system running in basic mode")
        return recommendations
    
    # High usage agent recommendations
    agent_usage = analytics.get("agent_usage_distribution", {})
    if agent_usage:
        most_used = max(agent_usage.items(), key=lambda x: x[1])
        if most_used[1] > 10:
            recommendations.append(f"High usage of {most_used[0]} - consider optimizing this agent")
    
    # Urgency pattern recommendations  
    urgency_dist = analytics.get("urgency_distribution", {})
    critical_count = urgency_dist.get("critical", 0)
    if critical_count > 5:
        recommendations.append("High number of critical handoffs - review planning processes")
    
    # Workload balance recommendations
    workload = analytics.get("current_workload", {})
    if workload:
        max_load = max(workload.values())
        min_load = min(workload.values())
        if max_load > min_load * 3:
            recommendations.append("Uneven agent workload detected - consider load balancing")
    
    if not recommendations:
        recommendations.append("Handoff patterns look healthy")
    
    return recommendations


def create_handoff_coordinator(config: Config) -> HandoffCoordinator:
    """Create handoff coordinator instance"""
    return HandoffCoordinator(config)


def create_handoff_tools():
    """Create handoff management tools"""
    return [request_agent_handoff, analyze_handoff_patterns]