"""Tests for production logging functionality."""

from __future__ import annotations

import asyncio
import json
import logging
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from ai_service_kit.logging import (
    JSONFormatter,
    LoggingConfig,
    ProductionFormatter,
    get_logger,
    log_errors,
    log_execution_time,
    log_performance,
    setup_production_logging,
)


class TestLoggingSetup:
    """Test production logging setup functionality."""

    def test_logging_config_defaults(self) -> None:
        """Test LoggingConfig default values."""
        config = LoggingConfig(service_name="test-service")
        
        assert config.service_name == "test-service"
        assert config.log_level == "INFO"
        assert config.log_dir == "./logs"
        assert config.max_file_size == 10 * 1024 * 1024
        assert config.backup_count == 5
        assert config.structured is True
        assert config.console_output is True
        assert config.environment == "production"

    def test_setup_production_logging(self) -> None:
        """Test basic production logging setup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = setup_production_logging(
                service_name="test-service",
                log_dir=temp_dir,
                console_output=False  # Disable console for testing
            )
            
            assert logger.name == "test-service"
            
            # Test logging
            logger.info("Test message")
            
            # Cleanup handlers to release file locks
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                handler.close()
                root_logger.removeHandler(handler)
            
            # Check that log files are created
            log_path = Path(temp_dir)
            assert (log_path / "test-service.log").exists()

    def test_json_formatter(self) -> None:
        """Test JSON formatter functionality."""
        formatter = JSONFormatter(
            service_name="test-service",
            environment="test"
        )
        
        # Create mock log record
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="test.py",
            lineno=123,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.funcName = "test_function"
        record.module = "test"
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test.module"
        assert log_data["message"] == "Test message"
        assert log_data["service"] == "test-service"
        assert log_data["environment"] == "test"
        assert log_data["module"] == "test"
        assert log_data["function"] == "test_function"
        assert log_data["line"] == 123
        assert "timestamp" in log_data

    def test_production_formatter(self) -> None:
        """Test production text formatter."""
        formatter = ProductionFormatter(
            service_name="test-service",
            environment="test"
        )
        
        # Create mock log record
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="test.py",
            lineno=123,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.funcName = "test_function"
        
        formatted = formatter.format(record)
        
        assert "[test-service]" in formatted
        assert "test.module.test_function:123" in formatted
        assert "Test message" in formatted
        assert "[INFO    ]" in formatted

    def test_get_logger(self) -> None:
        """Test get_logger function."""
        logger = get_logger("test.module")
        assert logger.name == "test.module"
        assert isinstance(logger, logging.Logger)


class TestLoggingDecorators:
    """Test logging decorators."""

    def test_log_execution_time_sync(self) -> None:
        """Test execution time logging for sync functions."""
        
        @log_execution_time(logger_name="test", include_args=False)  # Disable args to avoid conflict
        def test_function(x: int, y: int) -> int:
            return x + y
        
        # Setup logging first
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_production_logging(
                service_name="test-service",
                log_dir=temp_dir,
                console_output=False
            )
            
            result = test_function(1, 2)
            assert result == 3
            
            # Cleanup handlers
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                handler.close()
                root_logger.removeHandler(handler)

    @pytest.mark.asyncio
    async def test_log_execution_time_async(self) -> None:
        """Test execution time logging for async functions."""
        
        @log_execution_time(logger_name="test", include_result=True)
        async def test_async_function(x: int) -> int:
            await asyncio.sleep(0.001)  # Small delay
            return x * 2
        
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_production_logging(
                service_name="test-service",
                log_dir=temp_dir,
                console_output=False
            )
            
            result = await test_async_function(5)
            assert result == 10
            
            # Cleanup handlers
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                handler.close()
                root_logger.removeHandler(handler)

    def test_log_errors_decorator(self) -> None:
        """Test error logging decorator."""
        
        @log_errors(logger_name="test", reraise=False)
        def failing_function() -> None:
            raise ValueError("Test error")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_production_logging(
                service_name="test-service",
                log_dir=temp_dir,
                console_output=False
            )
            
            result = failing_function()
            assert result is None  # Function doesn't reraise
            
            # Cleanup handlers
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                handler.close()
                root_logger.removeHandler(handler)

    def test_log_performance_decorator(self) -> None:
        """Test performance logging decorator."""
        
        @log_performance(
            logger_name="test",
            slow_threshold_ms=0.1,  # Very low threshold for testing
            include_memory=False
        )
        def slow_function() -> str:
            import time
            time.sleep(0.001)  # Ensure we hit the threshold
            return "done"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_production_logging(
                service_name="test-service",
                log_dir=temp_dir,
                console_output=False
            )
            
            result = slow_function()
            assert result == "done"
            
            # Cleanup handlers
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                handler.close()
                root_logger.removeHandler(handler)


class TestIntegration:
    """Test integration scenarios."""

    def test_complete_logging_setup(self) -> None:
        """Test complete logging setup with all features."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup production logging
            logger = setup_production_logging(
                service_name="integration-test",
                log_level="DEBUG",
                log_dir=temp_dir,
                structured=True,
                console_output=False
            )
            
            # Test various log levels
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")
            
            # Flush handlers to ensure content is written
            root_logger = logging.getLogger()
            for handler in root_logger.handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()
            
            # Check log files exist
            log_path = Path(temp_dir)
            assert (log_path / "integration-test.log").exists()
            assert (log_path / "integration-test_error.log").exists()
            assert (log_path / "integration-test_daily.log").exists()
            
            # Read and verify structured logging
            with open(log_path / "integration-test.log", "r") as f:
                log_content = f.read()
            
            # Cleanup handlers
            for handler in root_logger.handlers[:]:
                handler.close()
                root_logger.removeHandler(handler)
                
            # Should contain JSON formatted logs
            log_lines = log_content.strip().split("\n")
            for line in log_lines:
                if line.strip():  # Skip empty lines
                    log_data = json.loads(line)
                    assert "timestamp" in log_data
                    assert "service" in log_data
                    assert log_data["service"] == "integration-test"