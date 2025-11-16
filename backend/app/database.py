"""
Database Configuration and Session Management
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.config import settings

# Create SQLAlchemy engine for PostgreSQL
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=20,  # Increased from 10 for better concurrency
    max_overflow=40,  # Increased from 20 for peak loads
    pool_recycle=3600,  # Recycle connections every hour
    pool_timeout=10,  # Reduced from default 30s for faster failure
    echo=False,  # DISABLED - Query logging adds 10-50ms overhead per query
    connect_args={
        "connect_timeout": 5,  # 5 second connection timeout
        "options": "-c statement_timeout=30000",  # 30 second query timeout
    },
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for declarative models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    Yields a database session and closes it after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
