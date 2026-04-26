"""Test the new static Logger interface."""

import tempfile
from pathlib import Path

from ai_service_kit.logging import Logger, log, setup_production_logging


def test_static_logger_interface() -> None:
    """Test that the static Logger interface works correctly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Setup logging
        setup_production_logging(
            service_name="test-static-logger",
            log_level="DEBUG", 
            log_dir=temp_dir,
            console_output=False
        )
        
        # Test static Logger methods
        Logger.debug("Debug message")
        Logger.info("Info message")  
        Logger.warning("Warning message")
        Logger.error("Error message")
        
        # Test short alias
        log.info("Message via alias")
        
        # Test explicit name
        Logger.info("Custom logger", name="custom.module")
        
        # Cleanup
        import logging
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            handler.close()
            root_logger.removeHandler(handler)
        
        # Verify log file exists and has content
        log_file = Path(temp_dir) / "test-static-logger.log"
        assert log_file.exists()
        
        content = log_file.read_text()
        assert "Debug message" in content
        assert "Info message" in content
        assert "Message via alias" in content


def test_module_name_detection() -> None:
    """Test that __name__ is detected automatically."""
    with tempfile.TemporaryDirectory() as temp_dir:
        setup_production_logging(
            service_name="test-module-detection",
            log_dir=temp_dir,
            console_output=False,
            structured=True  # JSON format to parse module name
        )
        
        Logger.info("Test module detection")
        
        # Cleanup
        import logging
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            handler.close()
            root_logger.removeHandler(handler)
        
        # Verify module name is captured
        log_file = Path(temp_dir) / "test-module-detection.log"
        assert log_file.exists()
        
        content = log_file.read_text()
        # Debug: print what we actually got
        print(f"Log content: {content}")
        # Should contain this test module's name (__main__ when run directly)
        assert "__main__" in content or "test_static_logger" in content


if __name__ == "__main__":
    test_static_logger_interface()
    test_module_name_detection()
    print("✅ Static logger tests passed!")