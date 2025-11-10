"""
Custom Middleware for FastAPI Application
"""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, status
from fastapi.responses import JSONResponse
import time
import logging

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Configure logging
logger = logging.getLogger(__name__)


async def log_requests_middleware(request: Request, call_next):
    """
    Middleware to log all incoming requests and their processing time.
    
    Args:
        request: Incoming request
        call_next: Next middleware/handler in chain
        
    Returns:
        Response: HTTP response
    """
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url.path}")
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.time() - start_time
    
    # Add processing time header
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log response
    logger.info(
        f"Response: {request.method} {request.url.path} "
        f"Status: {response.status_code} Time: {process_time:.3f}s"
    )
    
    return response


async def error_handling_middleware(request: Request, call_next):
    """
    Middleware for centralized error handling.
    
    Args:
        request: Incoming request
        call_next: Next middleware/handler in chain
        
    Returns:
        Response: HTTP response or error response
    """
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        logger.error(f"Unhandled error: {str(exc)}", exc_info=True)
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error",
                "error": str(exc)
            }
        )


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom handler for rate limit exceeded errors.
    
    Args:
        request: Incoming request
        exc: RateLimitExceeded exception
        
    Returns:
        JSONResponse: Error response
    """
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "detail": "Rate limit exceeded. Please try again later.",
            "retry_after": exc.detail
        }
    )


