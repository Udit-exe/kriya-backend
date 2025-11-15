"""
Admin API endpoints for manual configuration
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ..database import get_db
from .. import crud
from ..config import get_settings

router = APIRouter(prefix="/api/admin", tags=["Admin"])
settings = get_settings()


class SetPlaneTokenRequest(BaseModel):
    phone_number: str
    plane_api_token: str
    plane_user_id: Optional[str] = None
    plane_email: Optional[str] = None
    plane_workspace_slug: Optional[str] = None
    plane_project_id: Optional[str] = None


class SetPlaneTokenResponse(BaseModel):
    success: bool
    message: str
    phone_number: str
    plane_user_id: Optional[str] = None


@router.post("/set-plane-token", response_model=SetPlaneTokenResponse)
async def set_plane_token(
    request: SetPlaneTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Manually set Plane API token for a user (for testing)
    
    Request:
    {
        "phone_number": "+1234567890",
        "plane_api_token": "your-plane-api-token-here",
        "plane_user_id": "optional-user-id",
        "plane_email": "optional-email",
        "plane_workspace_slug": "optional-workspace",
        "plane_project_id": "optional-project-id"
    }
    
    This bypasses automatic token generation and sets it directly.
    Useful for testing with pre-generated tokens.
    """
    try:
        # Get user by phone number
        user = crud.get_user_by_phone(db, request.phone_number)
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail=f"User with phone number {request.phone_number} not found. Please onboard first."
            )
        
        # Set Plane token and related fields
        user.plane_api_token = request.plane_api_token
        if request.plane_user_id:
            user.plane_user_id = request.plane_user_id
        if request.plane_email:
            user.plane_email = request.plane_email
        if request.plane_workspace_slug:
            user.plane_workspace_slug = request.plane_workspace_slug
        elif not user.plane_workspace_slug:
            user.plane_workspace_slug = settings.PLANE_WORKSPACE_SLUG
        if request.plane_project_id:
            user.plane_project_id = request.plane_project_id
        elif not user.plane_project_id:
            user.plane_project_id = settings.PLANE_PROJECT_ID
        
        db.commit()
        db.refresh(user)
        
        return SetPlaneTokenResponse(
            success=True,
            message=f"Plane API token set successfully for {request.phone_number}",
            phone_number=user.phone_number,
            plane_user_id=user.plane_user_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Sanitize error message to avoid Unicode encoding issues
        error_msg = str(e).encode('ascii', 'ignore').decode('ascii')
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set Plane token: {error_msg}"
        )

