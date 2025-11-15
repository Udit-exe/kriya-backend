"""
Onboarding API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ..database import get_db
from ..services.plane_client import PlaneClient
from .. import crud

router = APIRouter(tags=["Onboarding"])
plane_client = PlaneClient()


class OnboardingRequest(BaseModel):
    name: str
    ph_number: str


class OnboardingResponse(BaseModel):
    success: bool
    message: str
    user_id: str
    phone_number: str
    name: str
    already_exists: bool


@router.post("/onboarding", response_model=OnboardingResponse)
async def onboard_user(
    request: OnboardingRequest,
    db: Session = Depends(get_db)
):
    """
    Onboard a new user or return existing user info
    
    Request:
    {
        "name": "John Doe",
        "ph_number": "+1234567890"
    }
    
    Response:
    {
        "success": true,
        "message": "User onboarded successfully" or "User already onboarded",
        "user_id": "uuid",
        "phone_number": "+1234567890",
        "name": "John Doe",
        "already_exists": false or true
    }
    """
    try:
        # Check if user already exists
        existing_user = crud.get_user_by_phone(db, request.ph_number)
        
        if existing_user:
            # User already exists
            return OnboardingResponse(
                success=True,
                message="User already onboarded",
                user_id=str(existing_user.id),
                phone_number=existing_user.phone_number,
                name=f"{existing_user.first_name} {existing_user.last_name}".strip(),
                already_exists=True
            )
        
        # Parse name into first_name and last_name
        name_parts = request.name.strip().split(maxsplit=1)
        first_name = name_parts[0] if name_parts else request.name
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        
        # Create new user in Kriya
        from ..schemas import UserRegisterRequest
        user_data = UserRegisterRequest(
            phone_number=request.ph_number,
            first_name=first_name,
            last_name=last_name,
            email=None
        )
        
        new_user = crud.create_user(db, user_data)
        
        # Initialize Plane integration (creates/caches API token)
        try:
            plane_user_id, api_token = plane_client.get_or_create_user_token(db, new_user)
            print(f"Plane integration initialized for user {new_user.phone_number}")
        except Exception as e:
            print(f"Warning: Plane integration failed: {str(e)}")
            # Continue anyway - user is created in Kriya
        
        return OnboardingResponse(
            success=True,
            message="User onboarded successfully",
            user_id=str(new_user.id),
            phone_number=new_user.phone_number,
            name=f"{new_user.first_name} {new_user.last_name}".strip(),
            already_exists=False
        )
        
    except Exception as e:
        # Sanitize error message to avoid Unicode encoding issues
        error_msg = str(e).encode('ascii', 'ignore').decode('ascii')
        raise HTTPException(
            status_code=500,
            detail=f"Onboarding failed: {error_msg}"
        )

