"""
Demonstration of Advanced NLP Context Management System

This example shows how the Planning Assistant uses sophisticated NLP 
to understand context, resolve references, and maintain conversation state.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.nlp.context_manager import AdvancedNLPContextManager
from src.tools.nlp_tool import NLPOperation, ContextQuery, create_nlp_tools


async def demo_basic_context_management():
    """Demonstrate basic context tracking across conversation turns"""
    print("🧠 Testing Basic Context Management")
    print("=" * 50)
    
    # Create context manager
    context_manager = AdvancedNLPContextManager()
    
    # Simulate a conversation
    conversation = [
        "I need to schedule a meeting with John tomorrow at 2pm",
        "Actually, make that 3pm instead",  # Reference to previous meeting
        "Also remind me to prepare the presentation for it",  # "it" refers to meeting
        "What time was that meeting again?",  # "that meeting" coreference
        "Can you move it to Friday?",  # "it" still refers to the meeting
    ]
    
    print("📝 Simulated conversation:")
    for i, message in enumerate(conversation, 1):
        print(f"{i}. User: {message}")
    
    print("\n🔍 Processing with context management...")
    
    for i, message in enumerate(conversation):
        print(f"\n--- Turn {i+1} ---")
        print(f"Input: {message}")
        
        # Process turn
        turn = context_manager.process_turn(message)
        
        print(f"Intent: {turn.intent} (confidence: {turn.intent_confidence:.2f})")
        print(f"Entities: {[(e.text, e.label) for e in turn.entities]}")
        
        if turn.resolved_references:
            print(f"Resolved references: {turn.resolved_references}")
    
    # Show final context state
    print(f"\n📊 Final Context Summary:")
    recent_context = context_manager.get_recent_context()
    print(f"- Total turns: {recent_context['turns']}")
    print(f"- Unique entities: {len(set(e['canonical_id'] for e in recent_context['entities']))}")
    print(f"- Active tasks: {len(recent_context['active_tasks'])}")
    print(f"- Temporal references: {len(recent_context['temporal_references'])}")


async def demo_entity_coreference_resolution():
    """Demonstrate entity coreference resolution"""
    print("\n🔗 Testing Entity Coreference Resolution")
    print("=" * 50)
    
    context_manager = AdvancedNLPContextManager()
    
    # Conversation with multiple references to same entities
    messages = [
        "Schedule a meeting with Sarah Johnson from Marketing",
        "Sarah is available Tuesday at 10am",  # Same person, different mention
        "Book a conference room for Sarah's meeting",  # Possessive reference
        "Send the agenda to Ms. Johnson beforehand",  # Formal title reference
        "Make sure the Marketing team lead gets the updates"  # Role-based reference
    ]
    
    for i, message in enumerate(messages):
        print(f"\nTurn {i+1}: {message}")
        turn = context_manager.process_turn(message)
        
        # Show entity resolution
        for entity in turn.entities:
            if entity.label == "PERSON":
                print(f"  Entity: '{entity.text}' → Canonical ID: {entity.canonical_id}")
                if entity.aliases:
                    print(f"  Aliases: {list(entity.aliases)}")
    
    # Show entity context
    print(f"\n🔍 Entity Analysis:")
    sarah_context = context_manager.get_context_for_entity("Sarah")
    if "error" not in sarah_context:
        print(f"- Sarah mentioned {sarah_context['mentions']} times")
        print(f"- Aliases: {sarah_context['aliases']}")
        print(f"- Related entities: {sarah_context['relationships']}")


async def demo_temporal_understanding():
    """Demonstrate temporal expression parsing and resolution"""
    print("\n⏰ Testing Temporal Understanding")
    print("=" * 50)
    
    context_manager = AdvancedNLPContextManager()
    
    temporal_messages = [
        "Schedule the team standup for tomorrow at 9am",
        "Move it to next Tuesday",  # "it" refers to standup, "next Tuesday" is relative
        "Actually, let's do it every Tuesday at the same time",  # Recurring pattern
        "Book the quarterly review for the last Friday of this month",
        "Set a reminder for 30 minutes before that meeting"  # "that meeting" reference
    ]
    
    for i, message in enumerate(temporal_messages):
        print(f"\nTurn {i+1}: {message}")
        turn = context_manager.process_turn(message)
        
        # Show temporal entities and their resolutions
        temporal_entities = [e for e in turn.entities if e.resolved_datetime]
        if temporal_entities:
            for entity in temporal_entities:
                print(f"  '{entity.text}' → {entity.resolved_datetime.strftime('%Y-%m-%d %H:%M')}")
        else:
            print("  No temporal entities resolved")
    
    # Show temporal context state
    temporal_state = context_manager.temporal_context.export_state()
    print(f"\n📅 Temporal Context:")
    print(f"- Reference time: {temporal_state['reference_time']}")
    print(f"- Temporal anchors: {len(temporal_state['temporal_anchors'])}")


async def demo_intent_tracking():
    """Demonstrate intent detection and tracking across turns"""
    print("\n🎯 Testing Intent Tracking")
    print("=" * 50)
    
    context_manager = AdvancedNLPContextManager()
    
    mixed_intent_messages = [
        "What meetings do I have today?",  # query intent
        "Cancel the 3pm call with the client",  # cancel intent  
        "Schedule a replacement for tomorrow",  # schedule intent
        "Don't forget to send the follow-up email",  # task creation intent
        "Actually, let's reschedule that to next week instead"  # reschedule intent
    ]
    
    for i, message in enumerate(mixed_intent_messages):
        print(f"\nTurn {i+1}: {message}")
        turn = context_manager.process_turn(message)
        
        print(f"  Intent: {turn.intent} (confidence: {turn.intent_confidence:.2f})")
    
    # Show intent history and patterns
    intent_context = context_manager.intent_tracker.get_intent_context()
    print(f"\n📈 Intent Analysis:")
    print(f"- Current intent: {intent_context['current_intent']}")
    print(f"- Recent pattern: {intent_context['recent_pattern']}")
    print(f"- Intent history length: {intent_context['intent_history_length']}")


async def demo_tool_integration():
    """Demonstrate integration with the NLP tool functions"""
    print("\n🔧 Testing Tool Integration")
    print("=" * 50)
    
    # Initialize the tools
    tools = create_nlp_tools("en_core_web_lg")
    process_language, query_context = tools
    
    # Test advanced NLP processing
    print("Testing process_language tool with context management...")
    
    nlp_operation = NLPOperation(
        text="Schedule a team retrospective for next Friday at 2pm in the main conference room",
        extract_entities=True,
        extract_temporal=True,
        extract_intent=True,
        extract_context=True,
        resolve_references=True,
        session_id="demo_session"
    )
    
    result = await process_language(nlp_operation)
    print("Result:")
    print(result)
    
    # Test context querying
    print("\n\nTesting query_context tool...")
    
    context_query = ContextQuery(
        query_type="analytics",
        session_id="demo_session"
    )
    
    analytics_result = await query_context(context_query)
    print("Analytics:")
    print(analytics_result)


async def demo_real_conversation_simulation():
    """Simulate a realistic planning conversation"""
    print("\n🗣️  Realistic Conversation Simulation")
    print("=" * 60)
    
    context_manager = AdvancedNLPContextManager()
    
    # Realistic planning conversation
    realistic_conversation = [
        "I need to plan my week. What do I have scheduled?",
        "Okay, so I have the client meeting on Tuesday. Can you move that to Wednesday?",
        "Great. Now I need to schedule time to prepare for it.",
        "Book 2 hours on Tuesday afternoon for presentation prep",
        "Also, remind me to follow up with the proposal we discussed last week",
        "Actually, let's schedule that follow-up call for Thursday morning",
        "And don't let me forget to review the quarterly reports before then",
        "One more thing - can you check if the conference room is free for the Wednesday meeting?",
        "Perfect. Send a calendar update to everyone about the time change"
    ]
    
    print("📱 Planning Assistant Conversation:")
    print("-" * 40)
    
    for i, message in enumerate(realistic_conversation, 1):
        print(f"\n👤 User ({i}): {message}")
        
        # Process with context
        turn = context_manager.process_turn(message)
        
        # Show system understanding
        print(f"🤖 System Understanding:")
        print(f"   Intent: {turn.intent} ({turn.intent_confidence:.1%} confidence)")
        
        if turn.entities:
            print(f"   Entities: {[(e.text, e.label) for e in turn.entities[:3]]}")  # Show first 3
        
        if turn.resolved_references:
            print(f"   Resolved: {turn.resolved_references}")
    
    # Final conversation analysis
    print(f"\n📊 Conversation Analysis:")
    full_context = context_manager.export_conversation_context()
    session_info = full_context["session_info"]
    
    print(f"- Total turns: {session_info['total_turns']}")
    print(f"- Unique entities: {session_info['total_entities']}")
    print(f"- Entity relationships: {session_info['entity_clusters']}")
    print(f"- Duration: {session_info['start_time']} to {session_info['end_time']}")
    
    # Show entity graph
    entity_graph = full_context["entity_graph"]
    print(f"- Connected entities: {len([k for k, v in entity_graph.items() if v])}")


async def main():
    """Run all NLP context management demonstrations"""
    print("🚀 Advanced NLP Context Management Demonstration")
    print("=" * 70)
    print()
    print("This demo shows how the Planning Assistant uses sophisticated")
    print("natural language processing to understand context, resolve") 
    print("references, and maintain conversation state across multiple turns.")
    print()
    
    try:
        await demo_basic_context_management()
        await demo_entity_coreference_resolution()
        await demo_temporal_understanding()
        await demo_intent_tracking()
        await demo_tool_integration()
        await demo_real_conversation_simulation()
        
        print("\n" + "=" * 70)
        print("🎉 All NLP Context Management demonstrations completed!")
        print("\nKey features demonstrated:")
        print("✓ Multi-turn context tracking")
        print("✓ Entity coreference resolution")
        print("✓ Temporal expression parsing") 
        print("✓ Intent detection and tracking")
        print("✓ Reference resolution (pronouns)")
        print("✓ Entity relationship mapping")
        print("✓ Tool integration")
        print("✓ Realistic conversation handling")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())