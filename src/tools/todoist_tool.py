"""
Todoist integration tool using the Todoist API
"""
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from openai_agents import function_tool
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


# Global API client (will be initialized in create_todoist_tool)
_todoist_api = None

@function_tool
async def manage_tasks(operation_input: TodoistOperation) -> str:
        """
        Manage tasks in Todoist
        
        Args:
            operation_input: Todoist operation details
        """
        if not _todoist_api:
            return "Error: Todoist API key not configured. Please set TODOIST_API_KEY in your .env file"
        
        operation = operation_input.operation
        
        try:
            if operation == "list":
                return await list_tasks(
                    _todoist_api,
                    operation_input.project_name,
                    operation_input.filter_query
                )
            
            elif operation == "create":
                if not operation_input.task_data:
                    return "Error: task_data required for create operation"
                return await create_task(_todoist_api, operation_input.task_data)
            
            elif operation == "update":
                if not operation_input.task_id or not operation_input.task_data:
                    return "Error: task_id and task_data required for update operation"
                return await update_task(
                    _todoist_api,
                    operation_input.task_id,
                    operation_input.task_data
                )
            
            elif operation == "complete":
                if not operation_input.task_id:
                    return "Error: task_id required for complete operation"
                return await complete_task(_todoist_api, operation_input.task_id)
            
            elif operation == "delete":
                if not operation_input.task_id:
                    return "Error: task_id required for delete operation"
                return await delete_task(_todoist_api, operation_input.task_id)
            
            else:
                return f"Unknown operation: {operation}"
                
        except Exception as e:
            return f"Error performing Todoist operation: {str(e)}"
    
def create_todoist_tool(api_key: str):
    """Create the Todoist tool for task management"""
    global _todoist_api
    _todoist_api = TodoistAPI(api_key) if api_key else None
    return manage_tasks


async def list_tasks(
    api: TodoistAPI,
    project_name: Optional[str] = None,
    filter_query: Optional[str] = None
) -> str:
    """List tasks from Todoist with enhanced filtering and project support"""
    
    try:
        # Get all active tasks
        tasks = api.get_tasks()
        projects = api.get_projects()
        
        # Create project mapping for easy lookup
        project_map = {p.id: p.name for p in projects}
        
        # Filter by project if specified
        if project_name:
            project = next((p for p in projects if p.name.lower() == project_name.lower()), None)
            if project:
                tasks = [t for t in tasks if t.project_id == project.id]
            else:
                available_projects = [p.name for p in projects]
                return json.dumps({
                    "error": f"Project '{project_name}' not found",
                    "available_projects": available_projects,
                    "suggestion": "Use one of the available project names"
                }, indent=2)
        
        # Apply advanced filter query
        if filter_query:
            filtered_tasks = []
            query_lower = filter_query.lower()
            
            for task in tasks:
                # Search in content, description, and labels
                matches = (
                    query_lower in task.content.lower() or
                    (task.description and query_lower in task.description.lower()) or
                    any(query_lower in label.lower() for label in task.labels) or
                    (project_map.get(task.project_id, "").lower() == query_lower)
                )
                
                if matches:
                    filtered_tasks.append(task)
            
            tasks = filtered_tasks
        
        # Convert to enhanced format
        task_list = []
        for task in tasks[:50]:  # Increased limit for better usability
            try:
                todoist_task = TodoistTask.from_todoist_response(task.__dict__)
                
                # Enhanced task information
                task_info = {
                    "id": task.id,
                    "title": task.content,
                    "description": task.description or "",
                    "priority": {
                        "value": todoist_task.priority.value,
                        "name": todoist_task.priority.name
                    },
                    "due_date": None,
                    "project": {
                        "id": task.project_id,
                        "name": project_map.get(task.project_id, "Unknown")
                    },
                    "labels": task.labels,
                    "url": task.url,
                    "created_at": task.created_at,
                    "is_completed": task.is_completed
                }
                
                # Handle due date formatting
                if task.due:
                    task_info["due_date"] = {
                        "date": task.due.date,
                        "datetime": task.due.datetime,
                        "string": task.due.string,
                        "is_recurring": task.due.is_recurring
                    }
                
                task_list.append(task_info)
                
            except Exception as task_error:
                # Log individual task processing error but continue
                print(f"Error processing task {task.id}: {task_error}")
                continue
        
        return json.dumps({
            "status": "success",
            "tasks": task_list,
            "total_count": len(task_list),
            "total_available": len(tasks),
            "filter_applied": filter_query is not None,
            "project_filter": project_name
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to retrieve tasks: {str(e)}",
            "suggestion": "Check your Todoist API key and internet connection"
        }, indent=2)


async def create_task(
    api: TodoistAPI,
    task_data: Dict[str, Any]
) -> str:
    """Create a new task in Todoist with enhanced project and label support"""
    
    try:
        # Get projects and labels for validation
        projects = api.get_projects()
        all_labels = api.get_labels()
        
        # Handle project resolution
        project_id = None
        project_name = task_data.get("project_name") or task_data.get("project")
        
        if project_name:
            project = next((p for p in projects if p.name.lower() == project_name.lower()), None)
            if project:
                project_id = project.id
            else:
                return json.dumps({
                    "status": "error",
                    "message": f"Project '{project_name}' not found",
                    "available_projects": [p.name for p in projects],
                    "suggestion": "Use an existing project or create it first in Todoist"
                }, indent=2)
        else:
            # Use provided project_id or default project
            project_id = task_data.get("project_id")
            if not project_id and projects:
                # Use the first project as default
                project_id = projects[0].id
        
        # Handle label validation and creation
        task_labels = task_data.get("labels", [])
        if isinstance(task_labels, str):
            task_labels = [label.strip() for label in task_labels.split(",")]
        
        # Validate labels exist
        existing_labels = {label.name.lower(): label.name for label in all_labels}
        validated_labels = []
        
        for label in task_labels:
            if label.lower() in existing_labels:
                validated_labels.append(existing_labels[label.lower()])
            else:
                # Create new label if it doesn't exist
                try:
                    new_label = api.add_label(name=label)
                    validated_labels.append(new_label.name)
                except:
                    # If label creation fails, skip it
                    print(f"Could not create label: {label}")
        
        # Create enhanced TodoistTask
        task = TodoistTask(
            title=task_data.get("title", "New Task").strip(),
            description=task_data.get("description", "").strip() or None,
            due_date=task_data.get("due_date"),
            priority=TaskPriority(task_data.get("priority", "p4")),
            labels=validated_labels,
            todoist_project_id=project_id
        )
        
        # Convert to Todoist payload
        payload = task.to_todoist_payload()
        
        # Add additional fields that might be in task_data
        if task_data.get("assignee_id"):
            payload["assignee_id"] = task_data["assignee_id"]
        
        if task_data.get("section_id"):
            payload["section_id"] = task_data["section_id"]
            
        if task_data.get("parent_id"):
            payload["parent_id"] = task_data["parent_id"]
        
        # Create task via API
        created_task = api.add_task(**payload)
        
        # Get project name for response
        project_name = next((p.name for p in projects if p.id == created_task.project_id), "Unknown")
        
        return json.dumps({
            "status": "success",
            "task": {
                "id": created_task.id,
                "title": created_task.content,
                "description": created_task.description,
                "project": {
                    "id": created_task.project_id,
                    "name": project_name
                },
                "priority": task.priority.name,
                "labels": created_task.labels,
                "due_date": created_task.due.string if created_task.due else None,
                "url": created_task.url,
                "created_at": created_task.created_at
            },
            "message": f"Task '{created_task.content}' created successfully in project '{project_name}'"
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to create task: {str(e)}",
            "task_data_provided": {
                "title": task_data.get("title"),
                "project": task_data.get("project_name") or task_data.get("project"),
                "priority": task_data.get("priority")
            },
            "suggestion": "Check task title, project name, and priority values"
        }, indent=2)


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