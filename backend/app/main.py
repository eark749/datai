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
    Initializes Redis and LangGraph agents on startup.
    """
    import asyncio
    
    # STARTUP
    print("=" * 60)
    print("🚀 Starting Application...")
    print("=" * 60)
    
    try:
        # Initialize in-memory service (no Redis needed)
        print("   🔄 Initializing in-memory state service...")
        from app.services.redis_service import redis_service
        print("   ✅ In-memory service ready")
        
        # Initialize Claude service
        print("   🔄 Initializing Claude service...")
        from app.services.claude_service import claude_service
        print("   ✅ Claude service ready")
        
        # Agent architecture removed - ready for new implementation
        print("   ⚠️  Agent architecture removed - awaiting new implementation")
        
    except Exception as e:
        print(f"\n⚠️  Startup warning: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("✅ Application Ready!")
    print("   ⚠️  Agent System: NOT IMPLEMENTED")
    print("=" * 60 + "\n")
    
    yield  # Application runs here
    
    # SHUTDOWN
    print("\n🛑 Shutting down application...")
    
    try:
        # Close in-memory service
        from app.services.redis_service import redis_service
        redis_service.close()
    except Exception as e:
        print(f"⚠️  Cleanup warning: {str(e)}")
    
    try:
        # Close database connections
        from app.services.db_service import db_connection_manager
        db_connection_manager.close_all_connections()
        print("✅ All database connections closed")
    except Exception as e:
        print(f"⚠️  Database cleanup warning: {str(e)}")


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
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)






