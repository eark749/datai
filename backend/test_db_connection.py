"""
Test Database Connection Script
Run this to verify your PostgreSQL connection works before starting the app.

Usage:
    python test_db_connection.py
"""
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_connection():
    """Test PostgreSQL connection"""
    
    # Get DATABASE_URL from environment
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ ERROR: DATABASE_URL not found in environment variables")
        print("\nPlease create a .env file in the backend directory with:")
        print("DATABASE_URL=postgresql://username:password@host:port/database")
        return False
    
    print("🔍 Testing database connection...")
    print(f"📊 Database URL: {database_url.split('@')[1] if '@' in database_url else 'invalid'}")
    print()
    
    try:
        # Create engine
        engine = create_engine(database_url, pool_pre_ping=True)
        
        # Test connection
        with engine.connect() as connection:
            # Try a simple query
            result = connection.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            
            print("✅ Connection successful!")
            print(f"📌 PostgreSQL version: {version[:50]}...")
            print()
            
            # Check if tables exist
            result = connection.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public';
            """))
            table_count = result.fetchone()[0]
            
            if table_count == 0:
                print("⚠️  No tables found. Run migrations:")
                print("   python -m alembic upgrade head")
            else:
                print(f"📋 Found {table_count} tables in database")
                
                # List tables
                result = connection.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name;
                """))
                tables = [row[0] for row in result.fetchall()]
                print(f"   Tables: {', '.join(tables)}")
            
            print()
            print("🎉 Database is ready to use!")
            return True
            
    except OperationalError as e:
        print("❌ Connection failed!")
        print(f"\nError: {str(e)}")
        print("\nCommon issues:")
        print("  1. Check your host, port, and database name")
        print("  2. Verify username and password are correct")
        print("  3. Ensure PostgreSQL is running")
        print("  4. Check if your IP is whitelisted (for AWS RDS)")
        print("  5. Verify security group allows connections on port 5432")
        return False
        
    except SQLAlchemyError as e:
        print("❌ Database error!")
        print(f"\nError: {str(e)}")
        return False
        
    except Exception as e:
        print("❌ Unexpected error!")
        print(f"\nError: {str(e)}")
        return False
    
    finally:
        if 'engine' in locals():
            engine.dispose()


def main():
    """Main function"""
    print("="*60)
    print("PostgreSQL Database Connection Test")
    print("="*60)
    print()
    
    success = test_connection()
    
    print()
    print("="*60)
    
    if success:
        print("✅ Test passed! You can now start the application.")
        sys.exit(0)
    else:
        print("❌ Test failed! Fix the issues above before starting.")
        sys.exit(1)


if __name__ == "__main__":
    main()

