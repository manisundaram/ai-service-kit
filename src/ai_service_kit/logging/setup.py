"""
Production-ready logging setup module for ai-service-kit.

This module provides comprehensive logging configuration for production environments
including rotation, structured logging, and environment-aware settings.
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class LoggingConfig:
    """Configuration for production logging setup."""
    
    service_name: str
    log_level: str = "INFO"
    log_dir: str = "./logs"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    structured: bool = True
    console_output: bool = True
    environment: str = "production"
    log_format: Optional[str] = None
    date_format: str = "%Y-%m-%d %H:%M:%S"
    json_ensure_ascii: bool = False


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def __init__(
        self,
        service_name: str,
        environment: str = "production",
        ensure_ascii: bool = False
    ):
        super().__init__()
        self.service_name = service_name
        self.environment = environment
        self.ensure_ascii = ensure_ascii
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
            "environment": self.environment,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from log record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "getMessage",
            }:
                extra_fields[key] = value
        
        if extra_fields:
            log_entry["extra"] = extra_fields
        
        return json.dumps(log_entry, ensure_ascii=self.ensure_ascii)


class ProductionFormatter(logging.Formatter):
    """Production-ready text formatter with consistent format."""
    
    def __init__(
        self,
        service_name: str,
        environment: str = "production",
        format_string: Optional[str] = None
    ):
        self.service_name = service_name
        self.environment = environment
        
        if format_string is None:
            format_string = (
                "%(asctime)s [%(levelname)-8s] "
                f"[{service_name}] %(name)s.%(funcName)s:%(lineno)d - %(message)s"
            )
        
        super().__init__(fmt=format_string, datefmt="%Y-%m-%d %H:%M:%S")


def setup_production_logging(
    service_name: str,
    log_level: str = "INFO",
    log_dir: str = "./logs",
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    structured: bool = True,
    console_output: bool = True,
    environment: str = "production"
) -> logging.Logger:
    """
    Set up production-ready logging with comprehensive features.
    
    Args:
        service_name: Name of the service for identification
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        max_file_size: Maximum size per log file before rotation
        backup_count: Number of backup files to keep
        structured: Use JSON structured logging for files
        console_output: Enable console output
        environment: Environment name (production, development, testing)
    
    Returns:
        Configured logger for the service
        
    Features:
        - Size-based rotating file handler
        - Daily rotating file handler for archives
        - Structured JSON logging for production
        - Console output for development
        - Separate error log file
        - Proper formatting and correlation
    """
    config = LoggingConfig(
        service_name=service_name,
        log_level=log_level.upper(),
        log_dir=log_dir,
        max_file_size=max_file_size,
        backup_count=backup_count,
        structured=structured,
        console_output=console_output,
        environment=environment
    )
    
    # Create log directory
    log_path = Path(config.log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.log_level))
    
    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Setup file logging
    _setup_file_logging(root_logger, config)
    
    # Setup console logging if enabled
    if config.console_output:
        _setup_console_logging(root_logger, config)
    
    # Get service logger
    service_logger = logging.getLogger(service_name)
    service_logger.info(
        f"Production logging configured for {service_name} "
        f"(level={config.log_level}, structured={config.structured}, "
        f"environment={config.environment})"
    )
    
    return service_logger


def _setup_file_logging(logger: logging.Logger, config: LoggingConfig) -> None:
    """Setup file-based logging handlers."""
    log_path = Path(config.log_dir)
    
    # Main application log with rotation
    app_log_file = log_path / f"{config.service_name}.log"
    app_handler = logging.handlers.RotatingFileHandler(
        filename=app_log_file,
        maxBytes=config.max_file_size,
        backupCount=config.backup_count,
        encoding="utf-8"
    )
    
    # Error log for ERROR and CRITICAL levels only
    error_log_file = log_path / f"{config.service_name}_error.log"
    error_handler = logging.handlers.RotatingFileHandler(
        filename=error_log_file,
        maxBytes=config.max_file_size,
        backupCount=config.backup_count,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    
    # Daily rotating handler for long-term storage
    daily_log_file = log_path / f"{config.service_name}_daily.log"
    daily_handler = logging.handlers.TimedRotatingFileHandler(
        filename=daily_log_file,
        when="midnight",
        interval=1,
        backupCount=30,  # Keep 30 days
        encoding="utf-8"
    )
    daily_handler.suffix = "%Y%m%d"
    
    # Configure formatters
    if config.structured:
        json_formatter = JSONFormatter(
            service_name=config.service_name,
            environment=config.environment,
            ensure_ascii=config.json_ensure_ascii
        )
        app_handler.setFormatter(json_formatter)
        error_handler.setFormatter(json_formatter)
        daily_handler.setFormatter(json_formatter)
    else:
        text_formatter = ProductionFormatter(
            service_name=config.service_name,
            environment=config.environment
        )
        app_handler.setFormatter(text_formatter)
        error_handler.setFormatter(text_formatter)
        daily_handler.setFormatter(text_formatter)
    
    # Add handlers to logger
    logger.addHandler(app_handler)
    logger.addHandler(error_handler)
    logger.addHandler(daily_handler)


def _setup_console_logging(logger: logging.Logger, config: LoggingConfig) -> None:
    """Setup console logging handler."""
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Use colored output for development
    if config.environment in ("development", "dev", "local"):
        console_formatter = logging.Formatter(
            f"%(asctime)s [\033[%(levelno)s;1m%(levelname)-8s\033[0m] "
            f"[\033[34m{config.service_name}\033[0m] "
            f"%(name)s.%(funcName)s:%(lineno)d - %(message)s",
            datefmt="%H:%M:%S"
        )
    else:
        console_formatter = ProductionFormatter(
            service_name=config.service_name,
            environment=config.environment,
            format_string=(
                "%(asctime)s [%(levelname)-8s] "
                f"[{config.service_name}] %(name)s - %(message)s"
            )
        )
    
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with consistent naming and configuration.
    
    Args:
        name: Logger name, typically __name__ from the calling module
        
    Returns:
        Configured logger instance
        
    Note:
        This assumes setup_production_logging() has already been called
        to configure the root logger and handlers.
    """
    return logging.getLogger(name)


def configure_uvicorn_logging(log_level: str = "INFO") -> None:
    """
    Configure uvicorn logging to integrate with production logging.
    
    Args:
        log_level: Log level for uvicorn loggers
    """
    # Configure uvicorn loggers
    uvicorn_loggers = [
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access"
    ]
    
    for logger_name in uvicorn_loggers:
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.setLevel(getattr(logging, log_level.upper()))
        # Remove uvicorn's default handlers to use our handlers
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True