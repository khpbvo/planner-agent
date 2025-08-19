"""
Gmail OAuth authentication and API management
"""
import os
import json
import pickle
from typing import Optional, List, Dict, Any
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import base64
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import re


class GmailAuthManager:
    """Manages Gmail OAuth authentication and API operations"""
    
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.modify'
    ]
    
    def __init__(self, config):
        self.config = config
        self.credentials_dir = Path("credentials")
        self.credentials_dir.mkdir(exist_ok=True)
        self.token_file = self.credentials_dir / "gmail_token.pickle"
        self.credentials_file = self.credentials_dir / "gmail_credentials.json"
        self._service = None
        
    def setup_credentials_file(self) -> bool:
        """Create credentials file from environment variables"""
        try:
            if not self.credentials_file.exists():
                credentials_content = {
                    "installed": {
                        "client_id": self.config.google_client_id,
                        "client_secret": self.config.google_client_secret,
                        "redirect_uris": [self.config.google_redirect_uri],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token"
                    }
                }
                
                with open(self.credentials_file, 'w') as f:
                    json.dump(credentials_content, f, indent=2)
                    
            return True
        except Exception as e:
            print(f"Error setting up credentials: {e}")
            return False
    
    def authenticate(self) -> bool:
        """Authenticate with Gmail API"""
        try:
            creds = None
            
            # Load existing token
            if self.token_file.exists():
                with open(self.token_file, 'rb') as token:
                    creds = pickle.load(token)
            
            # If no valid credentials, get new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                    except Exception as e:
                        print(f"Token refresh failed: {e}")
                        creds = None
                
                if not creds:
                    # Setup credentials file
                    if not self.setup_credentials_file():
                        return False
                    
                    if not self.credentials_file.exists():
                        print("Gmail credentials not found. Please set up Google OAuth.")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_file), self.SCOPES
                    )
                    
                    # Run local server for OAuth callback
                    creds = flow.run_local_server(port=8080)
                
                # Save credentials for next run
                with open(self.token_file, 'wb') as token:
                    pickle.dump(creds, token)
            
            # Build the service
            self._service = build('gmail', 'v1', credentials=creds)
            return True
            
        except Exception as e:
            print(f"Gmail authentication failed: {e}")
            return False
    
    @property
    def service(self):
        """Get authenticated Gmail service"""
        if not self._service:
            if not self.authenticate():
                return None
        return self._service
    
    def is_authenticated(self) -> bool:
        """Check if authenticated"""
        return self.service is not None
    
    async def list_messages(self, query: str = "", max_results: int = 10) -> Dict[str, Any]:
        """List Gmail messages"""
        try:
            if not self.service:
                return {"error": "Gmail not authenticated", "authenticated": False}
            
            # Build query with some useful defaults
            if not query:
                query = "is:unread OR (is:inbox newer_than:7d)"
            
            results = self.service.users().messages().list(
                userId='me', 
                q=query, 
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            email_list = []
            for message in messages:
                msg_detail = self.service.users().messages().get(
                    userId='me', 
                    id=message['id'],
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date', 'To']
                ).execute()
                
                headers = msg_detail.get('payload', {}).get('headers', [])
                header_dict = {h['name']: h['value'] for h in headers}
                
                email_info = {
                    "id": message['id'],
                    "thread_id": msg_detail.get('threadId'),
                    "from": header_dict.get('From', ''),
                    "to": header_dict.get('To', ''),
                    "subject": header_dict.get('Subject', ''),
                    "date": header_dict.get('Date', ''),
                    "snippet": msg_detail.get('snippet', ''),
                    "labels": msg_detail.get('labelIds', []),
                    "is_unread": 'UNREAD' in msg_detail.get('labelIds', [])
                }
                
                email_list.append(email_info)
            
            return {
                "status": "success",
                "emails": email_list,
                "total_count": len(email_list),
                "query_used": query
            }
            
        except HttpError as e:
            return {
                "status": "error",
                "message": f"Gmail API error: {e}",
                "suggestion": "Check Gmail API permissions and quotas"
            }
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Failed to list messages: {str(e)}"
            }
    
    async def get_message_content(self, message_id: str) -> Dict[str, Any]:
        """Get full message content"""
        try:
            if not self.service:
                return {"error": "Gmail not authenticated"}
            
            message = self.service.users().messages().get(
                userId='me', 
                id=message_id,
                format='full'
            ).execute()
            
            # Extract headers
            headers = message.get('payload', {}).get('headers', [])
            header_dict = {h['name']: h['value'] for h in headers}
            
            # Extract body
            body = self._extract_message_body(message.get('payload', {}))
            
            return {
                "status": "success",
                "message": {
                    "id": message_id,
                    "thread_id": message.get('threadId'),
                    "from": header_dict.get('From', ''),
                    "to": header_dict.get('To', ''),
                    "subject": header_dict.get('Subject', ''),
                    "date": header_dict.get('Date', ''),
                    "body": body,
                    "labels": message.get('labelIds', []),
                    "is_unread": 'UNREAD' in message.get('labelIds', [])
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get message: {str(e)}"
            }
    
    def _extract_message_body(self, payload: Dict[str, Any]) -> str:
        """Extract text content from message payload"""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain':
                    data = part.get('body', {}).get('data')
                    if data:
                        body += base64.urlsafe_b64decode(data).decode('utf-8')
                elif part.get('mimeType') == 'text/html' and not body:
                    # Fallback to HTML if no plain text
                    data = part.get('body', {}).get('data')
                    if data:
                        html_content = base64.urlsafe_b64decode(data).decode('utf-8')
                        # Basic HTML tag removal
                        body += re.sub('<[^<]+?>', '', html_content)
        else:
            # Simple message structure
            if payload.get('mimeType') == 'text/plain':
                data = payload.get('body', {}).get('data')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
        
        return body.strip()
    
    async def extract_action_items(self, emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract potential action items from emails"""
        action_items = []
        
        # Common action patterns
        action_patterns = [
            r'please\s+(.*?)(?:\.|$)',
            r'can\s+you\s+(.*?)(?:\.|$)', 
            r'need\s+to\s+(.*?)(?:\.|$)',
            r'remember\s+to\s+(.*?)(?:\.|$)',
            r'don\'t\s+forget\s+to\s+(.*?)(?:\.|$)',
            r'action\s+required:\s+(.*?)(?:\.|$)',
            r'todo:\s+(.*?)(?:\.|$)',
            r'deadline:\s+(.*?)(?:\.|$)',
            r'due\s+(.*?)(?:\.|$)'
        ]
        
        for email in emails:
            email_id = email.get('id', '')
            subject = email.get('subject', '')
            snippet = email.get('snippet', '')
            from_email = email.get('from', '')
            
            # Look for action patterns in subject and snippet
            text_to_search = f"{subject} {snippet}".lower()
            
            for pattern in action_patterns:
                matches = re.finditer(pattern, text_to_search, re.IGNORECASE)
                for match in matches:
                    action_text = match.group(1).strip()
                    
                    if len(action_text) > 5:  # Filter out very short matches
                        action_items.append({
                            "email_id": email_id,
                            "from": from_email,
                            "subject": subject,
                            "action": action_text,
                            "priority": "medium",
                            "extracted_pattern": pattern
                        })
        
        return action_items
    
    async def mark_as_read(self, message_id: str) -> Dict[str, Any]:
        """Mark message as read"""
        try:
            if not self.service:
                return {"error": "Gmail not authenticated"}
            
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            
            return {
                "status": "success",
                "message_id": message_id,
                "action": "marked as read"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to mark as read: {str(e)}"
            }