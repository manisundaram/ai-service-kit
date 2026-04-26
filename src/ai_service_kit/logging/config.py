"""
Environment-based logging configuration with cloud provider support.

This module reads logging configuration from environment variables and
sets up multiple logging destinations with different log levels.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from .cloud import create_cloud_handler
from .setup import setup_production_logging as _setup_production_logging


@dataclass
class CloudLoggingConfig:
    """Configuration for cloud logging providers."""
    
    provider: str  # 'aws', 'azure', 'gcp', 'datadog'
    enabled: bool = True
    level: str = "ERROR"  # Only errors to cloud by default
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class EnhancedLoggingConfig:
    """Enhanced logging configuration with cloud provider support."""
    
    # Basic logging
    service_name: str
    log_level: str = "INFO"
    log_dir: str = "./logs"
    structured: bool = True
    console_output: bool = True
    environment: str = "production"
    
    # File logging levels (can be different from console)
    file_log_level: str = "INFO"
    error_file_level: str = "ERROR"
    
    # Cloud providers
    cloud_providers: List[CloudLoggingConfig] = field(default_factory=list)
    
    # Performance
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


def parse_cloud_config_from_env() -> List[CloudLoggingConfig]:
    """
    Parse cloud logging configuration from environment variables.
    
    Expected environment variables:
        CLOUD_LOGGING_PROVIDERS=aws,datadog
        
        # AWS CloudWatch
        AWS_LOGGING_ENABLED=true
        AWS_LOGGING_LEVEL=ERROR
        AWS_LOG_GROUP=/my-app/production
        AWS_REGION=us-east-1
        
        # Azure Monitor  
        AZURE_LOGGING_ENABLED=true
        AZURE_LOGGING_LEVEL=WARNING
        AZURE_CONNECTION_STRING=InstrumentationKey=...
        
        # Google Cloud Logging
        GCP_LOGGING_ENABLED=true
        GCP_LOGGING_LEVEL=ERROR
        GCP_PROJECT_ID=my-project
        
        # Datadog
        DATADOG_LOGGING_ENABLED=true
        DATADOG_LOGGING_LEVEL=INFO
        DATADOG_API_KEY=...
    """
    providers = []
    
    # Parse enabled providers
    enabled_providers = os.getenv('CLOUD_LOGGING_PROVIDERS', '').split(',')
    enabled_providers = [p.strip() for p in enabled_providers if p.strip()]
    
    for provider in enabled_providers:
        provider = provider.lower()
        
        # Check if this provider is enabled
        env_key = f"{provider.upper()}_LOGGING_ENABLED"
        if not _str_to_bool(os.getenv(env_key, 'false')):
            continue
        
        # Get provider-specific configuration
        if provider in ('aws', 'cloudwatch'):
            config = CloudLoggingConfig(
                provider='aws',
                level=os.getenv('AWS_LOGGING_LEVEL', 'ERROR'),
                config={
                    'log_group': os.getenv('AWS_LOG_GROUP', '/ai-service/production'),
                    'region': os.getenv('AWS_REGION', 'us-east-1'),
                    'log_stream': os.getenv('AWS_LOG_STREAM'),  # Optional
                }
            )
            
        elif provider == 'azure':
            connection_string = os.getenv('AZURE_CONNECTION_STRING')
            if not connection_string:
                print(f"Warning: AZURE_CONNECTION_STRING not set, skipping Azure logging")
                continue
                
            config = CloudLoggingConfig(
                provider='azure',
                level=os.getenv('AZURE_LOGGING_LEVEL', 'ERROR'),
                config={
                    'connection_string': connection_string,
                }
            )
            
        elif provider in ('gcp', 'google'):
            config = CloudLoggingConfig(
                provider='gcp',
                level=os.getenv('GCP_LOGGING_LEVEL', 'ERROR'),
                config={
                    'project_id': os.getenv('GCP_PROJECT_ID'),  # Optional, uses default
                }
            )
            
        elif provider == 'datadog':
            api_key = os.getenv('DATADOG_API_KEY')
            if not api_key:
                print(f"Warning: DATADOG_API_KEY not set, skipping Datadog logging")
                continue
                
            config = CloudLoggingConfig(
                provider='datadog',
                level=os.getenv('DATADOG_LOGGING_LEVEL', 'INFO'),
                config={
                    'api_key': api_key,
                }
            )
            
        else:
            print(f"Warning: Unknown cloud provider '{provider}', skipping")
            continue
        
        providers.append(config)
    
    return providers


def load_logging_config_from_env(
    service_name: Optional[str] = None,
    environment: Optional[str] = None
) -> EnhancedLoggingConfig:
    """
    Load logging configuration from environment variables.
    
    Expected environment variables:
        # Basic logging
        APP_NAME=my-service
        APP_ENV=production
        LOG_LEVEL=INFO
        LOG_DIR=./logs
        LOG_STRUCTURED=true
        LOG_CONSOLE=true
        
        # Advanced logging levels
        FILE_LOG_LEVEL=DEBUG      # Different level for files
        ERROR_FILE_LEVEL=ERROR    # Separate error file level
        
        # Cloud logging (see parse_cloud_config_from_env for details)
        CLOUD_LOGGING_PROVIDERS=aws,datadog
        AWS_LOGGING_ENABLED=true
        AWS_LOGGING_LEVEL=ERROR
        ...
    """
    # Basic configuration
    config = EnhancedLoggingConfig(
        service_name=service_name or os.getenv('APP_NAME', 'ai-service'),
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        log_dir=os.getenv('LOG_DIR', './logs'),
        structured=_str_to_bool(os.getenv('LOG_STRUCTURED', 'true')),
        console_output=_str_to_bool(os.getenv('LOG_CONSOLE', 'true')),
        environment=environment or os.getenv('APP_ENV', 'production'),
        
        # Advanced file logging
        file_log_level=os.getenv('FILE_LOG_LEVEL', os.getenv('LOG_LEVEL', 'INFO')),
        error_file_level=os.getenv('ERROR_FILE_LEVEL', 'ERROR'),
        
        # Performance
        max_file_size=int(os.getenv('LOG_MAX_FILE_SIZE', str(10 * 1024 * 1024))),
        backup_count=int(os.getenv('LOG_BACKUP_COUNT', '5')),
    )
    
    # Parse cloud providers
    config.cloud_providers = parse_cloud_config_from_env()
    
    return config


def setup_enhanced_logging(
    service_name: Optional[str] = None,
    environment: Optional[str] = None,
    config: Optional[EnhancedLoggingConfig] = None
) -> None:
    """
    Setup production logging with cloud providers from environment configuration.
    
    Args:
        service_name: Service name (defaults to APP_NAME env var)
        environment: Environment (defaults to APP_ENV env var)  
        config: Pre-built configuration (defaults to loading from env)
        
    Example .env file:
        ```env
        APP_NAME=my-api
        APP_ENV=production
        LOG_LEVEL=INFO
        FILE_LOG_LEVEL=DEBUG
        LOG_STRUCTURED=true
        
        # Cloud logging
        CLOUD_LOGGING_PROVIDERS=aws,datadog
        
        # AWS CloudWatch (errors only)
        AWS_LOGGING_ENABLED=true
        AWS_LOGGING_LEVEL=ERROR
        AWS_LOG_GROUP=/my-api/production
        AWS_REGION=us-west-2
        
        # Datadog (info and above)
        DATADOG_LOGGING_ENABLED=true
        DATADOG_LOGGING_LEVEL=INFO
        DATADOG_API_KEY=abc123...
        ```
        
    Usage:
        ```python
        # Setup logging from .env file
        setup_enhanced_logging()
        
        # Use anywhere in your app
        from ai_service_kit.logging import Logger
        Logger.info("This goes to console and files")
        Logger.error("This ALSO goes to AWS CloudWatch and Datadog")
        ```
    """
    if config is None:
        config = load_logging_config_from_env(service_name, environment)
    
    # Setup basic file and console logging
    _setup_production_logging(
        service_name=config.service_name,
        log_level=config.log_level,
        log_dir=config.log_dir,
        max_file_size=config.max_file_size,
        backup_count=config.backup_count,
        structured=config.structured,
        console_output=config.console_output,
        environment=config.environment
    )
    
    # Add cloud handlers
    import logging
    root_logger = logging.getLogger()
    
    for provider_config in config.cloud_providers:
        try:
            # Convert string level to int
            level = getattr(logging, provider_config.level.upper())
            
            # Create cloud handler
            handler = create_cloud_handler(
                provider=provider_config.provider,
                service_name=config.service_name,
                environment=config.environment,
                level=level,
                **provider_config.config
            )
            
            root_logger.addHandler(handler)
            
            print(f"✅ {provider_config.provider.upper()} logging enabled "
                  f"(level: {provider_config.level})")
            
        except Exception as e:
            print(f"❌ Failed to setup {provider_config.provider} logging: {e}")


def _str_to_bool(value: str) -> bool:
    """Convert string to boolean."""
    return value.lower() in ('true', '1', 'yes', 'on', 'enabled')


# Convenience function for common use case
def setup_cloud_logging_from_env() -> None:
    """
    Quick setup function that reads everything from environment variables.
    
    Just call this once at app startup and all logging is configured
    based on your .env file settings.
    """
    setup_enhanced_logging()