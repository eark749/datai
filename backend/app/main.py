"""
FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.middleware import (
    limiter,
    log_requests_middleware,
    error_handling_middleware,
    rate_limit_exceeded_handler
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle manager - handles startup and shutdown events.
    Pre-warms schema cache on startup for better performance.
    """
    # STARTUP: Pre-warm schema cache
    print("=" * 60)
    print("🚀 Starting Application...")
    print("=" * 60)
    
    # Use asyncio.create_task to run cache warming in background
    # This prevents blocking and handles cancellation gracefully
    cache_task = None
    
    try:
        import asyncio
        from app.database import SessionLocal
        from app.models.db_connection import DBConnection
        from app.services.db_service import db_connection_manager
        from app.tools.sql_tools import SQLTools
        
        async def warm_cache():
            """Background task to warm schema cache"""
            try:
                # Use run_in_executor for sync database operations
                loop = asyncio.get_event_loop()
                
                def _load_schemas():
                    db = SessionLocal()
                    try:
                        print("\n📦 Pre-warming database schema cache...")
                        
                        # Load all active database connections
                        connections = db.query(DBConnection).filter(
                            DBConnection.is_active == True
                        ).all()
                        
                        if connections:
                            print(f"   Found {len(connections)} active database connection(s)")
                            
                            for conn in connections:
                                try:
                                    print(f"   ⏳ Loading schema for '{conn.name}'...", end=" ", flush=True)
                                    tools = SQLTools(conn, db_connection_manager)
                                    schema = tools.get_database_schema(use_cache=False)
                                    
                                    if "error" not in schema:
                                        table_count = len(schema.get("tables", []))
                                        print(f"✅ ({table_count} tables)")
                                    else:
                                        print(f"⚠️  Error: {schema['error'][:50]}")
                                        
                                except Exception as e:
                                    print(f"❌ Failed: {str(e)[:50]}")
                            
                            print("\n✅ Schema cache warming complete!")
                        else:
                            print("   ℹ️  No active database connections found")
                            
                    finally:
                        db.close()
                
                # Run sync code in executor
                await loop.run_in_executor(None, _load_schemas)
                
            except asyncio.CancelledError:
                print("\n⚠️  Cache warming cancelled (reload detected)")
                raise
            except Exception as e:
                print(f"\n⚠️  Cache warming failed (non-critical): {str(e)}")
        
        # Start cache warming as background task (don't await)
        cache_task = asyncio.create_task(warm_cache())
        
        # Give it a moment to start, but don't block
        try:
            await asyncio.wait_for(asyncio.shield(cache_task), timeout=0.5)
        except asyncio.TimeoutError:
            print("   📦 Cache warming continues in background...")
        except Exception:
            pass
            
    except Exception as e:
        print(f"\n⚠️  Startup warning: {str(e)}")
    
    print("\n" + "=" * 60)
    print("✅ Application Ready!")
    print("=" * 60 + "\n")
    
    yield  # Application runs here
    
    # SHUTDOWN: Clean up resources
    print("\n🛑 Shutting down application...")
    
    # Cancel cache warming task if still running
    if cache_task and not cache_task.done():
        cache_task.cancel()
        try:
            await cache_task
        except asyncio.CancelledError:
            pass
    
    try:
        from app.services.db_service import db_connection_manager
        db_connection_manager.close_all_connections()
        print("✅ All database connections closed")
    except Exception as e:
        print(f"⚠️  Cleanup warning: {str(e)}")


# Create FastAPI application with lifespan
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered SQL to Dashboard generation API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add rate limiter state
app.state.limiter = limiter

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.middleware("http")(log_requests_middleware)
app.middleware("http")(error_handling_middleware)

# Add rate limit exception handler
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


@app.get("/")
async def root():
    """Root endpoint - API health check"""
    return {
        "message": "Agentic SQL Dashboard API",
        "version": settings.APP_VERSION,
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT
    }


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": str(exc) if settings.DEBUG else "An error occurred"
        }
    )


# Include routers
from app.api import auth, chat, database, history

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(database.router, prefix="/api/databases", tags=["Databases"])
app.include_router(history.router, prefix="/api/history", tags=["History"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )

