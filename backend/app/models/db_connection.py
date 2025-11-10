"""
Database Connection Models
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


def generate_uuid():
    """Generate UUID as string for SQLite compatibility"""
    return str(uuid.uuid4())


class DBConnection(Base):
    """User's business database connection configuration"""

    __tablename__ = "db_connections"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(100), nullable=False)
    db_type = Column(String(50), nullable=False)  # postgresql, mysql, sqlite
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    database_name = Column(String(100), nullable=False)
    username = Column(String(100), nullable=False)
    encrypted_password = Column(Text, nullable=False)
    schema = Column(String(100), default="public")
    is_active = Column(Boolean, default=True, nullable=False)
    last_tested = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="db_connections")
    chats = relationship("Chat", back_populates="db_connection")
    query_history = relationship("QueryHistory", back_populates="db_connection")
    connection_test_logs = relationship(
        "ConnectionTestLog",
        back_populates="db_connection",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<DBConnection {self.name}>"


class ConnectionTestLog(Base):
    """Database connection test log"""

    __tablename__ = "connection_test_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    db_connection_id = Column(
        String(36),
        ForeignKey("db_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    test_status = Column(String(20), nullable=False)  # success, failure, timeout
    response_time_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    tested_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    db_connection = relationship("DBConnection", back_populates="connection_test_logs")

    def __repr__(self):
        return f"<ConnectionTestLog {self.test_status}>"

