"""
Supervisor Agent Tools
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.services.redis_service import redis_service
from app.models.db_connection import DBConnection
from app.database import get_db


async def get_conversation_history(
    session_id: str,
    limit: Optional[int] = 10
) -> List[Dict[str, Any]]:
    """
    Retrieve conversation history from Redis.
    
    Args:
        session_id: Unique session identifier
        limit: Maximum number of messages to retrieve
    
    Returns:
        List of message dictionaries
    """
    try:
        history = await redis_service.get_conversation_history(
            session_id=session_id,
            limit=limit
        )
        return history
    except Exception as e:
        print(f"Error retrieving conversation history: {e}")
        return []


async def get_database_list(user_id: int, db: Session) -> List[Dict[str, Any]]:
    """
    Get list of user's database connections.
    
    Args:
        user_id: User ID
        db: Database session
    
    Returns:
        List of database connection dictionaries
    """
    try:
        connections = db.query(DBConnection).filter(
            DBConnection.user_id == user_id
        ).all()
        
        return [
            {
                "id": conn.id,
                "name": conn.name,
                "db_type": conn.db_type,
                "status": "connected"  # Could check actual connection status
            }
            for conn in connections
        ]
    except Exception as e:
        print(f"Error retrieving database list: {e}")
        return []


async def explain_query(sql_query: str) -> str:
    """
    Explain what a SQL query does in plain language.
    
    Args:
        sql_query: SQL query to explain
    
    Returns:
        Plain language explanation
    """
    try:
        from app.services.claude_service import claude_service
        
        prompt = f"""Explain the following SQL query in simple, non-technical language:

SQL Query:
{sql_query}

Provide a brief explanation of:
1. What data it retrieves
2. Any filtering or grouping applied
3. What the results will show

Keep it concise and user-friendly."""
        
        response = await claude_service.create_message_async(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500
        )
        
        return claude_service.extract_text_content(response)
    except Exception as e:
        print(f"Error explaining query: {e}")
        return "Unable to explain query at this time."


async def get_system_capabilities() -> Dict[str, Any]:
    """
    Get system capabilities and features.
    
    Returns:
        Dictionary of system capabilities
    """
    return {
        "features": [
            "Natural language to SQL query generation",
            "Interactive dashboard creation",
            "Support for PostgreSQL, MySQL, and SQLite",
            "Automatic data visualization",
            "Query history and session management"
        ],
        "supported_databases": ["PostgreSQL", "MySQL", "SQLite"],
        "chart_types": ["bar", "line", "pie", "scatter", "table"],
        "max_query_rows": 10000,
        "max_dashboard_charts": 5
    }



