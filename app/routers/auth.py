"""
Authentication API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional

from .. import crud, schemas, models
from ..database import get_db
from ..config import get_settings

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
settings = get_settings()


def verify_api_key(api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """Verify API key for server-to-server communication"""
    if api_key != settings.PLANE_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return True


@router.post("/register", response_model=schemas.RegisterResponse)
async def register_user(
    user_data: schemas.UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register or login user with phone number
    
    - If user exists: Update info and generate new token (login)
    - If user doesn't exist: Create new user and generate token (register)
    """
    try:
        # Check if user already exists
        existing_user = crud.get_user_by_phone(db, user_data.phone_number)
        
        if existing_user:
            # User exists - update information
            user = crud.update_user(db, existing_user, user_data)
            message = "Login successful"
        else:
            # New user - create account
            user = crud.create_user(db, user_data)
            message = "Registration successful"
        
        # Generate JWT authentication token
        token_string, expires_at = crud.create_token(db, user)
        
        return schemas.RegisterResponse(
            success=True,
            message=message,
            token=token_string,
            user=schemas.UserResponse(
                id=str(user.id),
                phone_number=user.phone_number,
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email,
                created_at=user.created_at,
            ),
            expires_at=expires_at,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/validate-token", response_model=schemas.ValidateTokenResponse)
async def validate_token(
    request: schemas.ValidateTokenRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_api_key)
):
    """
    Validate JWT authentication token (called by Plane backend)
    
    Requires API key authentication via X-API-Key header
    """
    try:
        # Get and validate user from JWT
        user = crud.get_user_from_jwt(db, request.token)
        
        if not user:
            return schemas.ValidateTokenResponse(
                valid=False,
                message="Invalid or expired token"
            )
        
        return schemas.ValidateTokenResponse(
            valid=True,
            user=schemas.UserResponse(
                id=str(user.id),
                phone_number=user.phone_number,
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email,
                created_at=user.created_at,
            ),
            message="Token is valid"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Token validation failed: {str(e)}"
        )


@router.get("/user", response_model=schemas.UserResponse)
async def get_user_info(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Get user information by JWT token
    """
    # Get and validate user from JWT
    user = crud.get_user_from_jwt(db, token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return schemas.UserResponse(
        id=str(user.id),
        phone_number=user.phone_number,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        created_at=user.created_at,
    )


@router.delete("/logout")
async def logout(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Logout user by incrementing token_version
    This invalidates all existing tokens for the user
    """
    # Get user from JWT
    user = crud.get_user_from_jwt(db, token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Increment token version to invalidate all tokens
    crud.logout_user(db, user)
    
    return {"success": True, "message": "Logged out successfully"}



