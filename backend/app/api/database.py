"""
Database Connection Management API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.db_connection import DBConnection
from app.schemas.database import (
    DBConnectionCreate,
    DBConnectionUpdate,
    DBConnectionResponse,
    DBConnectionTest
)
from app.services.db_service import db_connection_manager

router = APIRouter()


@router.post("", response_model=DBConnectionResponse, status_code=status.HTTP_201_CREATED)
def create_database_connection(
    connection_data: DBConnectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a new database connection.
    
    Args:
        connection_data: Database connection details
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        DBConnectionResponse: Created database connection
    """
    # Encrypt password
    encrypted_password = db_connection_manager.encrypt_password(connection_data.password)
    
    # Create new database connection
    new_connection = DBConnection(
        user_id=current_user.id,
        name=connection_data.name,
        db_type=connection_data.db_type,
        host=connection_data.host,
        port=connection_data.port,
        database_name=connection_data.database_name,
        username=connection_data.username,
        encrypted_password=encrypted_password,
        schema=connection_data.schema
    )
    
    db.add(new_connection)
    db.commit()
    db.refresh(new_connection)
    
    return new_connection


@router.get("", response_model=List[DBConnectionResponse])
def list_database_connections(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all database connections for the current user.
    
    Args:
        skip: Number of connections to skip (pagination)
        limit: Maximum number of connections to return
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List[DBConnectionResponse]: List of user's database connections
    """
    connections = db.query(DBConnection).filter(
        DBConnection.user_id == current_user.id
    ).order_by(DBConnection.created_at.desc()).offset(skip).limit(limit).all()
    
    return connections


@router.get("/{connection_id}", response_model=DBConnectionResponse)
def get_database_connection(
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific database connection.
    
    Args:
        connection_id: Database connection ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        DBConnectionResponse: Database connection details
        
    Raises:
        HTTPException: If connection not found or not owned by user
    """
    connection = db.query(DBConnection).filter(
        DBConnection.id == connection_id,
        DBConnection.user_id == current_user.id
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Database connection not found"
        )
    
    return connection


@router.put("/{connection_id}", response_model=DBConnectionResponse)
def update_database_connection(
    connection_id: UUID,
    connection_data: DBConnectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a database connection.
    
    Args:
        connection_id: Database connection ID
        connection_data: Updated connection details
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        DBConnectionResponse: Updated database connection
        
    Raises:
        HTTPException: If connection not found or not owned by user
    """
    connection = db.query(DBConnection).filter(
        DBConnection.id == connection_id,
        DBConnection.user_id == current_user.id
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Database connection not found"
        )
    
    # Update fields
    if connection_data.name is not None:
        connection.name = connection_data.name
    if connection_data.host is not None:
        connection.host = connection_data.host
    if connection_data.port is not None:
        connection.port = connection_data.port
    if connection_data.database_name is not None:
        connection.database_name = connection_data.database_name
    if connection_data.username is not None:
        connection.username = connection_data.username
    if connection_data.password is not None:
        connection.encrypted_password = db_connection_manager.encrypt_password(connection_data.password)
    if connection_data.schema is not None:
        connection.schema = connection_data.schema
    if connection_data.is_active is not None:
        connection.is_active = connection_data.is_active
    
    db.commit()
    db.refresh(connection)
    
    return connection


@router.delete("/{connection_id}")
def delete_database_connection(
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a database connection.
    
    Args:
        connection_id: Database connection ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If connection not found or not owned by user
    """
    connection = db.query(DBConnection).filter(
        DBConnection.id == connection_id,
        DBConnection.user_id == current_user.id
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Database connection not found"
        )
    
    db.delete(connection)
    db.commit()
    
    return {"message": "Database connection deleted successfully"}


@router.post("/{connection_id}/test", response_model=DBConnectionTest)
def test_database_connection(
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Test a database connection.
    
    Args:
        connection_id: Database connection ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        DBConnectionTest: Test result
        
    Raises:
        HTTPException: If connection not found or not owned by user
    """
    connection = db.query(DBConnection).filter(
        DBConnection.id == connection_id,
        DBConnection.user_id == current_user.id
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Database connection not found"
        )
    
    # Test the connection
    test_log = db_connection_manager.test_connection(connection, db)
    
    return DBConnectionTest(
        success=(test_log.test_status == "success"),
        response_time_ms=test_log.response_time_ms,
        error_message=test_log.error_message,
        tested_at=test_log.tested_at
    )

