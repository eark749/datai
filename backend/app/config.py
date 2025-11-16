"""
Application Configuration
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # App Database (PostgreSQL on AWS)
    DATABASE_URL: str
    
    # Anthropic API
    ANTHROPIC_API_KEY: str
    
    # JWT Configuration
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database Encryption
    DB_ENCRYPTION_KEY: str
    
    # App Configuration
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "Agentic SQL Dashboard"
    APP_VERSION: str = "1.0.0"
    
    # CORS
    CORS_ORIGINS: list = [
        "http://localhost:3000", 
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000"
    ]
    
    # Query Constraints
    MAX_QUERY_ROWS: int = 10000
    MAX_QUERY_COLUMNS: int = 50
    QUERY_TIMEOUT_SECONDS: int = 30
    MAX_DASHBOARD_CHARTS: int = 5
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()


