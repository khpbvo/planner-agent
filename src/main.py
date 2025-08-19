"""
Main entry point for the Planning Assistant
"""
import asyncio
import sys
from pathlib import Path
import logging
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import config
from cli.interface import PlannerCLI
from agent_modules import create_orchestrator_agent


def setup_logging():
    """Configure logging for the application"""
    # Ensure the logs directory exists before configuring logging
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format=log_format,
        handlers=[
            logging.FileHandler(log_dir / "planner.log"),
            logging.StreamHandler()
        ],
        force=True
    )
    
    # Set specific loggers to warning to reduce noise
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    

async def initialize_services():
    """Initialize all services and connections"""
    logger = logging.getLogger(__name__)
    
    # Validate configuration
    if not config.validate_config():
        logger.error("Configuration validation failed")
        return None
        
    logger.info("Initializing Planning Assistant...")
    
    try:
        # Create the orchestrator agent with all sub-agents
        orchestrator = await create_orchestrator_agent(config)
        logger.info("Orchestrator agent initialized successfully")
        
        # TODO: Initialize SpaCy model
        # TODO: Test Todoist connection
        # TODO: Setup Gmail OAuth if configured
        
        return orchestrator
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}", exc_info=True)
        return None


async def main():
    """Main application entry point"""
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Planning Assistant...")
    
    # Initialize services and agents
    orchestrator = await initialize_services()
    
    if not orchestrator:
        logger.error("Failed to initialize. Please check your configuration.")
        sys.exit(1)
    
    # Create and run CLI
    cli = PlannerCLI(orchestrator_agent=orchestrator)
    
    try:
        await cli.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
    finally:
        logger.info("Planning Assistant stopped")


if __name__ == "__main__":
    asyncio.run(main())