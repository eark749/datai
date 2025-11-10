"""
Authentication Service - Business Logic for User Authentication
"""
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime, timedelta
from typing import Optional, Tuple

from app.models.user import User, RefreshToken
from app.schemas.user import UserCreate
from app.schemas.auth import Token
from app.utils.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.config import settings


class AuthService:
    """Authentication service for user registration and login"""
    
    @staticmethod
    def register_user(db: Session, user_data: UserCreate) -> User:
        """
        Register a new user.
        
        Args:
            db: Database session
            user_data: User registration data
            
        Returns:
            User: Created user
            
        Raises:
            HTTPException: If email or username already exists
        """
        # Check if email already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check if username already exists
        existing_username = db.query(User).filter(User.username == user_data.username).first()
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        # Create new user
        hashed_password = hash_password(user_data.password)
        new_user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_password
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return new_user
    
    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """
        Authenticate a user by email and password.
        
        Args:
            db: Database session
            email: User email
            password: User password
            
        Returns:
            Optional[User]: User if authenticated, None otherwise
        """
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        return user
    
    @staticmethod
    def create_tokens(db: Session, user: User) -> Token:
        """
        Create access and refresh tokens for a user.
        
        Args:
            db: Database session
            user: User to create tokens for
            
        Returns:
            Token: Access and refresh tokens
        """
        # Create access token
        access_token = create_access_token(data={"sub": str(user.id)})
        
        # Create refresh token
        refresh_token_str = create_refresh_token(data={"sub": str(user.id)})
        
        # Store refresh token in database
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token_obj = RefreshToken(
            user_id=user.id,
            token=refresh_token_str,
            expires_at=expires_at
        )
        
        db.add(refresh_token_obj)
        db.commit()
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token_str,
            token_type="bearer"
        )
    
    @staticmethod
    def refresh_access_token(db: Session, refresh_token: str) -> Tuple[str, User]:
        """
        Create a new access token using a refresh token.
        
        Args:
            db: Database session
            refresh_token: Refresh token
            
        Returns:
            Tuple[str, User]: New access token and user
            
        Raises:
            HTTPException: If refresh token is invalid or expired
        """
        # Verify refresh token
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Check if token exists in database and is not revoked
        token_obj = db.query(RefreshToken).filter(
            RefreshToken.token == refresh_token,
            RefreshToken.revoked == False
        ).first()
        
        if not token_obj:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not found or revoked"
            )
        
        # Check if token is expired
        if token_obj.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired"
            )
        
        # Get user
        user = db.query(User).filter(User.id == token_obj.user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new access token
        access_token = create_access_token(data={"sub": str(user.id)})
        
        return access_token, user
    
    @staticmethod
    def revoke_refresh_token(db: Session, refresh_token: str) -> bool:
        """
        Revoke a refresh token.
        
        Args:
            db: Database session
            refresh_token: Refresh token to revoke
            
        Returns:
            bool: True if token was revoked, False if not found
        """
        token_obj = db.query(RefreshToken).filter(
            RefreshToken.token == refresh_token
        ).first()
        
        if not token_obj:
            return False
        
        token_obj.revoked = True
        token_obj.revoked_at = datetime.utcnow()
        db.commit()
        
        return True

