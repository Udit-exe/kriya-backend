"""
CRUD operations for database models
"""
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
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


def generate_token() -> str:
    """Generate a unique token"""
    return f"kriya_{uuid.uuid4()}"


def create_token(db: Session, user_id: uuid.UUID) -> models.Token:
    """Create a new authentication token for user"""
    token_string = generate_token()
    expires_at = datetime.utcnow() + timedelta(hours=settings.TOKEN_EXPIRY_HOURS)
    
    db_token = models.Token(
        user_id=user_id,
        token=token_string,
        expires_at=expires_at,
        is_active=True,
    )
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return db_token


def get_token(db: Session, token_string: str) -> models.Token | None:
    """Get token by token string"""
    return db.query(models.Token).filter(models.Token.token == token_string).first()


def invalidate_token(db: Session, token: models.Token) -> None:
    """Invalidate a token"""
    token.is_active = False
    db.commit()


def invalidate_user_tokens(db: Session, user_id: uuid.UUID) -> None:
    """Invalidate all tokens for a user"""
    db.query(models.Token).filter(
        models.Token.user_id == user_id,
        models.Token.is_active == True
    ).update({"is_active": False})
    db.commit()


def cleanup_expired_tokens(db: Session) -> int:
    """Clean up expired tokens from database"""
    result = db.query(models.Token).filter(
        models.Token.expires_at < datetime.utcnow()
    ).delete()
    db.commit()
    return result

