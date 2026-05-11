# ai-service-kit

`ai-service-kit` is a standalone Python library that extracts stable reusable abstractions from `semantic-search-api` without bringing over app wiring, FastAPI routes, Chroma implementation details, or project-specific config.

If your goal is to start a new FastAPI service that consumes this kit, use the ai-service-template repository as the starting point and keep ai-service-kit as the shared library dependency.

## Documentation map

- Main package overview and quickstart: [README.md](README.md)
- Credentials and cloud logging configuration details: [CREDENTIALS_AND_CONFIG.md](CREDENTIALS_AND_CONFIG.md)
- Provider architecture and migration guidance: [MIGRATION_NOTES.md](MIGRATION_NOTES.md)

Quick navigation:

- New service setup: start with [README.md](README.md)
- Provider architecture decisions: see [MIGRATION_NOTES.md](MIGRATION_NOTES.md)
- Cloud logging credentials and examples: see [CREDENTIALS_AND_CONFIG.md](CREDENTIALS_AND_CONFIG.md)

Version `0.1.0` includes:

- Provider interfaces, registry, and factory for embedding providers.
- Provider interfaces, registry, and factory for LLM providers.
- **Reusable mock providers** (`MockLLMProvider`, `MockEmbeddingProvider`) for deterministic testing and mock mode — no credentials required.
- Reusable health models and health check abstractions.
- Service operational methods: `check_health()`, `get_diagnostics()`, `get_metrics()`, and `ping_service()`.
- Reusable diagnostics runners for config validation, readiness probes, and benchmarks.
- A reusable FastAPI operational scaffold for CORS, logging middleware, and standard ops endpoints.
- Shared pydantic-settings helpers for env parsing, secret masking, and debug snapshots.
- **Production logging module** with structured logging, request correlation, performance monitoring, and **cloud provider integration** (AWS CloudWatch, Azure Monitor, Google Cloud Logging, Datadog).
- A metrics collector interface with a no-op implementation.
- A default in-memory metrics collector that services can extend.
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
102 passed
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

Provider-specific notes:

- AWS CloudWatch: requires AWS_LOG_GROUP and AWS_REGION, optional AWS_LOG_STREAM
- Azure Monitor: requires AZURE_CONNECTION_STRING
- Google Cloud Logging: optional GCP_PROJECT_ID, uses default credentials if omitted
- Datadog: requires DATADOG_API_KEY

Activation model:

- CLOUD_LOGGING_PROVIDERS is the only activation switch
- Per-provider settings supply configuration details and log levels

**Environment configuration (.env file)**:

```env
# Basic setup
APP_NAME=my-api
LOG_LEVEL=INFO
FILE_LOG_LEVEL=DEBUG

# Enable cloud providers
CLOUD_LOGGING_PROVIDERS=aws,datadog

# AWS CloudWatch (errors only - cost-effective)
AWS_LOGGING_LEVEL=ERROR
AWS_LOG_GROUP=/my-api/production

# Datadog (info+ - rich dashboards)
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

## LLM and Embedding providers

The kit now supports both LLM and embedding provider families.

- Keep LLM and embeddings as separate interfaces.
- Reuse shared provider foundations (`registry`, `factory`, base errors, and usage normalization).
- Built-in providers auto-register on import, so apps can switch providers with env values only.

Example:

```python
from ai_service_kit.providers import (
    BaseLLMProvider,
    LLMProviderFactory,
    BaseEmbeddingProvider,
    ProviderFactory,
)
```

This keeps embedding APIs optimized for batch/vector workflows while preserving chat/completion ergonomics for LLM usage.

Supported providers:

- LLM: `openai`, `gemini`, `anthropic`, `ollama`, `mock`
- Embeddings: `openai`, `gemini`, `anthropic`, `ollama`, `mock`

Provider registration and factory notes:

- LLM providers and embedding providers stay separate at the interface level
- Shared registry, factory, and base provider primitives are centralized in src/ai_service_kit/providers/base.py
- Built-ins are auto-registered into default registries in src/ai_service_kit/providers/builtin.py
- Backward-compatible compatibility modules still exist for older import paths

Factory availability examples:

```python
from ai_service_kit.providers import LLMProviderFactory, ProviderFactory

print(LLMProviderFactory().get_available_providers())
print(ProviderFactory().get_available_providers())
```

Provider-specific configuration notes:

- You can run the same provider for both families (common case), for example OpenAI for LLM and embeddings
- You can split providers by family when needed, for example LLM=Gemini and Embeddings=OpenAI
- Provider names come from env-driven config in your service (`LLM_PROVIDER`, `EMBEDDING_PROVIDER`)
- Settings fallback is intentionally simple (2 levels only):
  - Family-specific provider key first (override)
  - Shared provider key second (default)

Examples:

```env
# Shared defaults (used by both families unless overridden)
OPENAI_API_KEY=shared-openai-key
OPENAI_MODEL=gpt-4o-mini

# Optional family-specific override
LLM_OPENAI_API_KEY=llm-specific-openai-key
EMBEDDING_OPENAI_MODEL=text-embedding-3-large
```

Behavior:

- LLM OpenAI API key: LLM_OPENAI_API_KEY -> OPENAI_API_KEY
- Embedding OpenAI model: EMBEDDING_OPENAI_MODEL -> OPENAI_MODEL

Required env keys by provider:

- OpenAI: `OPENAI_API_KEY` (or family-specific `LLM_OPENAI_API_KEY` / `EMBEDDING_OPENAI_API_KEY`)
- Gemini: `GEMINI_API_KEY` (or family-specific `LLM_GEMINI_API_KEY` / `EMBEDDING_GEMINI_API_KEY`)
- Anthropic: `ANTHROPIC_API_KEY` (or family-specific `LLM_ANTHROPIC_API_KEY` / `EMBEDDING_ANTHROPIC_API_KEY`)
- Ollama: **no API key required** (local server — `OLLAMA_BASE_URL` defaults to `http://localhost:11434`)

Recommended model keys:

- LLM models: `OPENAI_MODEL`, `GEMINI_MODEL`, `ANTHROPIC_MODEL`, `OLLAMA_MODEL`
- Embedding models: `EMBEDDING_OPENAI_MODEL`, `EMBEDDING_GEMINI_MODEL`, `EMBEDDING_ANTHROPIC_MODEL`, `EMBEDDING_OLLAMA_MODEL`

Switching providers without code changes:

```env
# Example A: same provider for both families
LLM_PROVIDER=openai
EMBEDDING_PROVIDER=openai

# Example B: split providers by family
LLM_PROVIDER=anthropic
EMBEDDING_PROVIDER=gemini

# Example C: fully local with Ollama
LLM_PROVIDER=ollama
EMBEDDING_PROVIDER=ollama
OLLAMA_MODEL=llama3.2
EMBEDDING_OLLAMA_MODEL=nomic-embed-text
```

### Ollama (local provider)

Ollama runs on your own machine and requires no API key. It uses the same
provider interface as cloud providers, so switching is a one-env-var change.

**Prerequisites:**

1. [Install Ollama](https://ollama.com/)
2. Pull the models you want to use:
   ```sh
   ollama pull llama3.2
   ollama pull nomic-embed-text
   ```
3. Ensure the Ollama server is running (`ollama serve`).

**Supported Ollama LLM models (common picks):** `llama3.2`, `llama3.1`, `mistral`, `qwen2.5`, `phi4`, `deepseek-r1`

**Supported Ollama embedding models:** `nomic-embed-text` (768d), `mxbai-embed-large` (1024d), `all-minilm` (384d)

**Configuration:**

```env
LLM_PROVIDER=ollama
EMBEDDING_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434   # optional — this is the default
OLLAMA_MODEL=llama3.2
EMBEDDING_OLLAMA_MODEL=nomic-embed-text
```

For rationale and migration details, see [MIGRATION_NOTES.md](MIGRATION_NOTES.md).

## Logging provider activation model

Logging provider activation uses one switch only:

- CLOUD_LOGGING_PROVIDERS controls which providers are active

Provider-specific logging settings (like AWS_LOGGING_LEVEL, AZURE_CONNECTION_STRING, DATADOG_API_KEY) configure those active providers.

Example:

```env
CLOUD_LOGGING_PROVIDERS=aws,datadog

AWS_LOGGING_LEVEL=ERROR
AWS_LOG_GROUP=/my-api/production
AWS_REGION=us-east-1

DATADOG_LOGGING_LEVEL=INFO
DATADOG_API_KEY=your-datadog-api-key
```

For full cloud-credential guidance, see [CREDENTIALS_AND_CONFIG.md](CREDENTIALS_AND_CONFIG.md).

## FastAPI operational scaffold

Use these helpers to avoid repeating startup wiring across sibling services:

```python
from ai_service_kit.health import apply_operational_middleware, register_operational_endpoints

apply_operational_middleware(
    app,
    enable_cors=settings.enable_cors,
    cors_origins=settings.cors_origins,
)

register_operational_endpoints(
    app,
    context_getter=lambda current_app: current_app.state.service_context,
    settings_snapshot_getter=lambda current_app: current_app.state.settings.debug_snapshot(),
)
```

Default endpoints:

- `/ping`
- `/health`
- `/diagnostics`
- `/metrics`
- `/debug/config`

## Settings helpers

The `ai_service_kit.settings` package provides reusable `pydantic-settings` patterns:

- `ServiceSettings` for generic service-level fields.
- `parse_csv_list` for list parsing from env vars.
- `build_provider_config` for normalized provider config selection.
- `resolve_provider_setting` and `build_two_level_provider_config` for family-specific -> shared fallback.

These helpers are intentionally generic; service-specific fields should remain in each service repo.

## Mock providers

`ai_service_kit.providers` ships two reusable mock implementations:

| Class                   | Interface               | Purpose                                                |
| ----------------------- | ----------------------- | ------------------------------------------------------ |
| `MockLLMProvider`       | `BaseLLMProvider`       | Deterministic text responses, no API key needed        |
| `MockEmbeddingProvider` | `BaseEmbeddingProvider` | Deterministic L2-normalized vectors, no API key needed |

Both providers:

- require zero credentials and make zero network calls
- return stable outputs for the same inputs (deterministic via SHA-256 hash + `seed`)
- accept a `latency_ms` config key if you want to simulate network delay in integration tests
- report normalized `usage` fields

**Activating mock providers in a service repo:**

```python
from ai_service_kit.providers import register_mock_providers

if settings.mock_mode:
    register_mock_providers()  # registers "mock" into both default registries

# Later, when building a provider for your family:
embedding_provider = embedding_factory.create_provider(
    "mock" if settings.mock_mode else settings.embedding_provider
)
```

`register_mock_providers()` accepts optional `embedding_registry` and `llm_registry` keyword arguments when you use custom registry instances.

**Config knobs:**

```python
MockLLMProvider({
    "model": "mock-llm",   # model name reported in responses
    "seed": 0,             # integer seed for determinism
    "latency_ms": 0,       # artificial latency (keep small in tests)
    "prefix": "",          # text prepended to every response
    "suffix": "",          # text appended to every response
})

MockEmbeddingProvider({
    "model": "mock-embed", # model name reported in results
    "dimension": 1536,     # output vector length
    "seed": 0,             # integer seed for determinism
    "latency_ms": 0,       # artificial latency (keep small in tests)
})
```

**What stays in service repos:** app-specific mock data, fake business documents, seeded vector corpora, and mock endpoint routes all belong in the service repo — not here.

## Environment configuration

This library does not currently load environment variables or require a `.env` file for unit tests. Keep `.env.example` in the application repo that owns provider credentials, runtime configuration, and service wiring. Add one here only if this library later grows runnable integration tests or examples that directly read environment-based settings.
