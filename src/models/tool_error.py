from typing import Optional
from pydantic import BaseModel

class ToolError(BaseModel):
    """Standard error format for tool responses"""
    status: str = "error"
    message: str
    code: Optional[str] = None
