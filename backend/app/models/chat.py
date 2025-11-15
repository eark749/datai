"""
Chat and Message Models
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class Chat(Base):
    """Chat session/conversation model"""

    __tablename__ = "chats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    db_connection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("db_connections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title = Column(String(255), nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    message_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        index=True,
    )

    # Relationships
    user = relationship("User", back_populates="chats")
    db_connection = relationship("DBConnection", back_populates="chats")
    messages = relationship(
        "Message",
        back_populates="chat",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    query_history = relationship("QueryHistory", back_populates="chat")

    def __repr__(self):
        return f"<Chat {self.title}>"


class Message(Base):
    """Individual message within a chat"""

    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(
        UUID(as_uuid=True),
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    message_metadata = Column(JSONB, default={}, nullable=False)  # Renamed from 'metadata' (reserved word)
    token_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    chat = relationship("Chat", back_populates="messages")
    dashboard_history = relationship("DashboardHistory", back_populates="message")
    query_history = relationship("QueryHistory", back_populates="message")

    def __repr__(self):
        return f"<Message {self.role} in {self.chat_id}>"

