"""Reusable FastAPI operational endpoint and middleware scaffolding."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from .service import ServiceContext, check_health, get_diagnostics, get_metrics, ping_service


def _import_fastapi_dependencies() -> tuple[Any, Any, Any]:
    try:
        from fastapi import HTTPException
        from fastapi.encoders import jsonable_encoder
        from fastapi.middleware.cors import CORSMiddleware
    except ImportError as exc:
        raise RuntimeError(
            "FastAPI dependencies are not installed. Install fastapi to use health.fastapi helpers."
        ) from exc
    return HTTPException, jsonable_encoder, CORSMiddleware


def apply_operational_middleware(
    app: Any,
    *,
    enable_cors: bool = False,
    cors_origins: Sequence[str] = (),
    enable_logging_middleware: bool = True,
    logging_middleware_kwargs: Mapping[str, Any] | None = None,
) -> None:
    """Apply common CORS and logging middleware used by service templates."""
    _, _, cors_middleware = _import_fastapi_dependencies()

    if enable_cors and cors_origins:
        app.add_middleware(
            cors_middleware,
            allow_origins=list(cors_origins),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    if enable_logging_middleware:
        from ..logging import LoggingMiddleware

        app.add_middleware(LoggingMiddleware, **dict(logging_middleware_kwargs or {}))


def register_operational_endpoints(
    app: Any,
    *,
    prefix: str = "",
    context_getter: Callable[[Any], ServiceContext] | None = None,
    settings_snapshot_getter: Callable[[Any], Mapping[str, Any]] | None = None,
    bootstrap_snapshot_getter: Callable[[Any], Mapping[str, Any]] | None = None,
) -> None:
    """Register reusable operational endpoints on a FastAPI app."""
    http_exception, jsonable_encoder, _ = _import_fastapi_dependencies()

    def _resolve_context(current_app: Any) -> ServiceContext:
        if context_getter is not None:
            return context_getter(current_app)
        return current_app.state.service_context

    @app.get(f"{prefix}/ping")
    async def ping() -> dict[str, Any]:
        try:
            return jsonable_encoder(ping_service(_resolve_context(app)))
        except Exception as exc:
            raise http_exception(status_code=500, detail=f"Ping endpoint failed: {exc}") from exc

    @app.get(f"{prefix}/health")
    async def health() -> dict[str, Any]:
        try:
            return jsonable_encoder(await check_health(_resolve_context(app)))
        except Exception as exc:
            raise http_exception(status_code=500, detail=f"Health check failed: {exc}") from exc

    @app.get(f"{prefix}/diagnostics")
    async def diagnostics() -> dict[str, Any]:
        try:
            return jsonable_encoder(await get_diagnostics(_resolve_context(app)))
        except Exception as exc:
            raise http_exception(status_code=500, detail=f"Diagnostics failed: {exc}") from exc

    @app.get(f"{prefix}/metrics")
    async def metrics() -> dict[str, Any]:
        try:
            return jsonable_encoder(get_metrics(_resolve_context(app)))
        except Exception as exc:
            raise http_exception(status_code=500, detail=f"Metrics collection failed: {exc}") from exc

    @app.get(f"{prefix}/debug/config")
    async def debug_config() -> dict[str, Any]:
        try:
            payload: dict[str, Any] = {}
            if settings_snapshot_getter is not None:
                payload["app"] = dict(settings_snapshot_getter(app))
            if bootstrap_snapshot_getter is not None:
                payload["bootstrap"] = dict(bootstrap_snapshot_getter(app))
            if not payload:
                payload["service"] = jsonable_encoder(_resolve_context(app).configuration())
            return jsonable_encoder(payload)
        except Exception as exc:
            raise http_exception(status_code=500, detail=f"Debug config failed: {exc}") from exc