"""
Cloud logging handlers for major cloud providers.

This module provides extensible cloud logging support with easy configuration
and per-provider log level control.
"""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type

from .setup import JSONFormatter


class CloudLogHandler(logging.Handler, ABC):
    """Base class for cloud logging handlers."""
    
    def __init__(
        self,
        service_name: str,
        environment: str = "production",
        level: int = logging.INFO,
        **kwargs
    ):
        super().__init__(level)
        self.service_name = service_name
        self.environment = environment
        self.setFormatter(JSONFormatter(service_name, environment))
    
    @abstractmethod
    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to the cloud provider."""
        pass
    
    def format_for_cloud(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Format log record for cloud providers."""
        formatted = self.format(record)
        try:
            return json.loads(formatted)
        except json.JSONDecodeError:
            # Fallback to basic structure
            return {
                "timestamp": record.created,
                "level": record.levelname,
                "message": record.getMessage(),
                "logger": record.name,
                "service": self.service_name,
                "environment": self.environment
            }


class AWSCloudWatchHandler(CloudLogHandler):
    """AWS CloudWatch Logs handler."""
    
    def __init__(
        self,
        service_name: str,
        log_group: str,
        log_stream: Optional[str] = None,
        region: str = "us-east-1",
        environment: str = "production",
        level: int = logging.ERROR,  # Only errors to CloudWatch by default
        **kwargs
    ):
        super().__init__(service_name, environment, level, **kwargs)
        self.log_group = log_group
        self.log_stream = log_stream or f"{service_name}-{environment}"
        self.region = region
        self._client = None
    
    def _get_client(self):
        """Lazy initialization of boto3 client."""
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client('logs', region_name=self.region)
                # Ensure log group exists
                self._ensure_log_group()
            except ImportError:
                raise ImportError(
                    "boto3 is required for AWS CloudWatch logging. "
                    "Install with: pip install boto3"
                )
        return self._client
    
    def _ensure_log_group(self):
        """Ensure the log group exists."""
        try:
            self._client.create_log_group(logGroupName=self.log_group)
        except self._client.exceptions.ResourceAlreadyExistsException:
            pass  # Log group already exists
        except Exception as e:
            # Don't fail logging setup if CloudWatch is unavailable
            print(f"Warning: Could not create CloudWatch log group: {e}")
    
    def emit(self, record: logging.LogRecord) -> None:
        """Send log record to CloudWatch."""
        try:
            client = self._get_client()
            log_data = self.format_for_cloud(record)
            
            # CloudWatch expects a specific format
            log_event = {
                'timestamp': int(record.created * 1000),  # CloudWatch wants milliseconds
                'message': json.dumps(log_data)
            }
            
            client.put_log_events(
                logGroupName=self.log_group,
                logStreamName=self.log_stream,
                logEvents=[log_event]
            )
        except Exception as e:
            # Don't crash the app if cloud logging fails
            print(f"CloudWatch logging failed: {e}")


class AzureMonitorHandler(CloudLogHandler):
    """Azure Monitor/Application Insights handler."""
    
    def __init__(
        self,
        service_name: str,
        connection_string: str,
        environment: str = "production",
        level: int = logging.ERROR,  # Only errors to Azure by default
        **kwargs
    ):
        super().__init__(service_name, environment, level, **kwargs)
        self.connection_string = connection_string
        self._client = None
    
    def _get_client(self):
        """Lazy initialization of Application Insights client."""
        if self._client is None:
            try:
                from applicationinsights import TelemetryClient
                self._client = TelemetryClient(self.connection_string)
            except ImportError:
                raise ImportError(
                    "applicationinsights is required for Azure Monitor logging. "
                    "Install with: pip install applicationinsights"
                )
        return self._client
    
    def emit(self, record: logging.LogRecord) -> None:
        """Send log record to Azure Monitor."""
        try:
            client = self._get_client()
            log_data = self.format_for_cloud(record)
            
            if record.levelno >= logging.ERROR:
                client.track_exception(
                    type_name=log_data.get('error_type', 'Error'),
                    value=log_data.get('message', ''),
                    properties=log_data
                )
            else:
                client.track_trace(
                    message=log_data.get('message', ''),
                    severity=self._map_severity(record.levelno),
                    properties=log_data
                )
            
            client.flush()
        except Exception as e:
            print(f"Azure Monitor logging failed: {e}")
    
    def _map_severity(self, level: int) -> str:
        """Map Python log level to Azure severity."""
        if level >= logging.CRITICAL:
            return 'Critical'
        elif level >= logging.ERROR:
            return 'Error'
        elif level >= logging.WARNING:
            return 'Warning'
        elif level >= logging.INFO:
            return 'Information'
        else:
            return 'Verbose'


class GoogleCloudLoggingHandler(CloudLogHandler):
    """Google Cloud Logging handler."""
    
    def __init__(
        self,
        service_name: str,
        project_id: Optional[str] = None,
        environment: str = "production",
        level: int = logging.WARNING,  # Warnings and above to GCP
        **kwargs
    ):
        super().__init__(service_name, environment, level, **kwargs)
        self.project_id = project_id
        self._client = None
    
    def _get_client(self):
        """Lazy initialization of Google Cloud Logging client."""
        if self._client is None:
            try:
                from google.cloud import logging as gcp_logging
                client = gcp_logging.Client(project=self.project_id)
                self._client = client.logger(self.service_name)
            except ImportError:
                raise ImportError(
                    "google-cloud-logging is required for GCP logging. "
                    "Install with: pip install google-cloud-logging"
                )
        return self._client
    
    def emit(self, record: logging.LogRecord) -> None:
        """Send log record to Google Cloud Logging."""
        try:
            logger = self._get_client()
            log_data = self.format_for_cloud(record)
            
            severity = self._map_severity(record.levelno)
            logger.log_struct(log_data, severity=severity)
        except Exception as e:
            print(f"Google Cloud Logging failed: {e}")
    
    def _map_severity(self, level: int) -> str:
        """Map Python log level to GCP severity."""
        if level >= logging.CRITICAL:
            return 'CRITICAL'
        elif level >= logging.ERROR:
            return 'ERROR'
        elif level >= logging.WARNING:
            return 'WARNING'
        elif level >= logging.INFO:
            return 'INFO'
        else:
            return 'DEBUG'


class DatadogHandler(CloudLogHandler):
    """Datadog logs handler."""
    
    def __init__(
        self,
        service_name: str,
        api_key: str,
        environment: str = "production",
        level: int = logging.INFO,
        **kwargs
    ):
        super().__init__(service_name, environment, level, **kwargs)
        self.api_key = api_key
        self._session = None
    
    def _get_session(self):
        """Lazy initialization of HTTP session."""
        if self._session is None:
            import requests
            self._session = requests.Session()
            self._session.headers.update({
                'DD-API-KEY': self.api_key,
                'Content-Type': 'application/json'
            })
        return self._session
    
    def emit(self, record: logging.LogRecord) -> None:
        """Send log record to Datadog."""
        try:
            session = self._get_session()
            log_data = self.format_for_cloud(record)
            
            # Datadog expects specific format
            payload = {
                'message': log_data.get('message', ''),
                'timestamp': int(record.created * 1000),
                'level': record.levelname.lower(),
                'service': self.service_name,
                'environment': self.environment,
                'logger': record.name,
                **{k: v for k, v in log_data.items() if k not in ['message', 'timestamp', 'level']}
            }
            
            session.post(
                'https://http-intake.logs.datadoghq.com/v1/input/{}'.format(self.api_key),
                json=payload,
                timeout=5
            )
        except Exception as e:
            print(f"Datadog logging failed: {e}")


# Registry for cloud handlers
CLOUD_HANDLERS: Dict[str, Type[CloudLogHandler]] = {
    'aws': AWSCloudWatchHandler,
    'cloudwatch': AWSCloudWatchHandler,
    'azure': AzureMonitorHandler,
    'gcp': GoogleCloudLoggingHandler,
    'google': GoogleCloudLoggingHandler,
    'datadog': DatadogHandler,
}


def create_cloud_handler(
    provider: str,
    service_name: str,
    environment: str = "production",
    level: int = logging.ERROR,
    **config
) -> CloudLogHandler:
    """
    Factory function to create cloud logging handlers.
    
    Args:
        provider: Cloud provider name ('aws', 'azure', 'gcp', 'datadog')
        service_name: Service name for logging
        environment: Environment name
        level: Minimum log level for this handler
        **config: Provider-specific configuration
        
    Returns:
        Configured cloud handler
        
    Examples:
        # AWS CloudWatch (errors only)
        handler = create_cloud_handler(
            'aws',
            'my-api',
            level=logging.ERROR,
            log_group='/my-app/production',
            region='us-west-2'
        )
        
        # Azure Monitor (warnings and above)
        handler = create_cloud_handler(
            'azure',
            'my-api',
            level=logging.WARNING,
            connection_string='InstrumentationKey=...'
        )
    """
    if provider not in CLOUD_HANDLERS:
        raise ValueError(f"Unknown cloud provider: {provider}. Available: {list(CLOUD_HANDLERS.keys())}")
    
    handler_class = CLOUD_HANDLERS[provider]
    return handler_class(
        service_name=service_name,
        environment=environment,
        level=level,
        **config
    )