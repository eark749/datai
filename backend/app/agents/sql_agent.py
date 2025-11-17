"""
SQL Agent - Database interaction specialist
"""

from typing import Dict, Any
from sqlalchemy.orm import Session

from app.agents.state import AgentState
from app.agents.tools.sql_tools import (
    get_database_schema,
    generate_sql_query,
    validate_query,
    execute_query,
    fix_query
)
from app.config import settings


class SQLAgent:
    """
    SQL Agent that handles database querying and data retrieval.
    """
    
    def __init__(self):
        """Initialize SQL agent"""
        self.max_retries = settings.AGENT_MAX_RETRIES
        self.row_limit = settings.SQL_ROW_LIMIT
    
    async def process(
        self,
        state: AgentState,
        db: Session
    ) -> Dict[str, Any]:
        """
        Process SQL query request.
        
        Args:
            state: Current agent state
            db: Database session
        
        Returns:
            Updated state with SQL results
        """
        try:
            query = state["user_query"]
            database_id = state.get("database_id")
            
            if not database_id:
                return {
                    "error": "No database connection specified. Please connect a database first.",
                    "sql_query": None,
                    "query_results": None
                }
            
            # Step 1: Get database schema
            print("📊 Getting database schema...")
            schema = await get_database_schema(database_id, db)
            
            # Step 2: Generate SQL query
            print("🔧 Generating SQL query...")
            sql_query = await generate_sql_query(
                query=query,
                schema=schema,
                row_limit=self.row_limit
            )
            
            # Step 3: Validate query
            print("✅ Validating SQL query...")
            validation = await validate_query(sql_query, schema)
            
            if not validation["is_valid"]:
                error_msg = "SQL query validation failed: " + ", ".join(validation["issues"])
                
                # Try to fix if retries available
                if state["retry_count"] < self.max_retries:
                    print("🔄 Attempting to fix query...")
                    sql_query = await fix_query(
                        query=sql_query,
                        error=error_msg,
                        schema=schema
                    )
                    # Re-validate
                    validation = await validate_query(sql_query, schema)
                    if not validation["is_valid"]:
                        return {
                            "error": error_msg,
                            "sql_query": sql_query,
                            "query_results": None
                        }
                else:
                    return {
                        "error": error_msg,
                        "sql_query": sql_query,
                        "query_results": None
                    }
            
            # Step 4: Execute query
            print("⚡ Executing SQL query...")
            results = await execute_query(
                query=sql_query,
                db_connection_id=database_id,
                db=db,
                timeout=settings.AGENT_TIMEOUT
            )
            
            print(f"✅ Query executed successfully: {results['metadata']['row_count']} rows")
            
            return {
                "sql_query": sql_query,
                "query_results": results["data"],
                "query_metadata": results["metadata"],
                "error": None
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ SQL Agent error: {error_msg}")
            
            # Try to fix if retries available and we have a query
            if state["retry_count"] < self.max_retries and state.get("sql_query"):
                print("🔄 Attempting to fix query after error...")
                try:
                    schema = await get_database_schema(database_id, db)
                    fixed_query = await fix_query(
                        query=state["sql_query"],
                        error=error_msg,
                        schema=schema
                    )
                    
                    # Try executing fixed query
                    results = await execute_query(
                        query=fixed_query,
                        db_connection_id=database_id,
                        db=db,
                        timeout=settings.AGENT_TIMEOUT
                    )
                    
                    print(f"✅ Fixed query executed successfully: {results['metadata']['row_count']} rows")
                    
                    return {
                        "sql_query": fixed_query,
                        "query_results": results["data"],
                        "query_metadata": results["metadata"],
                        "error": None
                    }
                except Exception as retry_error:
                    print(f"❌ Retry failed: {retry_error}")
            
            return {
                "error": f"Failed to execute SQL query: {error_msg}",
                "sql_query": state.get("sql_query"),
                "query_results": None
            }


# Global instance
sql_agent = SQLAgent()



