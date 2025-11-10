"""
Chat Pydantic Schemas
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID


class ChatCreate(BaseModel):
    """Schema for creating a new chat"""
    db_connection_id: UUID
    title: Optional[str] = None


class MessageCreate(BaseModel):
    """Schema for creating a message"""
    chat_id: Optional[UUID] = None
    db_connection_id: UUID
    message: str = Field(..., min_length=1, max_length=5000)


class MessageResponse(BaseModel):
    """Schema for message response"""
    id: UUID
    chat_id: UUID
    role: str
    content: str
    metadata: Dict[str, Any]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    """Schema for chat response"""
    id: UUID
    user_id: UUID
    db_connection_id: Optional[UUID]
    title: str
    is_archived: bool
    message_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ChatWithMessages(ChatResponse):
    """Schema for chat with all messages"""
    messages: List[MessageResponse]


class ChatQueryRequest(BaseModel):
    """Schema for chat query request"""
    db_connection_id: UUID
    message: str = Field(..., min_length=1, max_length=5000)
    chat_id: Optional[UUID] = None


class ChatQueryResponse(BaseModel):
    """Schema for chat query response"""
    chat_id: UUID
    message_id: UUID
    user_message: str
    assistant_message: str
    sql_query: Optional[str]
    data: List[Dict[str, Any]]
    dashboard_html: Optional[str]
    execution_time_ms: int
    row_count: int

