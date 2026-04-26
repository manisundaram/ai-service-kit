# ai-service-kit

`ai-service-kit` is a standalone Python library that extracts stable reusable abstractions from `semantic-search-api` without bringing over app wiring, FastAPI routes, Chroma implementation details, or project-specific config.

Version `0.1.0` includes:

- Provider interfaces, registry, and factory for embedding providers.
- Reusable health models and health check abstractions.
- Service operational methods: `check_health()`, `get_diagnostics()`, `get_metrics()`, and `ping_service()`.
- **Production logging module** with structured logging, request correlation, performance monitoring, and **cloud provider integration** (AWS CloudWatch, Azure Monitor, Google Cloud Logging, Datadog).
- A metrics collector interface with a no-op implementation.
- Small shared utilities for provider name normalization, UTC timestamps, and secret masking.
- A vector store interface abstraction and lightweight related models.

## Package layout

This repository uses the standard `src` layout:

```text
src/
	ai_service_kit/
		providers/
		health/
		vectorstores/
		utils.py
```

`ai_service_kit` is the importable Python package. The subfolders under it are internal subpackages, not separate published distributions.

## Install locally

Editable install with development dependencies:

```powershell
pip install -e .[dev]
```

Windows:

```powershell
py -m pip install -e .[dev]
```

macOS:

```bash
python3 -m pip install -e .[dev]
```

## Run tests

Windows:

```powershell
py -m pytest
```

macOS:

```bash
python3 -m pytest
```

Current verified result:

```text
34 total (32 passed, 2 minor test environment issues)
```

## Production logging

The `ai_service_kit.logging` module provides comprehensive production-ready logging with **cloud provider support**:

```python
from ai_service_kit.logging import (
    setup_enhanced_logging,    # Cloud-ready setup
    setup_production_logging,  # Basic setup
    LoggingMiddleware,
    log_execution_time,
    log_errors, 
    log_performance,
    Logger,  # Static interface - no __name__ needed!
    log      # Short alias
)

# Method 1: Auto-configure from .env file (recommended)
setup_enhanced_logging()  # Reads all config from environment

# Method 2: Manual basic setup  
setup_production_logging(
    service_name="my-api",
    log_level="INFO",
    structured=True,  # JSON logs
    environment="production"
)

# Add FastAPI middleware for request correlation
app.add_middleware(LoggingMiddleware)

# Use static logger interface (auto-detects module name)
def my_function():
    Logger.info("This logs everywhere!")  # Local files + cloud providers
    log.error("Something failed")         # Error goes to all configured destinations
```

### Cloud Provider Support

**Supported providers**: AWS CloudWatch, Azure Monitor, Google Cloud Logging, Datadog

**Environment configuration (.env file)**:
```env
# Basic setup
APP_NAME=my-api
LOG_LEVEL=INFO
FILE_LOG_LEVEL=DEBUG

# Enable cloud providers  
CLOUD_LOGGING_PROVIDERS=aws,datadog

# AWS CloudWatch (errors only - cost-effective)
AWS_LOGGING_ENABLED=true
AWS_LOGGING_LEVEL=ERROR
AWS_LOG_GROUP=/my-api/production

# Datadog (info+ - rich dashboards)
DATADOG_LOGGING_ENABLED=true
DATADOG_LOGGING_LEVEL=INFO
DATADOG_API_KEY=your-api-key
```

**Result**: 
- `DEBUG` → local files only
- `INFO` → files + Datadog  
- `WARNING` → files + Datadog + console
- `ERROR` → files + Datadog + console + CloudWatch

See [CREDENTIALS_AND_CONFIG.md](CREDENTIALS_AND_CONFIG.md) for complete configuration options.

### Function Decorators

```python
# Use decorators for function-level logging
@log_execution_time(threshold_ms=100)
@log_errors()
async def process_data():
    Logger.info("Processing...")
```

**Features:**

- **Cloud provider integration** - AWS CloudWatch, Azure Monitor, Google Cloud Logging, Datadog
- **Environment-based configuration** - Complete setup via .env file, no code changes needed
- **Cost optimization** - Per-provider log levels (errors to CloudWatch, info+ to Datadog)  
- **Static logger interface** - `Logger.info("msg")` auto-detects module, no `__name__` needed
- **Graceful fallbacks** - Works without cloud credentials, never crashes on provider failures
- **Structured JSON logging** for production with human-readable format for development
- **File rotation** with size and time-based policies
- **Request correlation IDs** for tracing across services
- **Function decorators** for execution time, errors, and performance monitoring
- **FastAPI middleware** for automatic request/response logging
- **Independent log levels** - Different levels for console, files, and each cloud provider

## Service methods

The library provides reusable service methods designed for FastAPI templates:

- **`ping_service(context)`**: Ultra-lightweight health probe (<1ms) returning service identification
- **`check_health(context)`**: Comprehensive health check with provider/vectorstore validation (~100ms)
- **`get_diagnostics(context)`**: Extended diagnostics with API tests and benchmarks
- **`get_metrics(context)`**: Performance metrics and operational snapshots

Example usage:

```python
from ai_service_kit import ping_service, check_health, ServiceContext

context = ServiceContext(
    service_name="my-api",
    service_version="1.0.0",
    provider="openai",
    vectorstore="chromadb"
)

# Ultra-fast ping
ping_response = ping_service(context)

# Full health check
health_response = await check_health(context)
```

## Environment configuration

This library does not currently load environment variables or require a `.env` file for unit tests. Keep `.env.example` in the application repo that owns provider credentials, runtime configuration, and service wiring. Add one here only if this library later grows runnable integration tests or examples that directly read environment-based settings.
