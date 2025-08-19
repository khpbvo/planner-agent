"""Tool factories with lazy imports and safe stubs.

This module avoids importing heavy/strict-schema tools at import time to ensure
the application can start even if optional integrations aren't configured.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from agents import function_tool


@dataclass
class ToolError:
    """Structured error returned from stub tools."""
    message: str
    suggestion: str = ""
    required_variables: List[str] = field(default_factory=list)
    status: str = "error"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "message": self.message,
            "suggestion": self.suggestion,
            "required_variables": self.required_variables,
        }


def create_calendar_tool():
    """Return the calendar tool (lazy-imports the module)."""
    from .calendar_tool import manage_calendar
    return manage_calendar


def create_nlp_tool(spacy_model: str = "en_core_web_sm"):
    """Return a lightweight NLP tool that doesn't require SpaCy to start.

    The full featured NLP tool can be wired later; this stub extracts a minimal
    intent and an optional naive datetime using simple heuristics.
    """

    @function_tool
    async def process_language(text: str) -> Dict[str, Any]:
        tl = text.lower()
        intent = "general_query"
        if any(k in tl for k in ["schedule", "meeting", "book"]):
            intent = "schedule_event"
        elif any(k in tl for k in ["task", "todo", "remind"]):
            intent = "create_task"
        elif any(k in tl for k in ["what's on", "list", "show"]):
            intent = "query_schedule"

        return {
            "raw_text": text,
            "intent": intent,
            "entities": [],
            "temporal_references": [],
            "people": [],
            "projects": [],
            "locations": [],
            "suggestion": "",
            "required_variables": [],
        }

    return process_language


def create_todoist_tool(api_key: Optional[str]):
    """Return a Todoist tool; if not configured, return a stub that explains it."""
    if not api_key:
        @function_tool
        async def manage_tasks(operation: str) -> ToolError:
            return ToolError(
                message="Todoist not configured",
                suggestion="Set TODOIST_API_KEY in your environment",
                required_variables=["TODOIST_API_KEY"],
        async def manage_tasks(operation: str) -> Dict[str, Any]:
            return ToolError(
                message="Todoist not configured",
                suggestion="Set TODOIST_API_KEY in your environment",
                required_variables=["TODOIST_API_KEY"],
            ).to_dict()

        return manage_tasks

    # Lazy import the real tool only if an API key is present
    from .todoist_tool import manage_tasks as real_manage_tasks
    return real_manage_tasks


def create_gmail_tool(config):
    """Return a Gmail tool; if not configured, return a stub."""
    if not getattr(config, "google_client_id", None):
        @function_tool
        async def manage_emails(operation: str) -> ToolError:
            return ToolError(
                message="Gmail integration not configured",
                required_variables=[
                    "GOOGLE_CLIENT_ID",
                    "GOOGLE_CLIENT_SECRET",
                    "GOOGLE_REDIRECT_URI",
                ],
                suggestion="Configure Gmail OAuth credentials",
            )

        return manage_emails

    from .gmail_tool import manage_emails as real_manage_emails
    return real_manage_emails


__all__ = [
    "ToolError",
    "create_calendar_tool",
    "create_todoist_tool",
    "create_gmail_tool",
    "create_nlp_tool",
]