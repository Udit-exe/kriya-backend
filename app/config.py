"""
Configuration settings for Kriya Backend
"""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "Kriya Authentication Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5433/kriya_db"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_SECRET_KEY: str = "your-jwt-secret-key-change-in-production-min-32-chars"
    JWT_ALGORITHM: str = "HS256"
    TOKEN_EXPIRY_HOURS: int = 24  # 24 hours token validity
    
    # CORS
    ALLOWED_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8000",
    ]
    
    # Plane Backend Integration
    PLANE_API_KEY: str = "shared-secret-key-for-plane-kriya-communication"
    PLANE_BACKEND_URL: str = "http://localhost:8000"
    PLANE_SERVICE_TOKEN: str = ""  # Plane API token for service account
    PLANE_WORKSPACE_SLUG: str = "default"  # Default workspace slug
    PLANE_PROJECT_ID: str = ""  # Default project ID
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Allow extra fields in .env file


@lru_cache()
def get_settings():
    """Get cached settings instance"""
    return Settings()

