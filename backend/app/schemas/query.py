"""
Query History Pydantic Schemas
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from uuid import UUID


class QueryHistoryResponse(BaseModel):
    """Schema for query history response"""
    id: UUID
    user_id: UUID
    chat_id: Optional[UUID]
    db_connection_id: UUID
    natural_language_query: str
    generated_sql: str
    sql_valid: bool
    execution_status: str
    execution_time_ms: Optional[int]
    row_count: Optional[int]
    error_message: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class QueryHistoryFilter(BaseModel):
    """Schema for filtering query history"""
    db_connection_id: Optional[UUID] = None
    execution_status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    skip: int = 0
    limit: int = 50

