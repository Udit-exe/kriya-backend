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
        
        # Generate authentication token
        token = crud.create_token(db, user.id)
        
        return schemas.RegisterResponse(
            success=True,
            message=message,
            token=token.token,
            user=schemas.UserResponse(
                id=str(user.id),
                phone_number=user.phone_number,
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email,
                created_at=user.created_at,
            ),
            expires_at=token.expires_at,
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
    Validate authentication token (called by Plane backend)
    
    Requires API key authentication via X-API-Key header
    """
    try:
        # Get token from database
        token = crud.get_token(db, request.token)
        
        if not token:
            return schemas.ValidateTokenResponse(
                valid=False,
                message="Token not found"
            )
        
        # Check if token is valid
        if not token.is_valid:
            return schemas.ValidateTokenResponse(
                valid=False,
                message="Token is expired or inactive"
            )
        
        # Get user information
        user = crud.get_user_by_id(db, token.user_id)
        
        if not user:
            return schemas.ValidateTokenResponse(
                valid=False,
                message="User not found"
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
    Get user information by token
    """
    # Get and validate token
    db_token = crud.get_token(db, token)
    
    if not db_token or not db_token.is_valid:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # Get user
    user = crud.get_user_by_id(db, db_token.user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
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
    Logout user by invalidating token
    """
    db_token = crud.get_token(db, token)
    
    if not db_token:
        raise HTTPException(status_code=404, detail="Token not found")
    
    crud.invalidate_token(db, db_token)
    
    return {"success": True, "message": "Logged out successfully"}


@router.post("/cleanup-tokens")
async def cleanup_expired_tokens(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_api_key)
):
    """
    Clean up expired tokens (maintenance endpoint)
    
    Requires API key authentication
    """
    count = crud.cleanup_expired_tokens(db)
    return {"success": True, "message": f"Cleaned up {count} expired tokens"}

