"""
Session Management for Kriya Dashboard
Handles user sessions with httpOnly cookies
"""
from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import secrets
import uuid
from datetime import datetime, timedelta

from ..database import get_db
from .. import crud, schemas
from ..config import get_settings

router = APIRouter(prefix="/api/session", tags=["Session"])
settings = get_settings()

# Import shared session store from auth router
# In production, use Redis or database
from ..routers import auth
sessions = auth.sessions


def get_current_user_from_session(
    session_id: Optional[str] = Cookie(None, alias="kriya_session"),
    db: Session = Depends(get_db)
):
    """Get user from session cookie"""
    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_id = sessions.get(session_id)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # Convert string UUID to UUID object if needed
    if isinstance(user_id, str):
        user_id = uuid.UUID(user_id)
    
    user = crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user


@router.post("/login")
async def create_session(
    token: str,  # Kriya JWT token
    db: Session = Depends(get_db),
    response: Response = None
):
    """
    Create session from Kriya JWT token
    Sets httpOnly cookie for secure session management
    """
    # Validate token and get user
    user = crud.get_user_from_jwt(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # Create session
    session_id = secrets.token_urlsafe(32)
    sessions[session_id] = user.id
    
    # Set httpOnly cookie
    response.set_cookie(
        key="kriya_session",
        value=session_id,
        httponly=True,
        secure=not settings.DEBUG,  # Only use secure cookies in production
        samesite="lax",
        max_age=86400 * 7  # 7 days
    )
    
    return {
        "success": True,
        "message": "Session created",
        "user": schemas.UserResponse(
            id=str(user.id),
            phone_number=user.phone_number,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            created_at=user.created_at,
        )
    }


@router.post("/logout")
async def destroy_session(
    user = Depends(get_current_user_from_session),
    session_id: Optional[str] = Cookie(None, alias="kriya_session"),
    response: Response = None
):
    """Destroy session"""
    if session_id and session_id in sessions:
        del sessions[session_id]
    
    response.delete_cookie(key="kriya_session")
    return {"success": True, "message": "Logged out successfully"}


@router.get("/me")
async def get_current_user(
    user = Depends(get_current_user_from_session)
):
    """Get current user from session"""
    return schemas.UserResponse(
        id=str(user.id),
        phone_number=user.phone_number,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        created_at=user.created_at,
    )

