"""
FastAPI middleware for request/response logging with correlation IDs.
"""

from __future__ import annotations

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .setup import get_logger


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for comprehensive request/response logging.
    
    Features:
        - Request correlation IDs for tracing
        - Request/response timing
        - Method, path, status code logging
        - Query parameters and headers (configurable)
        - Response size tracking
        - Error logging with context
        - Configurable log levels per route
    """
    
    def __init__(
        self,
        app,
        *,
        logger_name: str = "http",
        log_request_headers: bool = False,
        log_response_headers: bool = False,
        log_query_params: bool = True,
        log_request_body: bool = False,
        log_response_body: bool = False,
        exclude_paths: list[str] | None = None,
        exclude_health_checks: bool = True,
        max_body_size: int = 1024  # Log only first 1KB of body
    ):
        super().__init__(app)
        self.logger = get_logger(logger_name)
        self.log_request_headers = log_request_headers
        self.log_response_headers = log_response_headers
        self.log_query_params = log_query_params
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.max_body_size = max_body_size
        
        # Default exclude paths
        default_excludes = ["/ping", "/health", "/metrics"] if exclude_health_checks else []
        self.exclude_paths = set(exclude_paths or []) | set(default_excludes)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and response with comprehensive logging."""
        # Generate correlation ID
        correlation_id = str(uuid.uuid4())
        
        # Add correlation ID to request state
        request.state.correlation_id = correlation_id
        
        # Skip logging for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Record start time
        start_time = time.perf_counter()
        
        # Log incoming request
        await self._log_request(request, correlation_id)
        
        # Process request and handle errors
        try:
            response = await call_next(request)
        except Exception as exc:
            # Log error and re-raise
            process_time = time.perf_counter() - start_time
            self.logger.error(
                "Request processing failed",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "process_time_ms": round(process_time * 1000, 2),
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                }
            )
            raise
        
        # Calculate processing time
        process_time = time.perf_counter() - start_time
        
        # Log response
        self._log_response(request, response, correlation_id, process_time)
        
        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response
    
    async def _log_request(self, request: Request, correlation_id: str) -> None:
        """Log incoming request details."""
        log_data = {
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
            "user_agent": request.headers.get("user-agent"),
            "remote_addr": getattr(request.client, "host", None) if request.client else None,
        }
        
        # Add query parameters if enabled
        if self.log_query_params and request.query_params:
            log_data["query_params"] = dict(request.query_params)
        
        # Add request headers if enabled
        if self.log_request_headers:
            log_data["request_headers"] = dict(request.headers)
        
        # Add request body if enabled and content exists
        if self.log_request_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await self._get_request_body(request)
                if body:
                    log_data["request_body"] = body
            except Exception as e:
                log_data["request_body_error"] = str(e)
        
        self.logger.info("Incoming request", extra=log_data)
    
    def _log_response(
        self,
        request: Request,
        response: Response,
        correlation_id: str,
        process_time: float
    ) -> None:
        """Log response details."""
        log_data = {
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time_ms": round(process_time * 1000, 2),
            "response_size": len(response.body) if hasattr(response, "body") else None,
        }
        
        # Add response headers if enabled
        if self.log_response_headers:
            log_data["response_headers"] = dict(response.headers)
        
        # Add response body if enabled
        if self.log_response_body and hasattr(response, "body"):
            try:
                body = self._get_response_body(response)
                if body:
                    log_data["response_body"] = body
            except Exception as e:
                log_data["response_body_error"] = str(e)
        
        # Determine log level based on status code
        if response.status_code >= 500:
            log_level = "error"
        elif response.status_code >= 400:
            log_level = "warning"
        else:
            log_level = "info"
        
        # Log the response
        getattr(self.logger, log_level)("Request completed", extra=log_data)
    
    async def _get_request_body(self, request: Request) -> str | None:
        """Safely extract request body for logging."""
        try:
            # Get content type
            content_type = request.headers.get("content-type", "")
            
            # Only log text-based content
            if not any(ct in content_type.lower() for ct in ["json", "text", "xml"]):
                return f"<binary content: {content_type}>"
            
            # Read body
            body = await request.body()
            if not body:
                return None
            
            # Limit size and decode
            body_text = body[:self.max_body_size].decode("utf-8", errors="replace")
            
            if len(body) > self.max_body_size:
                body_text += f"... (truncated {len(body) - self.max_body_size} bytes)"
            
            return body_text
        except Exception:
            return "<error reading body>"
    
    def _get_response_body(self, response: Response) -> str | None:
        """Safely extract response body for logging."""
        try:
            if not hasattr(response, "body") or not response.body:
                return None
            
            # Get content type
            content_type = response.headers.get("content-type", "")
            
            # Only log text-based content
            if not any(ct in content_type.lower() for ct in ["json", "text", "xml"]):
                return f"<binary content: {content_type}>"
            
            # Limit size and decode
            body_text = response.body[:self.max_body_size].decode("utf-8", errors="replace")
            
            if len(response.body) > self.max_body_size:
                body_text += f"... (truncated {len(response.body) - self.max_body_size} bytes)"
            
            return body_text
        except Exception:
            return "<error reading body>"


def get_correlation_id(request: Request) -> str | None:
    """
    Get correlation ID from request state.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Correlation ID if available, None otherwise
    """
    return getattr(request.state, "correlation_id", None)


def add_correlation_context(logger_name: str, request: Request) -> dict:
    """
    Add correlation context to log extra data.
    
    Args:
        logger_name: Name of the logger
        request: FastAPI request object
        
    Returns:
        Dictionary with correlation context for logging
    """
    correlation_id = get_correlation_id(request)
    context = {}
    
    if correlation_id:
        context["correlation_id"] = correlation_id
        context["method"] = request.method
        context["path"] = request.url.path
    
    return context