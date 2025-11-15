"""
Task Management API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any

from ..database import get_db
from ..services.plane_client import PlaneClient
from .. import crud

router = APIRouter(tags=["Tasks"])
plane_client = PlaneClient()


class TaskDetails(BaseModel):
    title: str
    description: Optional[str] = ""
    priority: Optional[str] = "medium"  # low, medium, high, urgent
    


class UserMessage(BaseModel):
    task_type: str  # create_task, update_task, list_tasks, etc.
    task_details: TaskDetails


class CreateTaskRequest(BaseModel):
    user_message: UserMessage


class CreateTaskResponse(BaseModel):
    success: bool
    message: str
    task_id: Optional[str] = None
    task_name: Optional[str] = None
    task_url: Optional[str] = None


@router.post("/create_task", response_model=CreateTaskResponse)
async def create_task(
    request: CreateTaskRequest,
    phone_number: str = Header(..., alias="phone_number"),
    db: Session = Depends(get_db)
):
    """
    Create a task via WhatsApp bot or Dashboard
    
    Headers:
    - phone_number: User's phone number
    
    Request Body:
    {
        "user_message": {
            "task_type": "create_task",
            "task_details": {
                "title": "Fix login bug",
                "description": "Users can't login with email",
                "priority": "high"
            }
        }
    }
    
    Response:
    {
        "success": true,
        "message": "Task created successfully",
        "task_id": "uuid",
        "task_name": "Fix login bug",
        "task_url": "http://plane.com/workspace/project/issues/123"
    }
    """
    try:
        # Validate task_type
        if request.user_message.task_type != "create_task":
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported task_type: {request.user_message.task_type}. Only 'create_task' is supported."
            )
        
        # Get user by phone number
        user = crud.get_user_by_phone(db, phone_number)
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail=f"User with phone number {phone_number} not found. Please onboard first via /onboarding"
            )
        
        # Get or create Plane API token for user (creates Plane account if needed)
        try:
            plane_user_id, api_token = plane_client.get_or_create_user_token(db, user)
        except Exception as e:
            # Sanitize error message to avoid Unicode encoding issues
            error_msg = str(e).encode('ascii', 'ignore').decode('ascii')
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize Plane account. Please try again: {error_msg}"
            )
        
        # Prepare task data for Plane
        task_details = request.user_message.task_details
        
        # Map priority to Plane's expected values
        priority_mapping = {
            "low": "low",
            "medium": "medium",
            "high": "high",
            "urgent": "urgent"
        }
        
        plane_task_data = {
            "name": task_details.title,
            "description_html": f"<p>{task_details.description}</p>" if task_details.description else "",
            "priority": priority_mapping.get(task_details.priority.lower(), "medium"),
        }
        
        # Create task in Plane
        workspace_slug = user.plane_workspace_slug
        project_id = user.plane_project_id
        
        if not workspace_slug or not project_id:
            raise HTTPException(
                status_code=500,
                detail="Plane workspace or project not configured. Please contact admin."
            )
        
        plane_task = plane_client.create_task(
            user_api_token=api_token,
            workspace_slug=workspace_slug,
            project_id=project_id,
            task_data=plane_task_data
        )
        
        # Build task URL
        task_url = f"{plane_client.base_url}/{workspace_slug}/projects/{project_id}/issues/{plane_task.get('id')}"
        
        return CreateTaskResponse(
            success=True,
            message=f"Task created successfully: {task_details.title}",
            task_id=str(plane_task.get('id')),
            task_name=task_details.title,
            task_url=task_url
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Sanitize error message to avoid Unicode encoding issues
        error_msg = str(e).encode('ascii', 'ignore').decode('ascii')
        print(f"Error creating task: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create task: {error_msg}"
        )

