"""
Authentication Pydantic Schemas
"""
from pydantic import BaseModel
from typing import Optional
from app.schemas.user import UserResponse


class Token(BaseModel):
    """Token response schema"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Token payload schema"""
    sub: Optional[str] = None
    exp: Optional[int] = None
    type: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema"""
    refresh_token: str


class TokenResponse(BaseModel):
    """New access token response"""
    access_token: str
    token_type: str = "bearer"


class RegisterResponse(BaseModel):
    """Registration response with user info and tokens"""
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"



