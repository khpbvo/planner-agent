"""
Service status monitoring for all integrations
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import subprocess


class ServiceStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"  
    AUTHENTICATING = "authenticating"
    ERROR = "error"
    NOT_CONFIGURED = "not_configured"


class ServiceStatusManager:
    """Manages status monitoring for all service integrations"""
    
    def __init__(self, config):
        self.config = config
        self._last_checks = {}
        self._status_cache = {}
        self._check_interval = timedelta(minutes=5)
    
    async def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all services"""
        
        services = {
            "calendar": await self._check_calendar_status(),
            "todoist": await self._check_todoist_status(), 
            "gmail": await self._check_gmail_status(),
            "nlp": await self._check_nlp_status()
        }
        
        return services
    
    async def _check_calendar_status(self) -> Dict[str, Any]:
        """Check MacOS Calendar status"""
        try:
            # Test if Calendar app is accessible
            result = subprocess.run(
                ['osascript', '-e', 'tell application "Calendar" to return (name of every calendar)'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                calendars = [cal.strip() for cal in result.stdout.strip().split(',') if cal.strip()]
                return {
                    "status": ServiceStatus.CONNECTED,
                    "message": f"Found {len(calendars)} calendar(s)",
                    "calendars": calendars,
                    "last_check": datetime.now().isoformat()
                }
            else:
                return {
                    "status": ServiceStatus.ERROR,
                    "message": "Could not access Calendar app",
                    "error": result.stderr,
                    "last_check": datetime.now().isoformat()
                }
                
        except subprocess.TimeoutExpired:
            return {
                "status": ServiceStatus.ERROR,
                "message": "Calendar check timed out",
                "last_check": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": ServiceStatus.ERROR,
                "message": f"Calendar status check failed: {str(e)}",
                "last_check": datetime.now().isoformat()
            }
    
    async def _check_todoist_status(self) -> Dict[str, Any]:
        """Check Todoist API status"""
        if not self.config.todoist_api_key:
            return {
                "status": ServiceStatus.NOT_CONFIGURED,
                "message": "TODOIST_API_KEY not configured",
                "last_check": datetime.now().isoformat()
            }
        
        try:
            from todoist_api_python.api import TodoistAPI
            
            api = TodoistAPI(self.config.todoist_api_key)
            
            # Test API connection by getting user info
            user = api.get_current_user()
            projects = api.get_projects()
            
            return {
                "status": ServiceStatus.CONNECTED,
                "message": f"Connected as {user.full_name}",
                "user": {
                    "name": user.full_name,
                    "email": user.email,
                    "id": user.id
                },
                "projects_count": len(projects),
                "last_check": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": ServiceStatus.ERROR,
                "message": f"Todoist API error: {str(e)}",
                "suggestion": "Check your API key in .env file",
                "last_check": datetime.now().isoformat()
            }
    
    async def _check_gmail_status(self) -> Dict[str, Any]:
        """Check Gmail OAuth status"""
        if not all([self.config.google_client_id, self.config.google_client_secret]):
            return {
                "status": ServiceStatus.NOT_CONFIGURED,
                "message": "Google OAuth credentials not configured",
                "missing": [
                    var for var in ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REDIRECT_URI"]
                    if not getattr(self.config, var.lower(), None)
                ],
                "last_check": datetime.now().isoformat()
            }
        
        try:
            from gmail_oauth import GmailAuthManager
            
            auth_manager = GmailAuthManager(self.config)
            
            if auth_manager.is_authenticated():
                # Try a simple API call to verify connection
                result = await auth_manager.list_messages("", 1)
                
                if result.get("status") == "success":
                    return {
                        "status": ServiceStatus.CONNECTED,
                        "message": "Gmail API connected and authenticated",
                        "last_check": datetime.now().isoformat()
                    }
                else:
                    return {
                        "status": ServiceStatus.ERROR,
                        "message": "Gmail API authentication failed",
                        "error": result.get("message"),
                        "last_check": datetime.now().isoformat()
                    }
            else:
                return {
                    "status": ServiceStatus.AUTHENTICATING,
                    "message": "Gmail OAuth authentication required",
                    "action": "Run authentication flow",
                    "last_check": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                "status": ServiceStatus.ERROR,
                "message": f"Gmail status check failed: {str(e)}",
                "last_check": datetime.now().isoformat()
            }
    
    async def _check_nlp_status(self) -> Dict[str, Any]:
        """Check SpaCy NLP status"""
        try:
            import spacy
            
            # Try to load the configured model
            model_name = self.config.spacy_model
            
            try:
                nlp = spacy.load(model_name)
                
                # Test with a simple sentence
                doc = nlp("Schedule a meeting tomorrow at 2pm")
                entities = [(ent.text, ent.label_) for ent in doc.ents]
                
                return {
                    "status": ServiceStatus.CONNECTED,
                    "message": f"SpaCy model '{model_name}' loaded successfully",
                    "model": model_name,
                    "test_entities": entities,
                    "last_check": datetime.now().isoformat()
                }
                
            except OSError:
                # Model not found, try fallback
                try:
                    nlp = spacy.load("en_core_web_sm")
                    return {
                        "status": ServiceStatus.CONNECTED,
                        "message": f"Using fallback model 'en_core_web_sm' (configured: {model_name})",
                        "model": "en_core_web_sm",
                        "suggestion": f"Install {model_name} with: python -m spacy download {model_name}",
                        "last_check": datetime.now().isoformat()
                    }
                except OSError:
                    return {
                        "status": ServiceStatus.ERROR,
                        "message": "No SpaCy models found",
                        "suggestion": "Install a SpaCy model with: python -m spacy download en_core_web_sm",
                        "last_check": datetime.now().isoformat()
                    }
                    
        except ImportError:
            return {
                "status": ServiceStatus.ERROR,
                "message": "SpaCy not installed",
                "suggestion": "Install SpaCy with: pip install spacy",
                "last_check": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": ServiceStatus.ERROR,
                "message": f"NLP status check failed: {str(e)}",
                "last_check": datetime.now().isoformat()
            }
    
    def get_status_summary(self, services: Dict[str, Dict[str, Any]]) -> str:
        """Generate a user-friendly status summary"""
        
        status_icons = {
            ServiceStatus.CONNECTED: "🟢",
            ServiceStatus.DISCONNECTED: "🔴", 
            ServiceStatus.AUTHENTICATING: "🟡",
            ServiceStatus.ERROR: "🔴",
            ServiceStatus.NOT_CONFIGURED: "⚫"
        }
        
        summary_lines = []
        
        for service_name, service_info in services.items():
            status = service_info.get("status", ServiceStatus.ERROR)
            icon = status_icons.get(status, "❓")
            message = service_info.get("message", "Unknown status")
            
            summary_lines.append(f"{icon} {service_name.title()}: {message}")
        
        return "\n".join(summary_lines)