# ai-service-kit

`ai-service-kit` is a standalone Python library that extracts stable reusable abstractions from `semantic-search-api` without bringing over app wiring, FastAPI routes, Chroma implementation details, or project-specific config.

Version `0.1.0` includes:

- Provider interfaces, registry, and factory for embedding providers.
- Reusable health models and health check abstractions.
- Service operational methods: `check_health()`, `get_diagnostics()`, `get_metrics()`, and `ping_service()`.
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
22 passed
```

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
