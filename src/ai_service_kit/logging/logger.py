"""
Simplified logging interface with automatic module detection.
"""

import inspect
from typing import Any, Optional

from .setup import get_logger as _get_logger


class Logger:
    """
    Static logger interface with automatic module name detection.
    
    Usage:
        from ai_service_kit.logging import Logger
        
        def my_function():
            Logger.info("Processing data")  # Auto-detects module name
            Logger.error("Something failed")
    """
    
    _loggers: dict[str, Any] = {}
    
    @classmethod
    def _get_caller_module(cls) -> str:
        """Get the module name of the calling function."""
        frame = inspect.currentframe()
        try:
            # Go up the call stack to find the actual caller
            # Stack: _get_caller_module -> _get_logger -> [info/error/etc] -> actual_caller
            current_frame = frame
            for _ in range(3):  # Skip 3 frames to get to the real caller
                current_frame = current_frame.f_back
                if current_frame is None:
                    break
            
            if current_frame:
                module_name = current_frame.f_globals.get('__name__', 'unknown')
                return module_name
            return 'unknown'
        finally:
            del frame
    
    @classmethod
    def _get_logger(cls, name: Optional[str] = None) -> Any:
        """Get or create a logger for the given name."""
        logger_name = name or cls._get_caller_module()
        
        if logger_name not in cls._loggers:
            cls._loggers[logger_name] = _get_logger(logger_name)
        
        return cls._loggers[logger_name]
    
    @classmethod
    def debug(cls, msg: str, *, name: Optional[str] = None, **kwargs) -> None:
        """Log a debug message."""
        cls._get_logger(name).debug(msg, **kwargs)
    
    @classmethod
    def info(cls, msg: str, *, name: Optional[str] = None, **kwargs) -> None:
        """Log an info message."""
        cls._get_logger(name).info(msg, **kwargs)
    
    @classmethod
    def warning(cls, msg: str, *, name: Optional[str] = None, **kwargs) -> None:
        """Log a warning message."""
        cls._get_logger(name).warning(msg, **kwargs)
    
    @classmethod
    def error(cls, msg: str, *, name: Optional[str] = None, **kwargs) -> None:
        """Log an error message."""
        cls._get_logger(name).error(msg, **kwargs)
    
    @classmethod
    def critical(cls, msg: str, *, name: Optional[str] = None, **kwargs) -> None:
        """Log a critical message."""
        cls._get_logger(name).critical(msg, **kwargs)
    
    @classmethod
    def exception(cls, msg: str, *, name: Optional[str] = None, **kwargs) -> None:
        """Log an exception with traceback."""
        cls._get_logger(name).exception(msg, **kwargs)


# Convenience aliases
log = Logger  # Shorter alias: log.info("message")