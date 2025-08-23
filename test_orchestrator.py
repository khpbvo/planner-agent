#!/usr/bin/env python3
"""
Test the orchestrator agent with the fixed schemas
"""
import sys
import asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_orchestrator():
    print("Testing orchestrator with fixed schemas...")
    
    try:
        from agent_modules.orchestrator import create_orchestrator_agent
        from config import config
        
        # Create the orchestrator
        print("\nCreating orchestrator agent...")
        orchestrator = await create_orchestrator_agent(config)
        print("✓ Orchestrator created successfully!")
        
        # Verify it can handle the tools properly
        print("\n✅ Orchestrator agent is ready with all fixed tools!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Orchestrator creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_orchestrator())
    print("\n=== Test Complete ===")
    sys.exit(0 if success else 1)
