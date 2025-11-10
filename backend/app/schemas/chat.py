"""
Chat Pydantic Schemas
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any


class ChatCreate(BaseModel):
    """Schema for creating a new chat"""
    db_connection_id: str
    title: Optional[str] = None


class MessageCreate(BaseModel):
    """Schema for creating a message"""
    chat_id: Optional[str] = None
    db_connection_id: str
    message: str = Field(..., min_length=1, max_length=5000)


class MessageResponse(BaseModel):
    """Schema for message response"""
    id: str
    chat_id: str
    role: str
    content: str
    message_metadata: Dict[str, Any]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    """Schema for chat response"""
    id: str
    user_id: str
    db_connection_id: Optional[str]
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
    db_connection_id: str
    message: str = Field(..., min_length=1, max_length=5000)
    chat_id: Optional[str] = None


class ChatQueryResponse(BaseModel):
    """Schema for chat query response"""
    chat_id: str
    message_id: str
    user_message: str
    assistant_message: str
    sql_query: Optional[str]
    data: List[Dict[str, Any]]
    dashboard_html: Optional[str]
    execution_time_ms: int
    row_count: int


