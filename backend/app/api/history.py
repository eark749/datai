"""
History API Endpoints
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.query_history import QueryHistory
from app.schemas.query import QueryHistoryResponse

router = APIRouter()


@router.get("/queries", response_model=List[QueryHistoryResponse])
def get_query_history(
    db_connection_id: Optional[UUID] = None,
    execution_status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get query history with optional filters.
    
    Args:
        db_connection_id: Filter by database connection
        execution_status: Filter by status (success, error, timeout)
        start_date: Filter by start date
        end_date: Filter by end date
        skip: Number of entries to skip (pagination)
        limit: Maximum number of entries to return
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List[QueryHistoryResponse]: Query history entries
    """
    query = db.query(QueryHistory).filter(
        QueryHistory.user_id == current_user.id
    )
    
    # Apply filters
    if db_connection_id:
        query = query.filter(QueryHistory.db_connection_id == db_connection_id)
    
    if execution_status:
        query = query.filter(QueryHistory.execution_status == execution_status)
    
    if start_date:
        query = query.filter(QueryHistory.created_at >= start_date)
    
    if end_date:
        query = query.filter(QueryHistory.created_at <= end_date)
    
    # Order and paginate
    history = query.order_by(
        QueryHistory.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return history


@router.get("/queries/{query_id}", response_model=QueryHistoryResponse)
def get_query_details(
    query_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get details of a specific query.
    
    Args:
        query_id: Query history ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        QueryHistoryResponse: Query details
    """
    query = db.query(QueryHistory).filter(
        QueryHistory.id == query_id,
        QueryHistory.user_id == current_user.id
    ).first()
    
    if not query:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query not found"
        )
    
    return query



