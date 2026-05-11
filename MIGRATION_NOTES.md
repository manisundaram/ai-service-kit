# Migration Notes

## Recommendation: keep LLM and embeddings separate

Keep LLM generation and embeddings as separate provider families at the interface level.

- LLM operations are message/completion oriented and need chat-friendly request/response semantics.
- Embedding operations are batch/vector oriented and need dimensional metadata and retrieval-focused ergonomics.
- Forcing both into one interface tends to create awkward APIs for at least one use case.

The kit now shares the foundations while keeping family-specific contracts clean.

## What moved into ai-service-kit

- Shared provider foundation: base provider, generic registry/factory, common provider errors, token usage type.
- LLM provider family: base class, message/response models, errors, registry, and factory.
- Embedding provider family: preserved interface, now backed by the shared foundation.
- Diagnostics runners: config validation, readiness checks, and benchmark helpers.
- Metrics: default in-memory collector implementing the shared metrics interface.
- FastAPI ops scaffold: reusable middleware setup and standard operational endpoints.
- Settings helpers: reusable pydantic-settings base and parsing/masking helpers.

## Suggested service migration steps

1. Replace local provider registry/factory boilerplate with kit abstractions.
2. Keep existing provider implementations, but inherit from `BaseLLMProvider` or `BaseEmbeddingProvider`.
3. Move generic operational endpoints (`/ping`, `/health`, `/diagnostics`, `/metrics`, `/debug/config`) to the kit scaffold.
4. Keep domain-specific diagnostics, routes, and orchestration logic in each service.
5. Replace duplicated env/list/secret parsing with `ServiceSettings` helpers while retaining service-specific fields locally.

## Compatibility notes

- Existing embedding provider patterns remain backward compatible.
- Existing health service context and endpoint payload models are unchanged.
- New abstractions are additive and can be adopted incrementally.
