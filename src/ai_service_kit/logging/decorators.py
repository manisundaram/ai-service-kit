"""
Function decorators for comprehensive logging capabilities.
"""

from __future__ import annotations

import asyncio
import functools
import time
import traceback
from typing import Any, Callable, TypeVar, cast

from .setup import get_logger

F = TypeVar("F", bound=Callable[..., Any])


def log_execution_time(
    logger_name: str | None = None,
    log_level: str = "INFO",
    include_args: bool = False,
    include_result: bool = False,
    threshold_ms: float | None = None
) -> Callable[[F], F]:
    """
    Decorator to log function execution time and details.
    
    Args:
        logger_name: Logger name (defaults to function's module)
        log_level: Log level for execution logs
        include_args: Whether to log function arguments
        include_result: Whether to log function result
        threshold_ms: Only log if execution time exceeds threshold
        
    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        logger = get_logger(logger_name or func.__module__)
        log_func = getattr(logger, log_level.lower())
        
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                start_time = time.perf_counter()
                
                log_data = {
                    "function": func.__name__,
                    "function_module": func.__module__,
                }
                
                if include_args:
                    log_data["args"] = args
                    log_data["kwargs"] = kwargs
                
                try:
                    result = await func(*args, **kwargs)
                    execution_time = (time.perf_counter() - start_time) * 1000
                    
                    # Only log if above threshold
                    if threshold_ms is None or execution_time >= threshold_ms:
                        log_data["execution_time_ms"] = round(execution_time, 2)
                        log_data["status"] = "success"
                        
                        if include_result:
                            log_data["result"] = result
                        
                        log_func("Function execution completed", extra=log_data)
                    
                    return result
                
                except Exception as exc:
                    execution_time = (time.perf_counter() - start_time) * 1000
                    log_data["execution_time_ms"] = round(execution_time, 2)
                    log_data["status"] = "error"
                    log_data["error"] = str(exc)
                    log_data["error_type"] = type(exc).__name__
                    
                    logger.error("Function execution failed", extra=log_data)
                    raise
            
            return cast(F, async_wrapper)
        
        else:
            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                start_time = time.perf_counter()
                
                log_data = {
                    "function": func.__name__,
                    "function_module": func.__module__,
                }
                
                if include_args:
                    log_data["args"] = args
                    log_data["kwargs"] = kwargs
                
                try:
                    result = func(*args, **kwargs)
                    execution_time = (time.perf_counter() - start_time) * 1000
                    
                    # Only log if above threshold
                    if threshold_ms is None or execution_time >= threshold_ms:
                        log_data["execution_time_ms"] = round(execution_time, 2)
                        log_data["status"] = "success"
                        
                        if include_result:
                            log_data["result"] = result
                        
                        log_func("Function execution completed", extra=log_data)
                    
                    return result
                
                except Exception as exc:
                    execution_time = (time.perf_counter() - start_time) * 1000
                    log_data["execution_time_ms"] = round(execution_time, 2)
                    log_data["status"] = "error"
                    log_data["error"] = str(exc)
                    log_data["error_type"] = type(exc).__name__
                    
                    logger.error("Function execution failed", extra=log_data)
                    raise
            
            return cast(F, sync_wrapper)
    
    return decorator


def log_errors(
    logger_name: str | None = None,
    log_level: str = "ERROR",
    include_traceback: bool = True,
    include_args: bool = True,
    reraise: bool = True
) -> Callable[[F], F]:
    """
    Decorator to log function errors with detailed context.
    
    Args:
        logger_name: Logger name (defaults to function's module)
        log_level: Log level for error logs
        include_traceback: Whether to include full traceback
        include_args: Whether to log function arguments that caused error
        reraise: Whether to re-raise the exception after logging
        
    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        logger = get_logger(logger_name or func.__module__)
        log_func = getattr(logger, log_level.lower())
        
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:
                    log_data = {
                        "function": func.__name__,
                        "function_module": func.__module__,
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    }
                    
                    if include_args:
                        log_data["args"] = args
                        log_data["kwargs"] = kwargs
                    
                    if include_traceback:
                        log_data["traceback"] = traceback.format_exc()
                    
                    log_func(f"Error in {func.__name__}", extra=log_data)
                    
                    if reraise:
                        raise
                    
                    return None
            
            return cast(F, async_wrapper)
        
        else:
            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    log_data = {
                        "function": func.__name__,
                        "function_module": func.__module__,
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    }
                    
                    if include_args:
                        log_data["args"] = args
                        log_data["kwargs"] = kwargs
                    
                    if include_traceback:
                        log_data["traceback"] = traceback.format_exc()
                    
                    log_func(f"Error in {func.__name__}", extra=log_data)
                    
                    if reraise:
                        raise
                    
                    return None
            
            return cast(F, sync_wrapper)
    
    return decorator


def log_performance(
    logger_name: str | None = None,
    slow_threshold_ms: float = 1000.0,
    very_slow_threshold_ms: float = 5000.0,
    include_memory: bool = False
) -> Callable[[F], F]:
    """
    Decorator to log performance metrics and identify slow functions.
    
    Args:
        logger_name: Logger name (defaults to function's module)
        slow_threshold_ms: Threshold for slow execution warning
        very_slow_threshold_ms: Threshold for very slow execution error
        include_memory: Whether to include memory usage (requires psutil)
        
    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        logger = get_logger(logger_name or func.__module__)
        
        # Try to import memory profiling
        memory_available = False
        if include_memory:
            try:
                import psutil
                memory_available = True
            except ImportError:
                logger.warning(
                    "psutil not available for memory profiling in log_performance decorator"
                )
        
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                start_time = time.perf_counter()
                start_memory = None
                
                if memory_available:
                    import psutil
                    process = psutil.Process()
                    start_memory = process.memory_info().rss
                
                try:
                    result = await func(*args, **kwargs)
                    
                    # Calculate metrics
                    execution_time = (time.perf_counter() - start_time) * 1000
                    
                    log_data = {
                        "function": func.__name__,
                        "function_module": func.__module__,
                        "execution_time_ms": round(execution_time, 2),
                        "performance_status": "normal",
                    }
                    
                    if memory_available and start_memory:
                        import psutil
                        process = psutil.Process()
                        end_memory = process.memory_info().rss
                        memory_delta = end_memory - start_memory
                        log_data["memory_delta_mb"] = round(memory_delta / 1024 / 1024, 2)
                        log_data["memory_peak_mb"] = round(end_memory / 1024 / 1024, 2)
                    
                    # Determine log level based on performance
                    if execution_time >= very_slow_threshold_ms:
                        log_data["performance_status"] = "very_slow"
                        logger.error("Very slow function execution", extra=log_data)
                    elif execution_time >= slow_threshold_ms:
                        log_data["performance_status"] = "slow"
                        logger.warning("Slow function execution", extra=log_data)
                    else:
                        logger.debug("Function performance", extra=log_data)
                    
                    return result
                
                except Exception as exc:
                    execution_time = (time.perf_counter() - start_time) * 1000
                    log_data = {
                        "function": func.__name__,
                        "function_module": func.__module__,
                        "execution_time_ms": round(execution_time, 2),
                        "performance_status": "error",
                        "error": str(exc),
                    }
                    
                    logger.error("Function failed during performance monitoring", extra=log_data)
                    raise
            
            return cast(F, async_wrapper)
        
        else:
            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                start_time = time.perf_counter()
                start_memory = None
                
                if memory_available:
                    import psutil
                    process = psutil.Process()
                    start_memory = process.memory_info().rss
                
                try:
                    result = func(*args, **kwargs)
                    
                    # Calculate metrics
                    execution_time = (time.perf_counter() - start_time) * 1000
                    
                    log_data = {
                        "function": func.__name__,
                        "function_module": func.__module__,
                        "execution_time_ms": round(execution_time, 2),
                        "performance_status": "normal",
                    }
                    
                    if memory_available and start_memory:
                        import psutil
                        process = psutil.Process()
                        end_memory = process.memory_info().rss
                        memory_delta = end_memory - start_memory
                        log_data["memory_delta_mb"] = round(memory_delta / 1024 / 1024, 2)
                        log_data["memory_peak_mb"] = round(end_memory / 1024 / 1024, 2)
                    
                    # Determine log level based on performance
                    if execution_time >= very_slow_threshold_ms:
                        log_data["performance_status"] = "very_slow"
                        logger.error("Very slow function execution", extra=log_data)
                    elif execution_time >= slow_threshold_ms:
                        log_data["performance_status"] = "slow"
                        logger.warning("Slow function execution", extra=log_data)
                    else:
                        logger.debug("Function performance", extra=log_data)
                    
                    return result
                
                except Exception as exc:
                    execution_time = (time.perf_counter() - start_time) * 1000
                    log_data = {
                        "function": func.__name__,
                        "function_module": func.__module__,
                        "execution_time_ms": round(execution_time, 2),
                        "performance_status": "error",
                        "error": str(exc),
                    }
                    
                    logger.error("Function failed during performance monitoring", extra=log_data)
                    raise
            
            return cast(F, sync_wrapper)
    
    return decorator


def log_entry_exit(
    logger_name: str | None = None,
    log_level: str = "DEBUG",
    include_args: bool = True,
    include_result: bool = False
) -> Callable[[F], F]:
    """
    Decorator to log function entry and exit.
    
    Args:
        logger_name: Logger name (defaults to function's module)
        log_level: Log level for entry/exit logs
        include_args: Whether to log function arguments
        include_result: Whether to log function result
        
    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        logger = get_logger(logger_name or func.__module__)
        log_func = getattr(logger, log_level.lower())
        
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                log_data = {
                    "function": func.__name__,
                    "function_module": func.__module__,
                    "phase": "entry",
                }
                
                if include_args:
                    log_data["args"] = args
                    log_data["kwargs"] = kwargs
                
                log_func("Function entry", extra=log_data)
                
                try:
                    result = await func(*args, **kwargs)
                    
                    exit_data = {
                        "function": func.__name__,
                        "function_module": func.__module__,
                        "phase": "exit",
                        "status": "success",
                    }
                    
                    if include_result:
                        exit_data["result"] = result
                    
                    log_func("Function exit", extra=exit_data)
                    
                    return result
                
                except Exception as exc:
                    exit_data = {
                        "function": func.__name__,
                        "function_module": func.__module__,
                        "phase": "exit",
                        "status": "error",
                        "error": str(exc),
                    }
                    
                    logger.error("Function exit with error", extra=exit_data)
                    raise
            
            return cast(F, async_wrapper)
        
        else:
            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                log_data = {
                    "function": func.__name__,
                    "function_module": func.__module__,
                    "phase": "entry",
                }
                
                if include_args:
                    log_data["args"] = args
                    log_data["kwargs"] = kwargs
                
                log_func("Function entry", extra=log_data)
                
                try:
                    result = func(*args, **kwargs)
                    
                    exit_data = {
                        "function": func.__name__,
                        "function_module": func.__module__,
                        "phase": "exit",
                        "status": "success",
                    }
                    
                    if include_result:
                        exit_data["result"] = result
                    
                    log_func("Function exit", extra=exit_data)
                    
                    return result
                
                except Exception as exc:
                    exit_data = {
                        "function": func.__name__,
                        "function_module": func.__module__,
                        "phase": "exit",
                        "status": "error",
                        "error": str(exc),
                    }
                    
                    logger.error("Function exit with error", extra=exit_data)
                    raise
            
            return cast(F, sync_wrapper)
    
    return decorator