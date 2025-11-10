"""
Database Connection Pydantic Schemas
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID


class DBConnectionCreate(BaseModel):
    """Schema for creating a database connection"""
    name: str = Field(..., min_length=1, max_length=100)
    db_type: str = Field(..., pattern="^(postgresql|mysql|sqlite)$")
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(..., gt=0, lt=65536)
    database_name: str = Field(..., min_length=1, max_length=100)
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1)
    schema: Optional[str] = "public"


class DBConnectionUpdate(BaseModel):
    """Schema for updating a database connection"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    host: Optional[str] = Field(None, min_length=1, max_length=255)
    port: Optional[int] = Field(None, gt=0, lt=65536)
    database_name: Optional[str] = Field(None, min_length=1, max_length=100)
    username: Optional[str] = Field(None, min_length=1, max_length=100)
    password: Optional[str] = None
    schema: Optional[str] = None
    is_active: Optional[bool] = None


class DBConnectionResponse(BaseModel):
    """Schema for database connection response (without password)"""
    id: UUID
    user_id: UUID
    name: str
    db_type: str
    host: str
    port: int
    database_name: str
    username: str
    schema: str
    is_active: bool
    last_tested: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DBConnectionTest(BaseModel):
    """Schema for connection test result"""
    success: bool
    response_time_ms: Optional[int]
    error_message: Optional[str]
    tested_at: datetime

