"""Factories for optional integration tools.

Each factory lazily imports its tool implementation so the main
application can start even when optional dependencies are missing.
The returned callables are fully compliant with the OpenAI Agents SDK
and use Pydantic v2 models for both inputs and outputs.
"""
from typing import Optional


def create_calendar_tool():
    """Return the calendar tool."""
    from .calendar_tool import manage_calendar
    return manage_calendar


def create_nlp_tool(spacy_model: str = "en_core_web_sm"):
    """Return the NLP tool"""
    from .nlp_tool import process_language_tool
    return process_language_tool


def create_todoist_tool(api_key: Optional[str]):
    """Return a Todoist tool; if not configured, return a stub."""
    from agents import function_tool
    from .todoist_tool import TodoistOperation, TodoistResponse

    if not api_key:
        @function_tool
        async def manage_tasks(operation_input: TodoistOperation) -> TodoistResponse:
            return TodoistResponse(
                status="error",
                message="Todoist not configured",
                data={
                    "code": "not_configured",
                    "suggestion": "Set TODOIST_API_KEY in your environment",
                },
            )

        return manage_tasks

    from .todoist_tool import manage_tasks_tool
    return manage_tasks_tool


def create_gmail_tool(config):
    """Return a Gmail tool; if not configured, return a stub."""
    from agents import function_tool
    from .gmail_tool import GmailOperation, GmailResponse

    if not getattr(config, "google_client_id", None):
        @function_tool
        async def manage_emails(operation_input: GmailOperation) -> GmailResponse:
            return GmailResponse(
                status="error",
                message="Gmail integration not configured",
                authenticated=False,
            )

        return manage_emails

    from .gmail_tool import manage_emails as real_manage_emails
    return real_manage_emails


__all__ = [
    "create_calendar_tool",
    "create_todoist_tool",
    "create_gmail_tool",
    "create_nlp_tool",
]
