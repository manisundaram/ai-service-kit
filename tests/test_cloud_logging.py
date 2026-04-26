"""Test cloud logging configuration and setup."""

import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from ai_service_kit.logging import (
    CloudLoggingConfig,
    EnhancedLoggingConfig,
    load_logging_config_from_env,
    setup_enhanced_logging,
)


class TestCloudLoggingConfig:
    """Test cloud logging configuration."""
    
    def test_cloud_logging_config_creation(self) -> None:
        """Test creating cloud logging configuration."""
        config = CloudLoggingConfig(
            provider="aws",
            level="ERROR",
            config={
                "log_group": "/test/logs",
                "region": "us-west-2"
            }
        )
        
        assert config.provider == "aws"
        assert config.level == "ERROR"
        assert config.enabled is True
        assert config.config["log_group"] == "/test/logs"
        assert config.config["region"] == "us-west-2"
    
    def test_enhanced_logging_config_defaults(self) -> None:
        """Test enhanced logging configuration defaults."""
        config = EnhancedLoggingConfig(service_name="test-service")
        
        assert config.service_name == "test-service"
        assert config.log_level == "INFO"
        assert config.file_log_level == "INFO"
        assert config.error_file_level == "ERROR"
        assert config.structured is True
        assert config.cloud_providers == []
    
    @patch.dict(os.environ, {
        'APP_NAME': 'test-app',
        'APP_ENV': 'testing',
        'LOG_LEVEL': 'DEBUG',
        'FILE_LOG_LEVEL': 'INFO',
        'LOG_STRUCTURED': 'false',
        'LOG_CONSOLE': 'true',
    })
    def test_load_config_from_env_basic(self) -> None:
        """Test loading basic configuration from environment."""
        config = load_logging_config_from_env()
        
        assert config.service_name == "test-app"
        assert config.environment == "testing"
        assert config.log_level == "DEBUG"
        assert config.file_log_level == "INFO"
        assert config.structured is False
        assert config.console_output is True
    
    @patch.dict(os.environ, {
        'APP_NAME': 'test-app',
        'CLOUD_LOGGING_PROVIDERS': 'aws,datadog',
        'AWS_LOGGING_ENABLED': 'true',
        'AWS_LOGGING_LEVEL': 'ERROR',
        'AWS_LOG_GROUP': '/test-app/production',
        'AWS_REGION': 'us-west-2',
        'DATADOG_LOGGING_ENABLED': 'true',
        'DATADOG_LOGGING_LEVEL': 'INFO',
        'DATADOG_API_KEY': 'test-api-key',
    })
    def test_load_config_with_cloud_providers(self) -> None:
        """Test loading configuration with cloud providers."""
        config = load_logging_config_from_env()
        
        assert len(config.cloud_providers) == 2
        
        # Check AWS configuration
        aws_config = next((p for p in config.cloud_providers if p.provider == 'aws'), None)
        assert aws_config is not None
        assert aws_config.level == "ERROR"
        assert aws_config.config["log_group"] == "/test-app/production"
        assert aws_config.config["region"] == "us-west-2"
        
        # Check Datadog configuration
        datadog_config = next((p for p in config.cloud_providers if p.provider == 'datadog'), None)
        assert datadog_config is not None
        assert datadog_config.level == "INFO"
        assert datadog_config.config["api_key"] == "test-api-key"
    
    @patch.dict(os.environ, {
        'CLOUD_LOGGING_PROVIDERS': 'aws',
        'AWS_LOGGING_ENABLED': 'false',  # Explicitly disabled
    })
    def test_disabled_cloud_provider(self) -> None:
        """Test that disabled cloud providers are not included."""
        config = load_logging_config_from_env()
        assert len(config.cloud_providers) == 0
    
    @patch.dict(os.environ, {
        'CLOUD_LOGGING_PROVIDERS': 'azure',
        'AZURE_LOGGING_ENABLED': 'true',
        # Missing AZURE_CONNECTION_STRING
    })
    def test_missing_required_config(self) -> None:
        """Test handling of missing required configuration."""
        with patch('builtins.print') as mock_print:
            config = load_logging_config_from_env()
            assert len(config.cloud_providers) == 0
            mock_print.assert_called_with(
                "Warning: AZURE_CONNECTION_STRING not set, skipping Azure logging"
            )


class TestEnhancedLoggingSetup:
    """Test enhanced logging setup with cloud providers."""
    
    @patch('ai_service_kit.logging.config._setup_production_logging')
    def test_setup_enhanced_logging_basic(self, mock_setup: Mock) -> None:
        """Test enhanced logging setup without cloud providers."""
        config = EnhancedLoggingConfig(
            service_name="test-service",
            log_level="INFO",
            environment="testing"
        )
        
        setup_enhanced_logging(config=config)
        
        # Verify basic setup was called
        mock_setup.assert_called_once_with(
            service_name="test-service",
            log_level="INFO",
            log_dir="./logs",
            max_file_size=10 * 1024 * 1024,
            backup_count=5,
            structured=True,
            console_output=True,
            environment="testing"
        )
    
    @patch('ai_service_kit.logging.config._setup_production_logging')
    @patch('ai_service_kit.logging.config.create_cloud_handler')
    def test_setup_enhanced_logging_with_cloud(
        self, 
        mock_create_handler: Mock, 
        mock_setup: Mock
    ) -> None:
        """Test enhanced logging setup with cloud providers."""
        
        # Mock cloud handler
        mock_handler = Mock()
        mock_create_handler.return_value = mock_handler
        
        config = EnhancedLoggingConfig(
            service_name="test-service",
            cloud_providers=[
                CloudLoggingConfig(
                    provider="aws",
                    level="ERROR",
                    config={"log_group": "/test/logs"}
                )
            ]
        )
        
        with patch('builtins.print') as mock_print:
            setup_enhanced_logging(config=config)
        
        # Verify cloud handler was created
        mock_create_handler.assert_called_once()
        
        # Verify success message
        mock_print.assert_called_with("✅ AWS logging enabled (level: ERROR)")


def test_example_env_file_exists() -> None:
    """Test that the example .env file exists and is readable."""
    import os
    from pathlib import Path
    
    # Get the path to the example.env file
    current_dir = Path(__file__).parent.parent
    example_env = current_dir / "example.env"
    
    assert example_env.exists(), "example.env file should exist"
    
    content = example_env.read_text()
    
    # Check that it contains expected sections
    assert "AWS_LOGGING_ENABLED" in content
    assert "DATADOG_LOGGING_ENABLED" in content
    assert "CLOUD_LOGGING_PROVIDERS" in content
    assert "APP_NAME" in content


if __name__ == "__main__":
    # Run a simple integration test
    with tempfile.TemporaryDirectory() as temp_dir:
        os.environ['LOG_DIR'] = temp_dir
        os.environ['APP_NAME'] = 'integration-test'
        os.environ['LOG_LEVEL'] = 'INFO'
        
        # This should work without cloud providers
        config = load_logging_config_from_env()
        print(f"✅ Loaded config for {config.service_name}")
        
        # Test setup (without actual cloud providers to avoid dependencies)
        config.cloud_providers = []  # Remove any cloud providers for test
        setup_enhanced_logging(config=config)
        print("✅ Enhanced logging setup completed")
        
        # Test static logger
        from ai_service_kit.logging import Logger
        Logger.info("Integration test completed successfully")
        print("✅ Static logger test completed")