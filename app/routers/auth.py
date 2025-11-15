"""
Authentication API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Header, Response
from sqlalchemy.orm import Session
from typing import Optional
import secrets
import requests

from .. import crud, schemas, models
from ..database import get_db
from ..config import get_settings
from ..services.plane_client import PlaneClient

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
settings = get_settings()
plane_client = PlaneClient()

# In-memory session store (shared with session router)
# In production, use Redis or database
sessions = {}


def safe_error_message(e: Exception) -> str:
    """Safely convert exception to string, handling Unicode encoding issues"""
    try:
        # Try to get the error message, handling Unicode issues
        try:
            error_str = repr(e)
        except (UnicodeEncodeError, UnicodeDecodeError):
            error_str = f"{type(e).__name__}: {type(e).__qualname__}"
        
        # Try to encode/decode to remove problematic characters
        try:
            return error_str.encode('ascii', 'ignore').decode('ascii')
        except (UnicodeEncodeError, UnicodeDecodeError):
            return f"Error: {type(e).__name__}"
    except Exception:
        # If anything else fails, return generic message
        return f"Error: {type(e).__name__}"


def verify_api_key(api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """Verify API key for server-to-server communication"""
    if api_key != settings.PLANE_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return True


@router.post("/register", response_model=schemas.RegisterResponseNoToken)
async def register_user(
    user_data: schemas.UserRegisterRequest,
    response: Response,
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
        
        # Generate JWT authentication token (internal use only - never sent to frontend)
        token_string, expires_at = crud.create_token(db, user)
        
        # Initialize Plane integration (create/get Plane account and API token)
        # This happens in background - don't fail registration if it fails
        try:
            plane_user_id, api_token = plane_client.get_or_create_user_token(db, user)
            print(f"Plane account initialized for user {user.phone_number}")
        except Exception as e:
            print(f"Warning: Plane integration failed (will retry later): {str(e)}")
            # Continue - user can still use Kriya, Plane integration will happen on first API call
        
        # Authenticate with Plane using Kriya token (server-to-server)
        # This creates Plane session and gets redirect URL
        plane_redirect_url = None
        try:
            # Use the token to authenticate with Plane backend
            plane_auth_url = f"{settings.PLANE_BACKEND_URL}/api/auth/kriya/token/"
            plane_response = requests.post(
                plane_auth_url,
                json={"token": token_string},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if plane_response.status_code == 200:
                plane_data = plane_response.json()
                plane_redirect_url = plane_data.get("redirect_path", "/")
                print(f"Plane authentication successful for user {user.phone_number}")
            else:
                print(f"Warning: Plane authentication failed: {plane_response.status_code}")
        except Exception as e:
            error_msg = safe_error_message(e)
            print(f"Warning: Plane authentication failed: {error_msg}")
            # Continue - user can still use Kriya, Plane integration will happen on first API call
        
        # Create session with httpOnly cookie (token stays server-side)
        session_id = secrets.token_urlsafe(32)
        sessions[session_id] = user.id
        
        # Set httpOnly cookie - token never exposed to frontend
        response.set_cookie(
            key="kriya_session",
            value=session_id,
            httponly=True,
            secure=not settings.DEBUG,  # Only use secure cookies in production
            samesite="lax",
            max_age=86400 * 7  # 7 days
        )
        
        # Return response WITHOUT token - frontend only gets session cookie and redirect URL
        response_data = {
            "success": True,
            "message": message,
            "user": {
                "id": str(user.id),
                "phone_number": user.phone_number,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "created_at": user.created_at.isoformat(),
            }
        }
        
        # Add redirect URL if Plane authentication succeeded
        if plane_redirect_url:
            response_data["redirect_path"] = plane_redirect_url
        
        return response_data
        
    except Exception as e:
        # Safely get error message, handling Unicode encoding issues
        error_msg = safe_error_message(e)
        raise HTTPException(
            status_code=500,
            detail=f"Registration failed: {error_msg}"
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
        # Safely get error message, handling Unicode encoding issues
        error_msg = safe_error_message(e)
        raise HTTPException(
            status_code=500,
            detail=f"Token validation failed: {error_msg}"
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



