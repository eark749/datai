"""
SQL Agent Tools - LangChain tools for SQL operations
"""
from langchain.tools import tool
from langchain_core.tools import Tool
from sqlalchemy import text
from typing import Dict, Any, List, Optional
import json
import time
import re

from app.models.db_connection import DBConnection
from app.services.db_service import db_connection_manager


class SQLTools:
    """Collection of tools for SQL agent"""
    
    def __init__(self, db_config: DBConnection):
        """
        Initialize SQL tools with database configuration.
        
        Args:
            db_config: Database connection configuration
        """
        self.db_config = db_config
    
    def execute_sql_query(self, sql_query: str) -> str:
        """
        Execute SQL query against the connected database.
        Returns results in JSON format or error message.
        
        Args:
            sql_query: SQL query to execute
            
        Returns:
            str: JSON string with results or error
        """
        print(f"⚡ [SQL_TOOL] Executing SQL query")
        print(f"📝 [SQL_TOOL] Query: {sql_query}")
        
        try:
            # Validate SQL for safety
            if not self._is_safe_sql(sql_query):
                error_msg = "Query validation failed: Only SELECT queries are allowed"
                print(f"❌ [SQL_TOOL] {error_msg}")
                return json.dumps({
                    "success": False,
                    "error": error_msg,
                    "rows": []
                })
            
            # Get database session
            session = db_connection_manager.get_session(self.db_config, read_only=True)
            
            # Execute query with timeout
            start_time = time.time()
            result = session.execute(text(sql_query))
            execution_time = int((time.time() - start_time) * 1000)
            
            # Fetch results
            rows = []
            if result.returns_rows:
                columns = list(result.keys())
                for row in result:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        value = row[i]
                        # Convert non-serializable types
                        if hasattr(value, 'isoformat'):  # datetime, date
                            value = value.isoformat()
                        elif isinstance(value, bytes):
                            value = value.decode('utf-8', errors='ignore')
                        row_dict[col] = value
                    rows.append(row_dict)
            
            session.close()
            
            print(f"✅ [SQL_TOOL] Query executed successfully: {len(rows)} rows returned in {execution_time}ms")
            
            return json.dumps({
                "success": True,
                "rows": rows,
                "row_count": len(rows),
                "execution_time_ms": execution_time,
                "error": None
            })
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ [SQL_TOOL] Query execution failed: {error_msg}")
            
            return json.dumps({
                "success": False,
                "error": error_msg,
                "rows": [],
                "row_count": 0
            })
    
    def _is_safe_sql(self, sql_query: str) -> bool:
        """
        Validate SQL query for safety.
        Only SELECT queries are allowed.
        
        Args:
            sql_query: SQL query to validate
            
        Returns:
            bool: True if safe, False otherwise
        """
        # Remove comments and normalize whitespace
        query_clean = re.sub(r'--.*$', '', sql_query, flags=re.MULTILINE)
        query_clean = re.sub(r'/\*.*?\*/', '', query_clean, flags=re.DOTALL)
        query_clean = query_clean.strip().upper()
        
        # Dangerous keywords
        dangerous_keywords = [
            'DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 
            'CREATE', 'TRUNCATE', 'GRANT', 'REVOKE', 'EXEC',
            'EXECUTE', 'CALL'
        ]
        
        # Check if query starts with SELECT
        if not query_clean.startswith('SELECT') and not query_clean.startswith('WITH'):
            print(f"⚠️  [SQL_TOOL] Query must start with SELECT or WITH")
            return False
        
        # Check for dangerous keywords
        for keyword in dangerous_keywords:
            if keyword in query_clean:
                print(f"⚠️  [SQL_TOOL] Dangerous keyword detected: {keyword}")
                return False
        
        return True
    
    def get_langchain_tools(self) -> List[Tool]:
        """
        Get LangChain tools for this SQL agent.
        
        Returns:
            List[Tool]: List of LangChain tools
        """
        tools = [
            Tool(
                name="execute_sql_query",
                description=(
                    "Execute a SQL SELECT query against the database. "
                    "Input should be a valid SQL SELECT query. "
                    "Returns JSON with success status, rows of data, and row count. "
                    "Use this tool to retrieve data from the database."
                ),
                func=self.execute_sql_query
            )
        ]
        
        return tools


def create_sql_tools(db_config: DBConnection) -> List[Tool]:
    """
    Create SQL tools for a database connection.
    
    Args:
        db_config: Database connection configuration
        
    Returns:
        List[Tool]: List of LangChain tools
    """
    sql_tools = SQLTools(db_config)
    return sql_tools.get_langchain_tools()

