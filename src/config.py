"""
Configuration management for the Planning Assistant
"""
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config(BaseModel):
    """Application configuration"""
    
    # OpenAI settings
    openai_api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_model: str = Field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o"))
    
    # Todoist settings
    todoist_api_key: str = Field(default_factory=lambda: os.getenv("TODOIST_API_KEY", ""))
    
    # Google/Gmail settings
    google_client_id: str = Field(default_factory=lambda: os.getenv("GOOGLE_CLIENT_ID", ""))
    google_client_secret: str = Field(default_factory=lambda: os.getenv("GOOGLE_CLIENT_SECRET", ""))
    google_redirect_uri: str = Field(default_factory=lambda: os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8080"))
    
    # Application settings
    debug: bool = Field(default_factory=lambda: os.getenv("DEBUG", "False").lower() == "true")
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    session_db_path: str = Field(default_factory=lambda: os.getenv("SESSION_DB_PATH", "data/sessions.db"))
    
    # SpaCy settings
    spacy_model: str = Field(default_factory=lambda: os.getenv("SPACY_MODEL", "en_core_web_lg"))
    
    # Timezone settings
    default_timezone: str = Field(default_factory=lambda: os.getenv("DEFAULT_TIMEZONE", "UTC"))
    
    # Agent settings
    max_agent_turns: int = Field(default=10, description="Maximum turns for agent execution")
    agent_temperature: float = Field(default=0.7, description="Temperature for agent responses")
    enable_tracing: bool = Field(default=True, description="Enable OpenAI tracing")
    
    def validate_config(self) -> bool:
        """Validate that required configuration is present"""
        errors = []
        
        if not self.openai_api_key:
            errors.append("OPENAI_API_KEY is required")
            
        if self.todoist_api_key == "":
            errors.append("Warning: TODOIST_API_KEY not configured")
            
        if self.google_client_id == "":
            errors.append("Warning: Google/Gmail integration not configured")
            
        if errors:
            for error in errors:
                print(f"Configuration: {error}")
            return not any("required" in e for e in errors)
            
        return True
    
    def ensure_directories(self):
        """Ensure required directories exist"""
        # Create data directory for sessions database
        db_path = Path(self.session_db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create logs directory
        Path("logs").mkdir(exist_ok=True)
        
        # Create credentials directory for OAuth tokens
        Path("credentials").mkdir(exist_ok=True)


# Global config instance
config = Config()

# Ensure directories exist
config.ensure_directories()