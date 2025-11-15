"""
Database models for Kriya Backend
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    """User model for storing user information"""
    
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number = Column(String(20), unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), default="")
    email = Column(String(255), nullable=True)
    token_version = Column(Integer, default=0, nullable=False)  # For JWT revocation
    
    # Plane integration fields
    plane_user_id = Column(String(255), nullable=True)  # Plane's user ID
    plane_api_token = Column(Text, nullable=True)  # Cached Plane API token
    plane_email = Column(String(255), nullable=True)  # Email used in Plane
    plane_workspace_slug = Column(String(100), nullable=True)  # Default workspace
    plane_project_id = Column(String(255), nullable=True)  # Default project
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship with tokens (optional - for audit log only)
    tokens = relationship("Token", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.phone_number}>"


class Token(Base):
    """Token model for authentication tokens"""
    
    __tablename__ = "tokens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship with user
    user = relationship("User", back_populates="tokens")
    
    def __repr__(self):
        return f"<Token {self.token[:20]}...>"
    
    @property
    def is_expired(self):
        """Check if token is expired"""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self):
        """Check if token is valid (active and not expired)"""
        return self.is_active and not self.is_expired

