"""
Pydantic schemas for request/response validation
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re


class UserRegisterRequest(BaseModel):
    """Schema for user registration request"""
    
    phone_number: str = Field(..., description="User's phone number with country code")
    first_name: str = Field(..., min_length=1, max_length=100, description="User's first name")
    last_name: Optional[str] = Field("", max_length=100, description="User's last name")
    email: Optional[str] = Field(None, description="User's email (optional)")
    
    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v):
        """Validate phone number format"""
        # Remove spaces and dashes
        phone = v.replace(" ", "").replace("-", "")
        
        # Basic validation: should start with + and contain only digits after that
        if not re.match(r'^\+\d{10,15}$', phone):
            raise ValueError('Phone number must be in format +1234567890 (10-15 digits with country code)')
        
        return phone
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """Validate email format if provided"""
        if v and v.strip():
            email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_regex, v):
                raise ValueError('Invalid email format')
        return v


class UserResponse(BaseModel):
    """Schema for user response"""
    
    id: str
    phone_number: str
    first_name: str
    last_name: str
    email: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Schema for token response"""
    
    token: str
    expires_at: datetime


class RegisterResponse(BaseModel):
    """Schema for registration response"""
    
    success: bool = True
    message: str
    token: str
    user: UserResponse
    expires_at: datetime


class ValidateTokenRequest(BaseModel):
    """Schema for token validation request"""
    
    token: str = Field(..., description="Authentication token to validate")
    api_key: Optional[str] = Field(None, description="API key for server-to-server authentication")


class ValidateTokenResponse(BaseModel):
    """Schema for token validation response"""
    
    valid: bool
    user: Optional[UserResponse] = None
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    """Schema for error response"""
    
    success: bool = False
    error: str
    message: str
    details: Optional[dict] = None

