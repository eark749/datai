"""
Schema Service - Extract and cache database schemas
"""
from sqlalchemy import create_engine, inspect, text
from typing import Dict, Any, List, Optional
from uuid import UUID
import traceback

from app.models.db_connection import DBConnection
from app.services.db_service import db_connection_manager
from app.services.redis_service import redis_service


class SchemaService:
    """Service for extracting and caching database schemas"""
    
    @staticmethod
    def extract_schema(db_config: DBConnection) -> Dict[str, Any]:
        """
        Extract complete database schema including tables, columns, types, and relationships.
        
        Args:
            db_config: Database connection configuration
            
        Returns:
            Dict: Complete schema information
        """
        print(f"📊 [SCHEMA] Extracting schema for database: {db_config.database_name}")
        
        try:
            # Get database engine
            engine = db_connection_manager.get_engine(db_config, read_only=True)
            inspector = inspect(engine)
            
            schema_info = {
                "database_name": db_config.database_name,
                "database_type": db_config.db_type,
                "tables": []
            }
            
            # Get all table names
            table_names = inspector.get_table_names(schema=db_config.schema)
            print(f"📊 [SCHEMA] Found {len(table_names)} tables")
            
            # Extract detailed information for each table
            for table_name in table_names:
                table_info = SchemaService._extract_table_info(
                    inspector, 
                    table_name, 
                    db_config.schema
                )
                schema_info["tables"].append(table_info)
            
            print(f"✅ [SCHEMA] Schema extraction complete: {len(schema_info['tables'])} tables processed")
            return schema_info
            
        except Exception as e:
            print(f"❌ [SCHEMA] Error extracting schema: {str(e)}")
            traceback.print_exc()
            raise
    
    @staticmethod
    def _extract_table_info(
        inspector, 
        table_name: str, 
        schema: Optional[str]
    ) -> Dict[str, Any]:
        """
        Extract detailed information for a single table.
        
        Args:
            inspector: SQLAlchemy inspector
            table_name: Name of the table
            schema: Schema name (optional)
            
        Returns:
            Dict: Table information
        """
        table_info = {
            "name": table_name,
            "columns": [],
            "primary_keys": [],
            "foreign_keys": []
        }
        
        # Get columns
        columns = inspector.get_columns(table_name, schema=schema)
        for column in columns:
            table_info["columns"].append({
                "name": column["name"],
                "type": str(column["type"]),
                "nullable": column.get("nullable", True),
                "default": str(column.get("default", "")) if column.get("default") else None
            })
        
        # Get primary keys
        pk_constraint = inspector.get_pk_constraint(table_name, schema=schema)
        if pk_constraint and pk_constraint.get("constrained_columns"):
            table_info["primary_keys"] = pk_constraint["constrained_columns"]
        
        # Get foreign keys
        foreign_keys = inspector.get_foreign_keys(table_name, schema=schema)
        for fk in foreign_keys:
            table_info["foreign_keys"].append({
                "columns": fk.get("constrained_columns", []),
                "referenced_table": fk.get("referred_table"),
                "referenced_columns": fk.get("referred_columns", [])
            })
        
        return table_info
    
    @staticmethod
    async def get_or_load_schema(db_config: DBConnection) -> Dict[str, Any]:
        """
        Get schema from cache or load it from database.
        
        Args:
            db_config: Database connection configuration
            
        Returns:
            Dict: Schema information
        """
        print(f"🔍 [SCHEMA] Checking cache for DB: {db_config.id}")
        
        # Try to get from cache
        cached_schema = await redis_service.get_cached_schema(db_config.id)
        
        if cached_schema:
            print(f"✅ [SCHEMA] Cache HIT! Using cached schema")
            return cached_schema
        
        print(f"⚠️  [SCHEMA] Cache MISS. Loading schema from database...")
        
        # Extract schema from database
        schema = SchemaService.extract_schema(db_config)
        
        # Cache the schema (1 hour TTL)
        await redis_service.cache_schema(db_config.id, schema, ttl_minutes=60)
        print(f"💾 [SCHEMA] Schema cached for 60 minutes")
        
        return schema
    
    @staticmethod
    def format_schema_for_agent(schema: Dict[str, Any]) -> str:
        """
        Format schema into a readable string for the AI agent.
        
        Args:
            schema: Schema dictionary
            
        Returns:
            str: Formatted schema string
        """
        lines = [
            f"Database: {schema['database_name']} ({schema['database_type']})",
            f"Total Tables: {len(schema['tables'])}",
            "",
            "=== SCHEMA DETAILS ==="
        ]
        
        for table in schema['tables']:
            lines.append(f"\nTable: {table['name']}")
            lines.append(f"  Primary Keys: {', '.join(table['primary_keys']) if table['primary_keys'] else 'None'}")
            
            lines.append("  Columns:")
            for col in table['columns']:
                nullable = "NULL" if col['nullable'] else "NOT NULL"
                pk_marker = " [PK]" if col['name'] in table['primary_keys'] else ""
                lines.append(f"    - {col['name']}: {col['type']} {nullable}{pk_marker}")
            
            if table['foreign_keys']:
                lines.append("  Foreign Keys:")
                for fk in table['foreign_keys']:
                    fk_cols = ', '.join(fk['columns'])
                    ref_table = fk['referenced_table']
                    ref_cols = ', '.join(fk['referenced_columns'])
                    lines.append(f"    - {fk_cols} → {ref_table}({ref_cols})")
        
        return "\n".join(lines)


# Global instance
schema_service = SchemaService()





