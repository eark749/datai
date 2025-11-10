"""
Query and Dashboard History Models
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class QueryHistory(Base):
    """Query execution history model"""
    __tablename__ = "query_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id", ondelete="SET NULL"), nullable=True, index=True)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    db_connection_id = Column(UUID(as_uuid=True), ForeignKey("db_connections.id", ondelete="CASCADE"), nullable=False, index=True)
    natural_language_query = Column(Text, nullable=False)
    generated_sql = Column(Text, nullable=False)
    sql_valid = Column(Boolean, nullable=False)
    execution_status = Column(String(20), nullable=False, index=True)  # success, error, timeout
    execution_time_ms = Column(Integer, nullable=True)
    row_count = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="query_history")
    chat = relationship("Chat", back_populates="query_history")
    message = relationship("Message", back_populates="query_history")
    db_connection = relationship("DBConnection", back_populates="query_history")
    dashboard_history = relationship("DashboardHistory", back_populates="query_history", uselist=False)
    
    def __repr__(self):
        return f"<QueryHistory {self.execution_status}>"


class DashboardHistory(Base):
    """Dashboard generation history model"""
    __tablename__ = "dashboard_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    query_history_id = Column(UUID(as_uuid=True), ForeignKey("query_history.id", ondelete="SET NULL"), nullable=True)
    dashboard_type = Column(String(50), nullable=False)  # html, react, json
    dashboard_content = Column(Text, nullable=False)
    chart_count = Column(Integer, default=0, nullable=False)
    chart_types = Column(JSONB, default=[], nullable=False)
    data_summary = Column(JSONB, default={}, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="dashboard_history")
    message = relationship("Message", back_populates="dashboard_history")
    query_history = relationship("QueryHistory", back_populates="dashboard_history")
    
    def __repr__(self):
        return f"<DashboardHistory {self.dashboard_type}>"

