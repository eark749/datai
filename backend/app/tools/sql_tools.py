"""
SQL Tools for Agent 1 - SQL Generator & Data Retriever
"""

from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError
from typing import Dict, List, Any, Optional, Tuple
import json
import time
from functools import lru_cache
import hashlib

from app.models.db_connection import DBConnection
from app.services.db_service import DBConnectionManager
from app.utils.validators import SQLValidator
from app.config import settings


# Global schema cache to avoid redundant schema fetches
_schema_cache = {}


class SQLTools:
    """
    Tools for SQL generation, validation, and execution.
    Used by Agent 1 (SQL Agent) for database operations.
    """

    def __init__(self, db_connection: DBConnection, db_manager: DBConnectionManager):
        """
        Initialize SQL tools with database connection.

        Args:
            db_connection: Database connection configuration
            db_manager: Database connection manager
        """
        self.db_connection = db_connection
        self.db_manager = db_manager
        self.validator = SQLValidator()
        self._cache_key = f"{db_connection.id}_{db_connection.database_name}"

    def get_database_schema(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get database schema information (tables, columns, types).
        
        Args:
            use_cache: Whether to use cached schema (default: True)

        Returns:
            Dict: Schema metadata containing tables and columns

        Tool Definition for Claude:
        {
            "name": "get_database_schema",
            "description": "Retrieves the database schema including all tables, columns, data types, and relationships. Use this to understand the database structure before generating SQL queries.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
        """
        # Check cache first
        global _schema_cache
        if use_cache and self._cache_key in _schema_cache:
            print(f"✅ Using cached schema for {self.db_connection.database_name}")
            return _schema_cache[self._cache_key]
        
        try:
            print(f"🔄 Fetching fresh schema for {self.db_connection.database_name}")
            engine = self.db_manager.get_engine(self.db_connection, read_only=True)
            inspector = inspect(engine)

            schema_info = {
                "database_name": self.db_connection.database_name,
                "database_type": self.db_connection.db_type,
                "schema": self.db_connection.schema,
                "tables": [],
            }

            # Get all table names
            table_names = inspector.get_table_names(schema=self.db_connection.schema)

            # Get details for each table
            for table_name in table_names:
                table_info = {
                    "table_name": table_name,
                    "columns": [],
                    "primary_keys": [],
                    "foreign_keys": [],
                }

                # Get columns
                columns = inspector.get_columns(
                    table_name, schema=self.db_connection.schema
                )
                for column in columns:
                    table_info["columns"].append(
                        {
                            "name": column["name"],
                            "type": str(column["type"]),
                            "nullable": column["nullable"],
                            "default": str(column["default"])
                            if column.get("default")
                            else None,
                        }
                    )

                # Get primary keys
                pk_constraint = inspector.get_pk_constraint(
                    table_name, schema=self.db_connection.schema
                )
                if pk_constraint:
                    table_info["primary_keys"] = pk_constraint.get(
                        "constrained_columns", []
                    )

                # Get foreign keys
                foreign_keys = inspector.get_foreign_keys(
                    table_name, schema=self.db_connection.schema
                )
                for fk in foreign_keys:
                    table_info["foreign_keys"].append(
                        {
                            "columns": fk.get("constrained_columns", []),
                            "referred_table": fk.get("referred_table"),
                            "referred_columns": fk.get("referred_columns", []),
                        }
                    )

                schema_info["tables"].append(table_info)

            # Cache the schema
            _schema_cache[self._cache_key] = schema_info
            print(f"💾 Cached schema for {self.db_connection.database_name}")
            
            return schema_info

        except Exception as e:
            return {
                "error": f"Failed to retrieve schema: {str(e)}",
                "database_name": self.db_connection.database_name,
            }

    def validate_sql(self, sql_query: str) -> Dict[str, Any]:
        """
        Validate SQL query for safety (injection prevention, read-only check).

        Args:
            sql_query: SQL query to validate

        Returns:
            Dict: Validation result with is_valid and error_message

        Tool Definition for Claude:
        {
            "name": "validate_sql",
            "description": "Validates a SQL query for safety. Checks for SQL injection patterns, dangerous keywords (DROP, DELETE, etc.), and ensures the query is read-only (SELECT only).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "sql_query": {
                        "type": "string",
                        "description": "The SQL query to validate"
                    }
                },
                "required": ["sql_query"]
            }
        }
        """
        is_valid, error_message = self.validator.validate_sql(sql_query)

        result = {
            "is_valid": is_valid,
            "error_message": error_message,
            "sql_query": sql_query,
        }

        if is_valid:
            result["formatted_sql"] = self.validator.format_sql(sql_query)

        return result

    def execute_sql(self, sql_query: str) -> Dict[str, Any]:
        """
        Execute a validated SQL query and return results.

        Args:
            sql_query: SQL query to execute (must be validated first)

        Returns:
            Dict: Query results including data, row_count, execution_time

        Tool Definition for Claude:
        {
            "name": "execute_sql",
            "description": "Executes a validated SQL query on the database and returns the results. The query must be validated first using validate_sql. Returns data rows, column names, row count, and execution time.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "sql_query": {
                        "type": "string",
                        "description": "The validated SQL query to execute"
                    }
                },
                "required": ["sql_query"]
            }
        }
        """
        # Validate SQL before execution
        is_valid, error_message = self.validator.validate_sql(sql_query)

        if not is_valid:
            return {
                "success": False,
                "error": f"SQL validation failed: {error_message}",
                "data": [],
                "columns": [],
                "row_count": 0,
            }

        try:
            session = self.db_manager.get_session(self.db_connection, read_only=True)

            # Start timing
            start_time = time.time()

            # Execute query with row limit
            result = session.execute(
                text(sql_query).execution_options(
                    max_row_buffer=settings.MAX_QUERY_ROWS
                )
            )

            # Fetch results (limited to MAX_QUERY_ROWS)
            rows = result.fetchmany(settings.MAX_QUERY_ROWS)

            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)

            # Get column names
            columns = list(result.keys()) if result.keys() else []

            # Convert rows to list of dicts
            data = []
            for row in rows:
                row_dict = {}
                for i, col_name in enumerate(columns):
                    value = row[i]
                    # Handle non-JSON serializable types
                    if value is not None:
                        row_dict[col_name] = (
                            str(value)
                            if not isinstance(value, (str, int, float, bool))
                            else value
                        )
                    else:
                        row_dict[col_name] = None
                data.append(row_dict)

            # Check if there are more rows
            has_more = len(rows) == settings.MAX_QUERY_ROWS

            session.close()

            return {
                "success": True,
                "data": data,
                "columns": columns,
                "row_count": len(data),
                "execution_time_ms": execution_time_ms,
                "has_more": has_more,
                "max_rows": settings.MAX_QUERY_ROWS,
                "sql_query": sql_query,
            }

        except SQLAlchemyError as e:
            return {
                "success": False,
                "error": f"Database error: {str(e)}",
                "data": [],
                "columns": [],
                "row_count": 0,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Execution error: {str(e)}",
                "data": [],
                "columns": [],
                "row_count": 0,
            }

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        Get Claude-compatible tool definitions for all SQL tools.

        Returns:
            List[Dict]: List of tool definitions for Claude API
        """
        return [
            {
                "name": "get_database_schema",
                "description": "Retrieves the database schema including all tables, columns, data types, and relationships. Use this first to understand the database structure before generating SQL queries.",
                "input_schema": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "validate_sql",
                "description": "Validates a SQL query for safety. Checks for SQL injection patterns, dangerous keywords (DROP, DELETE, etc.), and ensures the query is read-only (SELECT only). Always validate before executing.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "sql_query": {
                            "type": "string",
                            "description": "The SQL query to validate",
                        }
                    },
                    "required": ["sql_query"],
                },
            },
            {
                "name": "execute_sql",
                "description": "Executes a validated SQL query on the database and returns the results. Only use after validating the query. Returns data rows, column names, row count, and execution time.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "sql_query": {
                            "type": "string",
                            "description": "The validated SQL query to execute",
                        }
                    },
                    "required": ["sql_query"],
                },
            },
        ]

    def execute_tool(
        self, tool_name: str, tool_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a tool by name with given input.

        Args:
            tool_name: Name of the tool to execute
            tool_input: Input parameters for the tool

        Returns:
            Dict: Tool execution result
        """
        if tool_name == "get_database_schema":
            return self.get_database_schema()
        elif tool_name == "validate_sql":
            return self.validate_sql(tool_input.get("sql_query", ""))
        elif tool_name == "execute_sql":
            return self.execute_sql(tool_input.get("sql_query", ""))
        else:
            return {"error": f"Unknown tool: {tool_name}"}
