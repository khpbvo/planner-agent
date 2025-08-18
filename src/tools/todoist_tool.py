"""
Todoist integration tool using the Todoist API
"""
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from agents import function_tool
from pydantic import BaseModel
from todoist_api_python.api import TodoistAPI

from ..models.task import TodoistTask, TaskPriority


class TodoistOperation(BaseModel):
    """Input for Todoist operations"""
    operation: str  # "list", "create", "update", "complete", "delete"
    task_data: Optional[Dict[str, Any]] = None
    task_id: Optional[str] = None
    project_name: Optional[str] = None
    filter_query: Optional[str] = None  # For advanced filtering


def create_todoist_tool(api_key: str):
    """Create the Todoist tool for task management"""
    
    # Initialize Todoist API client if API key is provided
    api = TodoistAPI(api_key) if api_key else None
    
    @function_tool(
        name_override="manage_tasks",
        description="Manage Todoist tasks - list, create, update, complete, and delete tasks"
    )
    async def manage_tasks(operation_input: TodoistOperation) -> str:
        """
        Manage tasks in Todoist
        
        Args:
            operation_input: Todoist operation details
        """
        if not api:
            return "Error: Todoist API key not configured. Please set TODOIST_API_KEY in your .env file"
        
        operation = operation_input.operation
        
        try:
            if operation == "list":
                return await list_tasks(
                    api,
                    operation_input.project_name,
                    operation_input.filter_query
                )
            
            elif operation == "create":
                if not operation_input.task_data:
                    return "Error: task_data required for create operation"
                return await create_task(api, operation_input.task_data)
            
            elif operation == "update":
                if not operation_input.task_id or not operation_input.task_data:
                    return "Error: task_id and task_data required for update operation"
                return await update_task(
                    api,
                    operation_input.task_id,
                    operation_input.task_data
                )
            
            elif operation == "complete":
                if not operation_input.task_id:
                    return "Error: task_id required for complete operation"
                return await complete_task(api, operation_input.task_id)
            
            elif operation == "delete":
                if not operation_input.task_id:
                    return "Error: task_id required for delete operation"
                return await delete_task(api, operation_input.task_id)
            
            else:
                return f"Unknown operation: {operation}"
                
        except Exception as e:
            return f"Error performing Todoist operation: {str(e)}"
    
    return manage_tasks


async def list_tasks(
    api: TodoistAPI,
    project_name: Optional[str] = None,
    filter_query: Optional[str] = None
) -> str:
    """List tasks from Todoist"""
    
    try:
        # Get all active tasks
        tasks = api.get_tasks()
        
        # Filter by project if specified
        if project_name:
            projects = api.get_projects()
            project = next((p for p in projects if p.name == project_name), None)
            if project:
                tasks = [t for t in tasks if t.project_id == project.id]
            else:
                return f"Project '{project_name}' not found"
        
        # Apply filter query if specified
        if filter_query:
            # This would need more sophisticated filtering logic
            # For now, just filter by content containing the query
            tasks = [t for t in tasks if filter_query.lower() in t.content.lower()]
        
        # Convert to our model and format
        task_list = []
        for task in tasks[:20]:  # Limit to 20 tasks for readability
            todoist_task = TodoistTask.from_todoist_response(task.__dict__)
            task_list.append({
                "id": task.id,
                "title": task.content,
                "priority": todoist_task.priority.value,
                "due": task.due.string if task.due else None,
                "project_id": task.project_id,
                "labels": task.labels
            })
        
        return json.dumps({
            "tasks": task_list,
            "total_count": len(tasks)
        }, indent=2)
        
    except Exception as e:
        return f"Error listing tasks: {str(e)}"


async def create_task(
    api: TodoistAPI,
    task_data: Dict[str, Any]
) -> str:
    """Create a new task in Todoist"""
    
    try:
        # Create TodoistTask from data
        task = TodoistTask(
            title=task_data.get("title", "New Task"),
            description=task_data.get("description"),
            due_date=task_data.get("due_date"),
            priority=TaskPriority(task_data.get("priority", "p4")),
            labels=task_data.get("labels", []),
            todoist_project_id=task_data.get("project_id")
        )
        
        # Convert to Todoist payload
        payload = task.to_todoist_payload()
        
        # Create task via API
        created_task = api.add_task(**payload)
        
        return json.dumps({
            "success": True,
            "task_id": created_task.id,
            "message": f"Task '{created_task.content}' created successfully",
            "url": created_task.url
        }, indent=2)
        
    except Exception as e:
        return f"Error creating task: {str(e)}"


async def update_task(
    api: TodoistAPI,
    task_id: str,
    task_data: Dict[str, Any]
) -> str:
    """Update an existing task"""
    
    try:
        # Prepare update payload
        update_payload = {}
        
        if "title" in task_data:
            update_payload["content"] = task_data["title"]
        
        if "description" in task_data:
            update_payload["description"] = task_data["description"]
        
        if "priority" in task_data:
            priority = TaskPriority(task_data["priority"])
            update_payload["priority"] = int(priority.value[-1])
        
        if "due_date" in task_data:
            if task_data["due_date"]:
                update_payload["due_datetime"] = task_data["due_date"]
            else:
                update_payload["due_string"] = None
        
        if "labels" in task_data:
            update_payload["labels"] = task_data["labels"]
        
        # Update task via API
        api.update_task(task_id=task_id, **update_payload)
        
        return json.dumps({
            "success": True,
            "task_id": task_id,
            "message": "Task updated successfully",
            "updates": update_payload
        }, indent=2)
        
    except Exception as e:
        return f"Error updating task: {str(e)}"


async def complete_task(
    api: TodoistAPI,
    task_id: str
) -> str:
    """Mark a task as complete"""
    
    try:
        api.close_task(task_id=task_id)
        
        return json.dumps({
            "success": True,
            "task_id": task_id,
            "message": "Task completed successfully"
        }, indent=2)
        
    except Exception as e:
        return f"Error completing task: {str(e)}"


async def delete_task(
    api: TodoistAPI,
    task_id: str
) -> str:
    """Delete a task"""
    
    try:
        api.delete_task(task_id=task_id)
        
        return json.dumps({
            "success": True,
            "task_id": task_id,
            "message": "Task deleted successfully"
        }, indent=2)
        
    except Exception as e:
        return f"Error deleting task: {str(e)}"