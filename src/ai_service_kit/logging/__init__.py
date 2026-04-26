"""
Production-ready logging module for ai-service-kit.

This module provides comprehensive logging capabilities for production environments
including structured logging, request correlation, performance monitoring, and
FastAPI integration.

Example Usage:
    ```python
    from ai_service_kit.logging import (
        setup_production_logging, 
        get_logger,
        LoggingMiddleware,
        log_execution_time,
        log_errors,
        log_performance,
        Logger,  # Static logger interface
        log      # Short alias for Logger
    )
    
    # Setup production logging
    service_logger = setup_production_logging(
        service_name="my-api",
        log_level="INFO",
        environment="production"
    )
    
    # Add middleware to FastAPI app
    app.add_middleware(LoggingMiddleware)
    
    # Use static logger interface (auto-detects module name)
    def my_function():
        Logger.info("Processing data...")  # or log.info(...)
    
    # Use decorators for function logging
    @log_execution_time()
    @log_errors()
    async def process_data():
        Logger.info("Processing data...")
    ```
"""

from .config import (
    CloudLoggingConfig,
    EnhancedLoggingConfig,
    load_logging_config_from_env,
    setup_enhanced_logging,
    setup_cloud_logging_from_env,
)
from .cloud import create_cloud_handler, CLOUD_HANDLERS
from .decorators import (
    log_entry_exit,
    log_errors,
    log_execution_time,
    log_performance,
)
from .logger import Logger, log
from .middleware import LoggingMiddleware, add_correlation_context, get_correlation_id
from .setup import (
    JSONFormatter,
    LoggingConfig,
    ProductionFormatter,
    configure_uvicorn_logging,
    get_logger,
    setup_production_logging,
)

__all__ = [
    # Enhanced cloud-ready setup  
    "setup_enhanced_logging",
    "setup_cloud_logging_from_env", 
    "load_logging_config_from_env",
    "CloudLoggingConfig",
    "EnhancedLoggingConfig",
    
    # Cloud providers
    "create_cloud_handler",
    "CLOUD_HANDLERS",
    
    # Main setup functions
    "setup_production_logging",
    "get_logger",
    "configure_uvicorn_logging",
    
    # Configuration and formatters
    "LoggingConfig",
    "JSONFormatter", 
    "ProductionFormatter",
    
    # FastAPI middleware
    "LoggingMiddleware",
    "get_correlation_id",
    "add_correlation_context",
    
    # Function decorators
    "log_execution_time",
    "log_errors",
    "log_performance",
    "log_entry_exit",
    
    # Static logger interface
    "Logger",
    "log",  # Short alias
]