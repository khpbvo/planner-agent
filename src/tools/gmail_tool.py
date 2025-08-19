"""
Gmail integration tool using Google API
"""
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from openai_agents import function_tool
from pydantic import BaseModel
import base64
from email.mime.text import MIMEText


class GmailOperation(BaseModel):
    """Input for Gmail operations"""
    operation: str  # "list", "read", "send", "extract_tasks", "mark_read"
    query: Optional[str] = None  # Search query
    message_id: Optional[str] = None
    email_data: Optional[Dict[str, Any]] = None
    max_results: int = 10


# Global config and auth manager (will be set in create_gmail_tool)
_gmail_config = None
_gmail_auth_manager = None

@function_tool
async def manage_emails(operation_input: GmailOperation) -> str:
        """
        Manage emails in Gmail with full OAuth integration
        
        Args:
            operation_input: Gmail operation details
        """
        operation = operation_input.operation
        
        # Check if Gmail is configured
        if not _gmail_config or not _gmail_config.google_client_id:
            return json.dumps({
                "status": "error",
                "message": "Gmail integration not configured",
                "suggestion": "Please set up Google OAuth credentials in your .env file",
                "required_variables": [
                    "GOOGLE_CLIENT_ID",
                    "GOOGLE_CLIENT_SECRET", 
                    "GOOGLE_REDIRECT_URI"
                ]
            }, indent=2)
        
        # Initialize auth manager if needed
        if not _gmail_auth_manager:
            from ..integrations.gmail_oauth import GmailAuthManager
            global _gmail_auth_manager
            _gmail_auth_manager = GmailAuthManager(_gmail_config)
        
        # Check authentication
        if not _gmail_auth_manager.is_authenticated():
            return json.dumps({
                "status": "error",
                "message": "Gmail authentication required",
                "suggestion": "Run the authentication flow first. This will open a browser window.",
                "action": "authenticate"
            }, indent=2)
        
        try:
            if operation == "list":
                result = await _gmail_auth_manager.list_messages(
                    operation_input.query or "", 
                    operation_input.max_results
                )
                return json.dumps(result, indent=2)
            
            elif operation == "read":
                if not operation_input.message_id:
                    return json.dumps({
                        "status": "error",
                        "message": "message_id required for read operation"
                    }, indent=2)
                    
                result = await _gmail_auth_manager.get_message_content(operation_input.message_id)
                return json.dumps(result, indent=2)
            
            elif operation == "extract_tasks":
                # First get recent emails
                list_result = await _gmail_auth_manager.list_messages(
                    operation_input.query or "is:unread OR newer_than:7d", 
                    min(operation_input.max_results, 20)
                )
                
                if list_result.get("status") == "success":
                    emails = list_result.get("emails", [])
                    action_items = await _gmail_auth_manager.extract_action_items(emails)
                    
                    return json.dumps({
                        "status": "success",
                        "action_items": action_items,
                        "total_emails_scanned": len(emails),
                        "total_actions_found": len(action_items)
                    }, indent=2)
                else:
                    return json.dumps(list_result, indent=2)
            
            elif operation == "mark_read":
                if not operation_input.message_id:
                    return json.dumps({
                        "status": "error",
                        "message": "message_id required for mark_read operation"
                    }, indent=2)
                    
                result = await _gmail_auth_manager.mark_as_read(operation_input.message_id)
                return json.dumps(result, indent=2)
            
            elif operation == "authenticate":
                # Special operation to trigger authentication
                success = _gmail_auth_manager.authenticate()
                if success:
                    return json.dumps({
                        "status": "success",
                        "message": "Gmail authentication completed successfully",
                        "authenticated": True
                    }, indent=2)
                else:
                    return json.dumps({
                        "status": "error", 
                        "message": "Gmail authentication failed",
                        "suggestion": "Check your OAuth credentials and try again"
                    }, indent=2)
            
            else:
                return json.dumps({
                    "status": "error",
                    "message": f"Unknown operation: {operation}",
                    "supported_operations": ["list", "read", "extract_tasks", "mark_read", "authenticate"]
                }, indent=2)
                
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Gmail operation failed: {str(e)}",
                "operation": operation
            }, indent=2)
    
def create_gmail_tool(config):
    """Create the Gmail tool for email management"""
    global _gmail_config
    _gmail_config = config
    return manage_emails


async def list_emails(query: Optional[str] = None, max_results: int = 10) -> str:
    """List emails from Gmail"""
    
    # This is a mock implementation
    # Real implementation would use Google API client
    
    mock_emails = [
        {
            "id": "msg_001",
            "from": "boss@company.com",
            "subject": "Project deadline reminder",
            "snippet": "Please remember the project is due next Friday...",
            "date": "2024-01-15T10:30:00Z"
        },
        {
            "id": "msg_002",
            "from": "client@example.com",
            "subject": "Meeting request for next week",
            "snippet": "Would you be available for a meeting on Tuesday?",
            "date": "2024-01-15T09:15:00Z"
        },
        {
            "id": "msg_003",
            "from": "finance@company.com",
            "subject": "Invoice #12345 - Due Jan 31",
            "snippet": "Please process the attached invoice by the end of the month",
            "date": "2024-01-14T14:20:00Z"
        }
    ]
    
    if query:
        # Simple filter simulation
        mock_emails = [e for e in mock_emails if query.lower() in e["subject"].lower()]
    
    return json.dumps({
        "emails": mock_emails[:max_results],
        "total": len(mock_emails),
        "query": query
    }, indent=2)


async def read_email(message_id: str) -> str:
    """Read a specific email"""
    
    # Mock implementation
    mock_email = {
        "id": message_id,
        "from": "boss@company.com",
        "to": "user@company.com",
        "subject": "Project deadline reminder",
        "body": """Hi,

Just a reminder that the Q1 project deliverables are due next Friday, January 26th.

Please ensure:
1. All documentation is complete
2. Code is reviewed and tested
3. Final presentation is ready

Let me know if you need any help or have concerns about the deadline.

Best regards,
Your Boss""",
        "date": "2024-01-15T10:30:00Z",
        "attachments": []
    }
    
    return json.dumps(mock_email, indent=2)


async def send_email(email_data: Dict[str, Any]) -> str:
    """Send an email via Gmail"""
    
    to = email_data.get("to", "")
    subject = email_data.get("subject", "")
    body = email_data.get("body", "")
    
    # Mock implementation
    # Real implementation would use Gmail API
    
    return json.dumps({
        "success": True,
        "message": f"Email sent to {to}",
        "subject": subject,
        "timestamp": datetime.now().isoformat()
    }, indent=2)


async def extract_tasks_from_emails(query: Optional[str] = None) -> str:
    """Extract actionable tasks from emails"""
    
    # This would use NLP to extract tasks
    # Mock implementation for now
    
    extracted_tasks = [
        {
            "email_id": "msg_001",
            "subject": "Project deadline reminder",
            "task": "Complete Q1 project deliverables",
            "due_date": "2024-01-26",
            "priority": "high"
        },
        {
            "email_id": "msg_002",
            "subject": "Meeting request for next week",
            "task": "Schedule meeting with client",
            "due_date": "2024-01-23",
            "priority": "medium"
        },
        {
            "email_id": "msg_003",
            "subject": "Invoice #12345",
            "task": "Process invoice #12345",
            "due_date": "2024-01-31",
            "priority": "medium"
        }
    ]
    
    return json.dumps({
        "extracted_tasks": extracted_tasks,
        "total": len(extracted_tasks)
    }, indent=2)


async def mark_as_read(message_id: str) -> str:
    """Mark an email as read"""
    
    return json.dumps({
        "success": True,
        "message_id": message_id,
        "status": "marked as read"
    }, indent=2)