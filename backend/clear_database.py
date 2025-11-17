#!/usr/bin/env python3
"""
Database Data Cleanup Script
Removes all data from PostgreSQL tables while keeping table structures intact.
Handles foreign key constraints safely.
"""
import sys
import os
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError
import argparse
from typing import List

# Add the app directory to the path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import settings


class DatabaseCleaner:
    """Safely clear all data from PostgreSQL database"""
    
    def __init__(self, database_url: str):
        """
        Initialize database cleaner.
        
        Args:
            database_url: PostgreSQL connection URL
        """
        self.engine = create_engine(database_url)
        print(f"🔗 Connected to database")
    
    def get_all_tables(self, schema: str = "public") -> List[str]:
        """
        Get all table names in the database.
        
        Args:
            schema: Schema name (default: public)
            
        Returns:
            List of table names
        """
        inspector = inspect(self.engine)
        tables = inspector.get_table_names(schema=schema)
        print(f"📊 Found {len(tables)} tables in schema '{schema}'")
        return tables
    
    def clear_all_data(self, schema: str = "public", confirm: bool = True):
        """
        Clear all data from all tables.
        
        Args:
            schema: Schema name (default: public)
            confirm: Ask for confirmation before proceeding
        """
        tables = self.get_all_tables(schema)
        
        if not tables:
            print("⚠️  No tables found in database")
            return
        
        print("\n📋 Tables that will be cleared:")
        for i, table in enumerate(tables, 1):
            print(f"   {i}. {table}")
        
        if confirm:
            print("\n⚠️  WARNING: This will DELETE ALL DATA from these tables!")
            print("⚠️  Table structures will be preserved.")
            response = input("\n❓ Are you sure you want to continue? (yes/no): ")
            
            if response.lower() not in ['yes', 'y']:
                print("❌ Operation cancelled")
                return
        
        print("\n🧹 Starting data cleanup...\n")
        
        with self.engine.connect() as conn:
            try:
                # Start transaction
                trans = conn.begin()
                
                # Disable foreign key checks temporarily
                print("🔓 Disabling foreign key constraints...")
                conn.execute(text("SET session_replication_role = 'replica';"))
                
                # Clear each table
                cleared_count = 0
                failed_tables = []
                
                for table in tables:
                    try:
                        print(f"🗑️  Clearing table: {table}...", end=" ")
                        
                        # Use TRUNCATE for better performance
                        conn.execute(text(f'TRUNCATE TABLE "{schema}"."{table}" CASCADE'))
                        
                        # Get count to verify
                        result = conn.execute(text(f'SELECT COUNT(*) FROM "{schema}"."{table}"'))
                        count = result.scalar()
                        
                        if count == 0:
                            print("✅ Cleared")
                            cleared_count += 1
                        else:
                            print(f"⚠️  Still has {count} rows")
                            failed_tables.append(table)
                            
                    except Exception as e:
                        print(f"❌ Failed: {str(e)}")
                        failed_tables.append(table)
                
                # Re-enable foreign key checks
                print("\n🔒 Re-enabling foreign key constraints...")
                conn.execute(text("SET session_replication_role = 'origin';"))
                
                # Commit transaction
                trans.commit()
                
                # Summary
                print("\n" + "="*60)
                print("📊 CLEANUP SUMMARY")
                print("="*60)
                print(f"✅ Successfully cleared: {cleared_count}/{len(tables)} tables")
                
                if failed_tables:
                    print(f"❌ Failed tables ({len(failed_tables)}):")
                    for table in failed_tables:
                        print(f"   - {table}")
                else:
                    print("🎉 All tables cleared successfully!")
                
                print("="*60)
                
            except Exception as e:
                trans.rollback()
                print(f"\n❌ Error during cleanup: {str(e)}")
                print("🔄 All changes rolled back")
                raise
    
    def clear_specific_tables(self, table_names: List[str], schema: str = "public"):
        """
        Clear data from specific tables only.
        
        Args:
            table_names: List of table names to clear
            schema: Schema name (default: public)
        """
        print(f"\n🎯 Clearing {len(table_names)} specific tables...\n")
        
        with self.engine.connect() as conn:
            try:
                trans = conn.begin()
                
                # Disable foreign key checks
                conn.execute(text("SET session_replication_role = 'replica';"))
                
                for table in table_names:
                    try:
                        print(f"🗑️  Clearing table: {table}...", end=" ")
                        conn.execute(text(f'TRUNCATE TABLE "{schema}"."{table}" CASCADE'))
                        print("✅ Cleared")
                    except Exception as e:
                        print(f"❌ Failed: {str(e)}")
                
                # Re-enable foreign key checks
                conn.execute(text("SET session_replication_role = 'origin';"))
                trans.commit()
                
                print("\n✅ Specific tables cleared successfully!")
                
            except Exception as e:
                trans.rollback()
                print(f"\n❌ Error: {str(e)}")
                raise
    
    def close(self):
        """Close database connection"""
        self.engine.dispose()
        print("\n🔌 Database connection closed")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Clear all data from PostgreSQL database tables"
    )
    parser.add_argument(
        "--database-url",
        type=str,
        help="PostgreSQL connection URL (default: from settings.DATABASE_URL)"
    )
    parser.add_argument(
        "--schema",
        type=str,
        default="public",
        help="Database schema name (default: public)"
    )
    parser.add_argument(
        "--tables",
        type=str,
        nargs="+",
        help="Specific tables to clear (default: all tables)"
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt"
    )
    
    args = parser.parse_args()
    
    # Get database URL
    database_url = args.database_url or settings.DATABASE_URL
    
    if not database_url:
        print("❌ Error: No database URL provided")
        print("   Use --database-url or set DATABASE_URL in .env")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("🧹 DATABASE DATA CLEANUP SCRIPT")
    print("="*60)
    print(f"📍 Schema: {args.schema}")
    
    if args.tables:
        print(f"🎯 Mode: Clear specific tables ({len(args.tables)} tables)")
    else:
        print("🎯 Mode: Clear ALL tables")
    
    print("="*60 + "\n")
    
    try:
        # Create cleaner
        cleaner = DatabaseCleaner(database_url)
        
        # Clear data
        if args.tables:
            cleaner.clear_specific_tables(args.tables, schema=args.schema)
        else:
            cleaner.clear_all_data(schema=args.schema, confirm=not args.yes)
        
        # Close connection
        cleaner.close()
        
        print("\n✅ Script completed successfully!\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Script failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

