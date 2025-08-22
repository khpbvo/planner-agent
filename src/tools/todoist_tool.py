import json
import os
from typing import List, Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel
try:
    from pydantic import ConfigDict
except Exception:  # pragma: no cover
    ConfigDict = dict  # type: ignore
from agents import function_tool

# Conditional import for Todoist API
try:
    from todoist_api_python.api import TodoistAPI
    TODOIST_AVAILABLE = True
except ImportError:
    TODOIST_AVAILABLE = False

from models.task import TodoistTask, TaskPriority
from models import ToolError


class TodoistOperation(BaseModel):
    """Input for Todoist operations"""
    operation: str  # "list", "create", "update", "complete", "delete"
    task_data: Optional[Any] = None
    task_id: Optional[str] = None
    project_name: Optional[str] = None
    filter_query: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class TodoistResponse(BaseModel):
    """Structured response for Todoist operations"""
    status: str
    message: Optional[str] = None
    tasks: Optional[List[Any]] = None
    task: Optional[Any] = None
    data: Optional[Any] = None

    model_config = ConfigDict(extra="forbid")


# Global API instance
_todoist_api = None

def initialize_todoist_api():
    """Initialize the Todoist API with the API key from environment."""
    global _todoist_api
    if not TODOIST_AVAILABLE:
        return False
        
    api_key = os.getenv("TODOIST_API_KEY")
    if api_key:
        _todoist_api = TodoistAPI(api_key)
        return True
    return False

# Initialize on import
initialize_todoist_api()


# Legacy JSON interface retained for compatibility, but not registered as a tool
async def manage_tasks_json(operation_input: TodoistOperation) -> str:
    """Manage tasks in Todoist (JSON string interface)"""
    try:
        operation = operation_input.operation

        if not _todoist_api:
            return ToolError(
                message="Todoist API key not configured. Please set TODOIST_API_KEY in your .env file",
                code="not_configured",
            ).model_dump_json(indent=2)

        if operation == "list":
            return await list_tasks_json()

        elif operation == "create":
            if not operation_input.task_data:
                return ToolError(message="task_data required for create operation").model_dump_json(indent=2)
            return await create_task_json(_todoist_api, operation_input.task_data)

        elif operation == "update":
            if not operation_input.task_id or not operation_input.task_data:
                return ToolError(message="task_id and task_data required for update operation").model_dump_json(indent=2)
            return await update_task_json(
                _todoist_api,
                operation_input.task_id,
                operation_input.task_data
            )

        elif operation == "complete":
            if not operation_input.task_id:
                return ToolError(message="task_id required for complete operation").model_dump_json(indent=2)
            return await complete_task_json(_todoist_api, operation_input.task_id)

        elif operation == "delete":
            if not operation_input.task_id:
                return ToolError(message="task_id required for delete operation").model_dump_json(indent=2)
            return await delete_task_json(_todoist_api, operation_input.task_id)

        else:
            return ToolError(message=f"Unknown operation: {operation}").model_dump_json(indent=2)

    except Exception as e:
        return ToolError(message=f"Error performing Todoist operation: {str(e)}").model_dump_json(indent=2)


async def manage_tasks(operation_input: TodoistOperation) -> TodoistResponse:
    """Manage tasks in Todoist."""
    operation = operation_input.operation

    try:
        if not _todoist_api:
            return TodoistResponse(
                status="error", 
                message="Todoist API key not configured. Please set TODOIST_API_KEY in your .env file"
            )

        if operation == "list":
            result = await list_tasks_structured()
            return TodoistResponse(status="success", tasks=result["tasks"], data={"total": result["total"]})
        elif operation == "create":
            if not operation_input.task_data:
                return TodoistResponse(status="error", message="task_data required for create operation")
            result = await create_task_structured(_todoist_api, operation_input.task_data)
            return TodoistResponse(status="success", task=result)
        elif operation == "update":
            if not operation_input.task_id or not operation_input.task_data:
                return TodoistResponse(status="error", message="task_id and task_data required for update operation")
            result = await update_task_structured(_todoist_api, operation_input.task_id, operation_input.task_data)
            return TodoistResponse(status="success", data=result)
        elif operation == "complete":
            if not operation_input.task_id:
                return TodoistResponse(status="error", message="task_id required for complete operation")
            result = await complete_task_structured(_todoist_api, operation_input.task_id)
            return TodoistResponse(status="success", data=result)
        elif operation == "delete":
            if not operation_input.task_id:
                return TodoistResponse(status="error", message="task_id required for delete operation")
            result = await delete_task_structured(_todoist_api, operation_input.task_id)
            return TodoistResponse(status="success", data=result)
        else:
            return TodoistResponse(status="error", message=f"Unknown operation: {operation}")
    except Exception as e:
        return TodoistResponse(status="error", message=f"Error performing Todoist operation: {str(e)}")


# Expose a FunctionTool instance for OpenAI Agents SDK
manage_tasks_tool = function_tool(manage_tasks)


def create_todoist_tool(api_key: str):
    """Create the Todoist tool for task management"""
    return manage_tasks


# JSON interface implementations
async def list_tasks_json() -> str:
    """List all tasks (JSON interface)"""
    try:
        tasks = _todoist_api.get_tasks()
        task_list = []
        for task in tasks:
            task_list.append({
                "id": task.id,
                "content": task.content,
                "description": task.description or "",
                "priority": task.priority,
                "due": task.due.string if task.due else None,
                "project_id": task.project_id,
                "is_completed": task.is_completed,
                "created_at": task.created_at
            })
        
        return json.dumps({
            "status": "success",
            "tasks": task_list,
            "total": len(task_list)
        }, indent=2)
    except Exception as e:
        return ToolError(message=f"Failed to list tasks: {str(e)}").model_dump_json(indent=2)


async def create_task_json(api: TodoistAPI, task_data: Dict[str, Any]) -> str:
    """Create a new task (JSON interface)"""
    try:
        task = api.add_task(
            content=task_data.get("content", "New Task"),
            description=task_data.get("description", ""),
            priority=task_data.get("priority", 1),
            due_string=task_data.get("due_string"),
            project_id=task_data.get("project_id")
        )
        
        return json.dumps({
            "status": "success",
            "task": {
                "id": task.id,
                "content": task.content,
                "description": task.description,
                "priority": task.priority,
                "due": task.due.string if task.due else None,
                "project_id": task.project_id
            }
        }, indent=2)
    except Exception as e:
        return ToolError(message=f"Failed to create task: {str(e)}").model_dump_json(indent=2)


async def update_task_json(api: TodoistAPI, task_id: str, task_data: Dict[str, Any]) -> str:
    """Update an existing task (JSON interface)"""
    try:
        api.update_task(
            task_id=task_id,
            content=task_data.get("content"),
            description=task_data.get("description"),
            priority=task_data.get("priority"),
            due_string=task_data.get("due_string")
        )
        
        return json.dumps({
            "status": "success",
            "message": f"Task {task_id} updated successfully",
            "task_id": task_id
        }, indent=2)
    except Exception as e:
        return ToolError(message=f"Failed to update task: {str(e)}").model_dump_json(indent=2)


async def complete_task_json(api: TodoistAPI, task_id: str) -> str:
    """Mark a task as complete (JSON interface)"""
    try:
        api.close_task(task_id=task_id)
        return json.dumps({
            "status": "success",
            "message": f"Task {task_id} marked as complete",
            "task_id": task_id
        }, indent=2)
    except Exception as e:
        return ToolError(message=f"Failed to complete task: {str(e)}").model_dump_json(indent=2)


async def delete_task_json(api: TodoistAPI, task_id: str) -> str:
    """Delete a task (JSON interface)"""
    try:
        api.delete_task(task_id=task_id)
        return json.dumps({
            "status": "success",
            "message": f"Task {task_id} deleted successfully",
            "task_id": task_id
        }, indent=2)
    except Exception as e:
        return ToolError(message=f"Failed to delete task: {str(e)}").model_dump_json(indent=2)


# Structured interface implementations
async def list_tasks_structured() -> Dict[str, Any]:
    """List all tasks (structured interface)"""
    if not _todoist_api:
        # Mock data for when API is not available
        tasks = [
            {
                "id": "task_001",
                "title": "Finish report",
                "description": "Finalize the quarterly report",
                "priority": 1,
                "due_date": (datetime.now()).isoformat(),
            },
            {
                "id": "task_002",
                "title": "Plan meeting",
                "description": "Organize planning meeting for next week",
                "priority": 2,
                "due_date": (datetime.now()).isoformat(),
            },
        ]
        return {"tasks": tasks, "total": len(tasks)}
    
    try:
        tasks = _todoist_api.get_tasks()
        task_list = []
        for task in tasks:
            task_list.append({
                "id": task.id,
                "content": task.content,
                "description": task.description or "",
                "priority": task.priority,
                "due": task.due.string if task.due else None,
                "project_id": task.project_id,
                "is_completed": task.is_completed,
                "created_at": task.created_at
            })
        
        return {"tasks": task_list, "total": len(task_list)}
    except Exception as e:
        return {"tasks": [], "total": 0, "error": str(e)}


async def create_task_structured(api: TodoistAPI, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new task (structured interface)"""
    if not api:
        # Mock response when API is not available
        return {
            "id": "task_new",
            "title": task_data.get("title", "New Task"),
            "description": task_data.get("description", ""),
            "priority": task_data.get("priority", 1),
            "due_date": task_data.get("due_date"),
        }
    
    try:
        task = api.add_task(
            content=task_data.get("content", "New Task"),
            description=task_data.get("description", ""),
            priority=task_data.get("priority", 1),
            due_string=task_data.get("due_string"),
            project_id=task_data.get("project_id")
        )
        
        return {
            "id": task.id,
            "content": task.content,
            "description": task.description,
            "priority": task.priority,
            "due": task.due.string if task.due else None,
            "project_id": task.project_id
        }
    except Exception as e:
        return {"error": str(e)}


async def update_task_structured(api: TodoistAPI, task_id: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing task (structured interface)"""
    if not api:
        return {"task_id": task_id, "updates": task_data}
    
    try:
        api.update_task(
            task_id=task_id,
            content=task_data.get("content"),
            description=task_data.get("description"),
            priority=task_data.get("priority"),
            due_string=task_data.get("due_string")
        )
        return {"task_id": task_id, "updates": task_data}
    except Exception as e:
        return {"task_id": task_id, "error": str(e)}


async def complete_task_structured(api: TodoistAPI, task_id: str) -> Dict[str, Any]:
    """Mark a task as complete (structured interface)"""
    if not api:
        return {"task_id": task_id, "status": "completed"}
    
    try:
        api.close_task(task_id=task_id)
        return {"task_id": task_id, "status": "completed"}
    except Exception as e:
        return {"task_id": task_id, "error": str(e)}


async def delete_task_structured(api: TodoistAPI, task_id: str) -> Dict[str, Any]:
    """Delete a task (structured interface)"""
    if not api:
        return {"task_id": task_id, "status": "deleted"}
    
    try:
        api.delete_task(task_id=task_id)
        return {"task_id": task_id, "status": "deleted"}
    except Exception as e:
        return {"task_id": task_id, "error": str(e)}