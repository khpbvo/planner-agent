#!/usr/bin/env python3
"""
Test the main application startup
"""
import sys
import asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_main_startup():
    print("Testing main application startup...")
    
    try:
        from main import initialize_services, setup_logging
        
        # Setup logging
        setup_logging()
        print("✓ Logging configured")
        
        # Initialize services
        orchestrator = await initialize_services()
        if orchestrator:
            print("✓ Services initialized successfully")
            print("✓ Orchestrator agent ready")
            return True
        else:
            print("❌ Failed to initialize services")
            return False
            
    except Exception as e:
        print(f"❌ Startup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_main_startup())
    print("\n=== Startup Test Complete ===")
    sys.exit(0 if success else 1)
