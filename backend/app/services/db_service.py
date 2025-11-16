"""
Database Connection Manager Service
Handles dynamic database connections with encrypted credentials
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from cryptography.fernet import Fernet
from typing import Dict, Optional
import time
from datetime import datetime

from app.config import settings
from app.models.db_connection import DBConnection, ConnectionTestLog


class DBConnectionManager:
    """
    Manages dynamic database connections with credential encryption.
    Provides connection pooling and credential security.
    """
    
    def __init__(self):
        """Initialize the connection manager with encryption key"""
        self._fernet = Fernet(settings.DB_ENCRYPTION_KEY.encode())
        self._connections: Dict[str, any] = {}  # Cache of active connections
    
    def encrypt_password(self, password: str) -> str:
        """
        Encrypt a database password.
        
        Args:
            password: Plain text password
            
        Returns:
            str: Encrypted password
        """
        return self._fernet.encrypt(password.encode()).decode()
    
    def decrypt_password(self, encrypted_password: str) -> str:
        """
        Decrypt a database password.
        
        Args:
            encrypted_password: Encrypted password
            
        Returns:
            str: Decrypted plain text password
        """
        return self._fernet.decrypt(encrypted_password.encode()).decode()
    
    def build_connection_url(self, db_config: DBConnection, use_ssl: bool = False) -> str:
        """
        Build SQLAlchemy connection URL from database configuration.
        
        Args:
            db_config: Database connection configuration
            use_ssl: Whether to use SSL (for AWS RDS, etc.)
            
        Returns:
            str: SQLAlchemy connection URL
        """
        password = self.decrypt_password(db_config.encrypted_password)
        
        # Check if host is AWS RDS (auto-enable SSL)
        is_aws_rds = 'rds.amazonaws.com' in db_config.host.lower()
        
        if db_config.db_type == "postgresql":
            url = f"postgresql://{db_config.username}:{password}@{db_config.host}:{db_config.port}/{db_config.database_name}"
            # Add SSL for AWS RDS
            if is_aws_rds or use_ssl:
                url += "?sslmode=require"
        elif db_config.db_type == "mysql":
            url = f"mysql+pymysql://{db_config.username}:{password}@{db_config.host}:{db_config.port}/{db_config.database_name}"
            # Add SSL for AWS RDS
            if is_aws_rds or use_ssl:
                url += "?ssl=true"
        elif db_config.db_type == "sqlite":
            url = f"sqlite:///{db_config.database_name}"
        else:
            raise ValueError(f"Unsupported database type: {db_config.db_type}")
        
        return url
    
    def get_engine(self, db_config: DBConnection, read_only: bool = True):
        """
        Get or create SQLAlchemy engine for a database connection.
        
        Args:
            db_config: Database connection configuration
            read_only: Whether to enforce read-only access (default: True)
            
        Returns:
            Engine: SQLAlchemy engine
        """
        cache_key = f"{db_config.id}_{read_only}"
        
        # Return cached connection if exists
        if cache_key in self._connections:
            return self._connections[cache_key]
        
        # Build connection URL (SSL auto-detected for AWS RDS)
        connection_url = self.build_connection_url(db_config, use_ssl=True)
        
        # Additional SSL arguments for AWS RDS
        connect_args = {}
        is_aws_rds = 'rds.amazonaws.com' in db_config.host.lower()
        
        if is_aws_rds and db_config.db_type == "postgresql":
            connect_args['sslmode'] = 'require'
        elif is_aws_rds and db_config.db_type == "mysql":
            connect_args['ssl'] = {'ssl_verify_cert': False, 'ssl_verify_identity': False}
        
        # Create engine with connection pooling
        engine = create_engine(
            connection_url,
            pool_pre_ping=True,
            pool_size=10,  # Increased from 5
            max_overflow=20,  # Increased from 10
            pool_timeout=10,  # Reduced from 30s for faster failure
            pool_recycle=3600,  # Recycle connections every hour
            echo=False,  # DISABLED - logging adds overhead
            connect_args={
                **connect_args,
                "connect_timeout": 5  # 5 second connection timeout
            }
        )
        
        # Test connection and set read-only mode if PostgreSQL
        if read_only and db_config.db_type == "postgresql":
            try:
                with engine.connect() as conn:
                    # Set read-only transaction
                    conn.execute(text("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY"))
            except Exception as e:
                print(f"Warning: Could not set read-only mode: {e}")
        
        # Cache the engine
        self._connections[cache_key] = engine
        
        return engine
    
    def get_session(self, db_config: DBConnection, read_only: bool = True):
        """
        Get a database session for executing queries.
        
        Args:
            db_config: Database connection configuration
            read_only: Whether to enforce read-only access (default: True)
            
        Returns:
            Session: SQLAlchemy session
        """
        engine = self.get_engine(db_config, read_only)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return SessionLocal()
    
    def test_connection(self, db_config: DBConnection, app_db_session) -> ConnectionTestLog:
        """
        Test a database connection and log the result.
        
        Args:
            db_config: Database connection configuration
            app_db_session: Application database session for logging
            
        Returns:
            ConnectionTestLog: Test result log
        """
        start_time = time.time()
        
        try:
            # Try to connect and execute a simple query
            engine = self.get_engine(db_config, read_only=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            response_time = int((time.time() - start_time) * 1000)
            
            # Create successful test log
            test_log = ConnectionTestLog(
                db_connection_id=db_config.id,
                test_status="success",
                response_time_ms=response_time,
                error_message=None
            )
            
            # Update last_tested timestamp
            db_config.last_tested = datetime.utcnow()
            
        except OperationalError as e:
            response_time = int((time.time() - start_time) * 1000)
            test_log = ConnectionTestLog(
                db_connection_id=db_config.id,
                test_status="failure",
                response_time_ms=response_time,
                error_message=str(e)
            )
        except SQLAlchemyError as e:
            response_time = int((time.time() - start_time) * 1000)
            test_log = ConnectionTestLog(
                db_connection_id=db_config.id,
                test_status="failure",
                response_time_ms=response_time,
                error_message=str(e)
            )
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            test_log = ConnectionTestLog(
                db_connection_id=db_config.id,
                test_status="failure",
                response_time_ms=response_time,
                error_message=str(e)
            )
        
        # Save test log
        app_db_session.add(test_log)
        app_db_session.commit()
        app_db_session.refresh(test_log)
        
        return test_log
    
    def close_connection(self, db_config_id: str, read_only: bool = True):
        """
        Close and remove a cached connection.
        
        Args:
            db_config_id: Database configuration ID
            read_only: Whether this is the read-only connection
        """
        cache_key = f"{db_config_id}_{read_only}"
        
        if cache_key in self._connections:
            engine = self._connections[cache_key]
            engine.dispose()
            del self._connections[cache_key]
    
    def close_all_connections(self):
        """Close all cached database connections"""
        for engine in self._connections.values():
            engine.dispose()
        self._connections.clear()


# Global instance
db_connection_manager = DBConnectionManager()




