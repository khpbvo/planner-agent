"""
Demonstration of the intelligent handoff system

This example shows how the Planning Assistant uses intelligent handoffs
to delegate complex tasks to specialized agents.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

sys.path.insert(0, str(project_root / 'src'))

from config import Config
from agent_modules.orchestrator import create_orchestrator_agent
from agent_modules.handoffs import HandoffRequest, create_handoff_coordinator
from models.context import PlanningContext, EntityContext, UserPreferences
from agents import SQLiteSession, Runner


async def demo_basic_handoffs():
    """Demonstrate basic handoff functionality"""
    print("🔄 Testing Basic Handoff System")
    print("=" * 50)
    
    # Setup
    config = Config()
    coordinator = create_handoff_coordinator(config)
    
    # Simulate different request types
    test_requests = [
        "Schedule a meeting with John tomorrow at 2pm",
        "Create a high-priority task to finish the report by Friday", 
        "Check my emails and extract any action items",
        "Analyze my workload for this week and suggest optimizations",
        "Parse this text: 'Meeting with client next Tuesday at 3pm in downtown office'"
    ]
    
    for request in test_requests:
        print(f"\n📝 Request: {request}")
        
        # Create mock context
        context = PlanningContext(
            session_id="demo_session",
            user_preferences=UserPreferences(),
            entities=EntityContext()
        )
        
        # Analyze handoff need
        handoff_request = coordinator.analyze_handoff_need(context, request)
        
        if handoff_request:
            print(f"🎯 Target Agent: {handoff_request.target_agent}")
            print(f"📋 Reason: {handoff_request.reason}")
            print(f"⚡ Urgency: {handoff_request.urgency}")
            
            # Create the handoff
            handoff = coordinator.create_handoff(handoff_request)
            print(f"✅ Handoff created successfully")
            print(f"📝 Instructions preview: {handoff.instructions[:100]}...")
        else:
            print("⚠️  No handoff needed - can be handled by orchestrator")
    
    # Show analytics
    print(f"\n📊 Handoff Analytics")
    print("-" * 30)
    analytics = coordinator.get_handoff_analytics()
    for key, value in analytics.items():
        print(f"{key}: {value}")


async def demo_full_conversation_handoffs():
    """Demonstrate handoffs in a full conversation"""
    print("\n🗣️  Testing Full Conversation with Handoffs")
    print("=" * 50)
    
    try:
        # Setup
        config = Config()
        orchestrator = await create_orchestrator_agent(config)
        
        # Create session
        session = SQLiteSession(
            session_id="handoff_demo",
            db_path="data/demo_conversations.db"
        )
        
        # Test complex request that should trigger handoffs
        complex_request = """
        I need help organizing my work for next week. Can you:
        1. Check what meetings I have scheduled
        2. Look at my task list in Todoist 
        3. Analyze my recent emails for any urgent items
        4. Create an optimal schedule that balances everything
        """
        
        print(f"📝 Complex Request: {complex_request}")
        print("\n🤖 Processing with handoffs...")
        
        # Process with streaming to see handoffs
        result = Runner.run_streamed(
            orchestrator,
            complex_request,
            session=session,
            max_turns=10
        )
        
        response_text = ""
        handoff_count = 0
        
        # Monitor stream for handoffs
        async for event in result.stream_events():
            if event.type == "agent_updated_stream_event":
                handoff_count += 1
                print(f"🔄 Handoff #{handoff_count}: → {event.new_agent.name}")
            elif event.type == "run_item_stream_event":
                if event.item.type == "tool_call_item":
                    print(f"🔧 Tool Call: {event.item.name}")
        
        # Wait for completion
        final_result = await result
        print(f"\n✅ Conversation completed")
        print(f"🔄 Total handoffs: {handoff_count}")
        print(f"📄 Final response length: {len(str(final_result.final_output))} characters")
        
    except Exception as e:
        print(f"❌ Error in conversation demo: {str(e)}")


async def demo_handoff_patterns():
    """Demonstrate different handoff patterns"""
    print("\n🎭 Testing Handoff Pattern Recognition")
    print("=" * 50)
    
    config = Config()
    coordinator = create_handoff_coordinator(config)
    
    # Test pattern recognition
    patterns = {
        "Calendar Operations": [
            "book a meeting",
            "check my availability", 
            "schedule appointment",
            "what's on my calendar"
        ],
        "Task Management": [
            "create a task",
            "mark as complete",
            "set priority",
            "add to project"
        ],
        "Email Processing": [
            "check emails",
            "send message",
            "extract action items",
            "reply to sender"
        ],
        "Smart Planning": [
            "optimize my schedule",
            "analyze workload",
            "find best time",
            "balance my tasks"
        ],
        "NLP Processing": [
            "extract dates from text",
            "parse this sentence",
            "understand intent",
            "identify entities"
        ]
    }
    
    context = PlanningContext(
        session_id="pattern_demo",
        user_preferences=UserPreferences(),
        entities=EntityContext()
    )
    
    for category, requests in patterns.items():
        print(f"\n📂 {category}")
        print("-" * 20)
        
        for request in requests:
            handoff_request = coordinator.analyze_handoff_need(context, request)
            if handoff_request:
                print(f"✓ '{request}' → {handoff_request.target_agent}")
            else:
                print(f"⚪ '{request}' → orchestrator")


async def main():
    """Run all handoff demonstrations"""
    print("🚀 Intelligent Handoff System Demonstration")
    print("=" * 60)
    
    try:
        await demo_basic_handoffs()
        await demo_handoff_patterns() 
        await demo_full_conversation_handoffs()
        
        print("\n🎉 All demonstrations completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())