"""
SQL Agent Tools
"""

from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import Session
from uuid import UUID
import json
import re
import time

from app.services.redis_service import redis_service
from app.services.claude_service import claude_service
from app.models.db_connection import DBConnection
from app.config import settings
from app.agents.prompts.sql_prompts import (
    SQL_GENERATION_PROMPT,
    SQL_VALIDATION_PROMPT,
    SQL_FIX_PROMPT
)


async def get_database_schema(
    db_connection_id: UUID,
    db: Session
) -> Dict[str, Any]:
    """
    Get database schema (tables, columns, types).
    Cached in Redis for 1 hour.
    
    Args:
        db_connection_id: Database connection ID
        db: Database session
    
    Returns:
        Schema dictionary
    """
    try:
        # Check cache first
        cached_schema = await redis_service.get_cached_schema(db_connection_id)
        if cached_schema:
            print("✅ Using cached schema")
            return cached_schema
        
        # Get database connection
        db_conn = db.query(DBConnection).filter(
            DBConnection.id == db_connection_id
        ).first()
        
        if not db_conn:
            raise ValueError(f"Database connection {db_connection_id} not found")
        
        # Get decrypted connection string
        connection_string = db_conn.get_connection_string()
        
        # Create engine and inspect
        engine = create_engine(connection_string)
        inspector = inspect(engine)
        
        schema = {
            "tables": [],
            "database_type": db_conn.db_type
        }
        
        # Get all tables and their columns
        for table_name in inspector.get_table_names():
            columns = []
            for column in inspector.get_columns(table_name):
                columns.append({
                    "name": column["name"],
                    "type": str(column["type"]),
                    "nullable": column.get("nullable", True)
                })
            
            # Get primary keys
            pk_constraint = inspector.get_pk_constraint(table_name)
            primary_keys = pk_constraint.get("constrained_columns", [])
            
            schema["tables"].append({
                "name": table_name,
                "columns": columns,
                "primary_keys": primary_keys
            })
        
        engine.dispose()
        
        # Cache the schema
        await redis_service.cache_schema(db_connection_id, schema, ttl_minutes=60)
        
        return schema
        
    except Exception as e:
        print(f"❌ Error getting database schema: {e}")
        raise


async def generate_sql_query(
    query: str,
    schema: Dict[str, Any],
    row_limit: int = 10000
) -> str:
    """
    Generate SQL query from natural language using Claude.
    
    Args:
        query: Natural language query
        schema: Database schema
        row_limit: Maximum rows to return
    
    Returns:
        Generated SQL query string
    """
    try:
        # Format schema for prompt
        schema_text = _format_schema_for_prompt(schema)
        
        prompt = SQL_GENERATION_PROMPT.format(
            query=query,
            schema=schema_text,
            row_limit=row_limit
        )
        
        response = await claude_service.create_message_async(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.2  # Lower temperature for more deterministic SQL
        )
        
        sql_query = claude_service.extract_text_content(response).strip()
        
        # Clean up SQL query (remove markdown code blocks if present)
        sql_query = re.sub(r'^```sql\n|^```\n|\n```$', '', sql_query, flags=re.MULTILINE)
        sql_query = sql_query.strip()
        
        return sql_query
        
    except Exception as e:
        print(f"❌ Error generating SQL query: {e}")
        raise


async def validate_query(
    query: str,
    schema: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validate SQL query for security and correctness.
    
    Args:
        query: SQL query to validate
        schema: Database schema
    
    Returns:
        Validation result dictionary
    """
    try:
        issues = []
        suggestions = []
        
        # Check for dangerous SQL keywords
        dangerous_keywords = [
            r'\bDROP\b', r'\bDELETE\b', r'\bINSERT\b', r'\bUPDATE\b',
            r'\bALTER\b', r'\bTRUNCATE\b', r'\bCREATE\b', r'\bEXEC\b',
            r'\bEXECUTE\b', r'\b--\b', r'/\*', r'\*/', r'\bxp_\w+\b'
        ]
        
        for keyword_pattern in dangerous_keywords:
            if re.search(keyword_pattern, query, re.IGNORECASE):
                issues.append(f"Query contains potentially dangerous operation: {keyword_pattern}")
        
        # Check if it's a SELECT query
        if not re.match(r'^\s*SELECT\b', query, re.IGNORECASE):
            issues.append("Query must be a SELECT statement (read-only)")
        
        # Check for LIMIT clause
        if not re.search(r'\bLIMIT\s+\d+', query, re.IGNORECASE):
            suggestions.append("Consider adding a LIMIT clause to prevent large result sets")
        
        # Basic syntax check
        if query.count('(') != query.count(')'):
            issues.append("Unbalanced parentheses in query")
        
        is_valid = len(issues) == 0
        
        return {
            "is_valid": is_valid,
            "issues": issues,
            "suggestions": suggestions
        }
        
    except Exception as e:
        print(f"❌ Error validating query: {e}")
        return {
            "is_valid": False,
            "issues": [str(e)],
            "suggestions": []
        }


async def execute_query(
    query: str,
    db_connection_id: UUID,
    db: Session,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Execute SQL query and return results.
    
    Args:
        query: SQL query to execute
        db_connection_id: Database connection ID
        db: Database session
        timeout: Query timeout in seconds
    
    Returns:
        Query results with metadata
    """
    try:
        start_time = time.time()
        
        # Get database connection
        db_conn = db.query(DBConnection).filter(
            DBConnection.id == db_connection_id
        ).first()
        
        if not db_conn:
            raise ValueError(f"Database connection {db_connection_id} not found")
        
        # Get decrypted connection string
        connection_string = db_conn.get_connection_string()
        
        # Create engine
        engine = create_engine(
            connection_string,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        
        # Execute query
        with engine.connect() as connection:
            result = connection.execute(text(query))
            
            # Fetch results
            columns = list(result.keys())
            rows = []
            
            for row in result:
                row_dict = {}
                for i, value in enumerate(row):
                    # Convert non-serializable types
                    if hasattr(value, 'isoformat'):  # datetime objects
                        row_dict[columns[i]] = value.isoformat()
                    else:
                        row_dict[columns[i]] = value
                rows.append(row_dict)
                
                # Respect row limit
                if len(rows) >= settings.SQL_ROW_LIMIT:
                    break
        
        engine.dispose()
        
        execution_time = time.time() - start_time
        
        return {
            "data": rows,
            "metadata": {
                "row_count": len(rows),
                "column_count": len(columns),
                "columns": columns,
                "execution_time": round(execution_time, 3),
                "query": query
            }
        }
        
    except Exception as e:
        print(f"❌ Error executing query: {e}")
        raise


async def fix_query(
    query: str,
    error: str,
    schema: Dict[str, Any]
) -> str:
    """
    Fix a failed SQL query using Claude.
    
    Args:
        query: Original SQL query that failed
        error: Error message
        schema: Database schema
    
    Returns:
        Corrected SQL query
    """
    try:
        schema_text = _format_schema_for_prompt(schema)
        
        prompt = SQL_FIX_PROMPT.format(
            query=query,
            error=error,
            schema=schema_text
        )
        
        response = await claude_service.create_message_async(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.2
        )
        
        fixed_query = claude_service.extract_text_content(response).strip()
        
        # Clean up SQL query
        fixed_query = re.sub(r'^```sql\n|^```\n|\n```$', '', fixed_query, flags=re.MULTILINE)
        fixed_query = fixed_query.strip()
        
        return fixed_query
        
    except Exception as e:
        print(f"❌ Error fixing query: {e}")
        raise


def _format_schema_for_prompt(schema: Dict[str, Any]) -> str:
    """
    Format database schema for inclusion in prompts.
    
    Args:
        schema: Database schema dictionary
    
    Returns:
        Formatted schema string
    """
    lines = []
    lines.append(f"Database Type: {schema.get('database_type', 'Unknown')}\n")
    lines.append("Tables and Columns:\n")
    
    for table in schema.get("tables", []):
        lines.append(f"\nTable: {table['name']}")
        if table.get("primary_keys"):
            lines.append(f"  Primary Keys: {', '.join(table['primary_keys'])}")
        lines.append("  Columns:")
        for column in table["columns"]:
            nullable = "NULL" if column.get("nullable") else "NOT NULL"
            lines.append(f"    - {column['name']} ({column['type']}) {nullable}")
    
    return "\n".join(lines)

