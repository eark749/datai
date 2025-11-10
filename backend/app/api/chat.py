"""
Chat API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.chat import Chat
from app.schemas.chat import (
    ChatQueryRequest,
    ChatQueryResponse,
    ChatResponse,
    ChatWithMessages,
    MessageResponse
)
from app.services.chat_service import ChatService
from app.middleware import limiter

router = APIRouter()


@router.post("/query", response_model=ChatQueryResponse)
@limiter.limit("10/minute")
async def chat_query(
    request: Request,
    query_request: ChatQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Send a natural language query and get SQL results + dashboard.
    
    This is the main endpoint that orchestrates Agent 1 (SQL) and Agent 2 (Dashboard).
    
    Args:
        request: Chat query request with message and database connection
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        ChatQueryResponse: Query results including SQL, data, and dashboard HTML
    """
    result = await ChatService.process_chat_query(
        db=db,
        user=current_user,
        user_query=query_request.message,
        db_connection_id=query_request.db_connection_id,
        chat_id=query_request.chat_id
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Failed to process query")
        )
    
    return ChatQueryResponse(
        chat_id=result["chat_id"],
        message_id=result["message_id"],
        user_message=result["user_message"],
        assistant_message=result["assistant_message"],
        sql_query=result.get("sql_query"),
        data=result.get("data", []),
        dashboard_html=result.get("dashboard_html"),
        execution_time_ms=result.get("execution_time_ms", 0),
        row_count=result.get("row_count", 0)
    )


@router.get("/chats", response_model=List[ChatResponse])
def list_chats(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all chats for the current user.
    
    Args:
        skip: Number of chats to skip (pagination)
        limit: Maximum number of chats to return
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List[ChatResponse]: List of user's chats
    """
    chats = db.query(Chat).filter(
        Chat.user_id == current_user.id
    ).order_by(Chat.updated_at.desc()).offset(skip).limit(limit).all()
    
    return chats


@router.get("/chats/{chat_id}", response_model=ChatWithMessages)
def get_chat(
    chat_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific chat with all its messages.
    
    Args:
        chat_id: Chat ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        ChatWithMessages: Chat with all messages
        
    Raises:
        HTTPException: If chat not found or not owned by user
    """
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == current_user.id
    ).first()
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    return chat


@router.delete("/chats/{chat_id}")
def delete_chat(
    chat_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a chat and all its messages.
    
    Args:
        chat_id: Chat ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If chat not found or not owned by user
    """
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == current_user.id
    ).first()
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    db.delete(chat)
    db.commit()
    
    return {"message": "Chat deleted successfully"}


@router.patch("/chats/{chat_id}/archive")
def archive_chat(
    chat_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Archive or unarchive a chat.
    
    Args:
        chat_id: Chat ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        ChatResponse: Updated chat
        
    Raises:
        HTTPException: If chat not found or not owned by user
    """
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == current_user.id
    ).first()
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    chat.is_archived = not chat.is_archived
    db.commit()
    db.refresh(chat)
    
    return chat

