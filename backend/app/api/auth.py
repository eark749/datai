"""
Authentication API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.user import UserCreate, UserResponse, UserLogin
from app.schemas.auth import Token, RefreshTokenRequest, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account.
    
    Args:
        user_data: User registration data (email, username, password)
        db: Database session
        
    Returns:
        UserResponse: Created user information
        
    Raises:
        HTTPException: If email or username already exists
    """
    user = AuthService.register_user(db, user_data)
    return user


@router.post("/login", response_model=Token)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """
    Login with email and password.
    
    Args:
        login_data: User login credentials (email, password)
        db: Database session
        
    Returns:
        Token: Access token and refresh token
        
    Raises:
        HTTPException: If credentials are invalid
    """
    user = AuthService.authenticate_user(db, login_data.email, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    tokens = AuthService.create_tokens(db, user)
    return tokens


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(token_data: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Refresh access token using refresh token.
    
    Args:
        token_data: Refresh token
        db: Database session
        
    Returns:
        TokenResponse: New access token
        
    Raises:
        HTTPException: If refresh token is invalid or expired
    """
    access_token, user = AuthService.refresh_access_token(db, token_data.refresh_token)
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer"
    )


@router.post("/logout")
def logout(token_data: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Logout by revoking refresh token.
    
    Args:
        token_data: Refresh token to revoke
        db: Database session
        
    Returns:
        dict: Success message
    """
    success = AuthService.revoke_refresh_token(db, token_data.refresh_token)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refresh token not found"
        )
    
    return {"message": "Successfully logged out"}

