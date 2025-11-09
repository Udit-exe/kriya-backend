"""
CRUD operations for database models
"""
import uuid
import jwt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Dict, Optional
from . import models, schemas
from .config import get_settings

settings = get_settings()


def get_user_by_phone(db: Session, phone_number: str) -> models.User | None:
    """Get user by phone number"""
    return db.query(models.User).filter(models.User.phone_number == phone_number).first()


def get_user_by_id(db: Session, user_id: uuid.UUID) -> models.User | None:
    """Get user by ID"""
    return db.query(models.User).filter(models.User.id == user_id).first()


def create_user(db: Session, user_data: schemas.UserRegisterRequest) -> models.User:
    """Create a new user"""
    db_user = models.User(
        phone_number=user_data.phone_number,
        first_name=user_data.first_name,
        last_name=user_data.last_name or "",
        email=user_data.email,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user: models.User, user_data: schemas.UserRegisterRequest) -> models.User:
    """Update existing user information"""
    user.first_name = user_data.first_name
    user.last_name = user_data.last_name or ""
    user.email = user_data.email
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user


def generate_jwt_token(user: models.User) -> tuple[str, datetime]:
    """
    Generate a JWT token for user
    Returns: (token_string, expires_at)
    """
    expires_at = datetime.utcnow() + timedelta(hours=settings.TOKEN_EXPIRY_HOURS)
    
    payload = {
        "user_id": str(user.id),
        "phone_number": user.phone_number,
        "token_version": user.token_version,  # For revocation support
        "exp": expires_at,
        "iat": datetime.utcnow(),
        "iss": "kriya-auth"  # Issuer
    }
    
    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return token, expires_at


def decode_jwt_token(token: str) -> Optional[Dict]:
    """
    Decode and validate JWT token
    Returns: payload dict if valid, None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_signature": True, "verify_exp": True}
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def create_token(db: Session, user: models.User) -> tuple[str, datetime]:
    """
    Create a new JWT authentication token for user
    No database storage needed - JWT is stateless!
    Returns: (token_string, expires_at)
    """
    token_string, expires_at = generate_jwt_token(user)
    return token_string, expires_at


def validate_token_version(user: models.User, token_version: int) -> bool:
    """
    Check if the token version in JWT matches the current user's version
    If user logged out, token_version is incremented, invalidating old tokens
    """
    return user.token_version == token_version


def logout_user(db: Session, user: models.User) -> None:
    """
    Logout user by incrementing token_version
    This invalidates all existing tokens
    """
    user.token_version += 1
    db.commit()
    db.refresh(user)


def get_user_from_jwt(db: Session, token: str) -> Optional[models.User]:
    """
    Extract user from JWT token and validate
    Returns: User object if valid, None if invalid
    """
    # Decode JWT
    payload = decode_jwt_token(token)
    if not payload:
        return None
    
    # Extract user_id and token_version
    user_id = payload.get("user_id")
    token_version = payload.get("token_version", 0)
    
    if not user_id:
        return None
    
    # Get user from database
    user = get_user_by_id(db, uuid.UUID(user_id))
    if not user:
        return None
    
    # Check if token version matches (revocation check)
    if not validate_token_version(user, token_version):
        return None
    
    return user

