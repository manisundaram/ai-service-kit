import asyncio

import pytest

fastapi = pytest.importorskip("fastapi")
assert fastapi is not None

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_service_kit.health import (
    CheckResult,
    HealthStatus,
    ServiceContext,
    apply_operational_middleware,
    register_operational_endpoints,
)


class DummyCheck:
    async def run(self) -> CheckResult:
        return CheckResult(name="configuration", status=HealthStatus.HEALTHY, summary="ok")


def test_register_operational_endpoints_adds_standard_routes() -> None:
    app = FastAPI()
    app.state.service_context = ServiceContext(
        service_name="demo",
        service_version="1.0.0",
        health_checks=(DummyCheck(),),
        diagnostics_checks=(DummyCheck(),),
    )

    register_operational_endpoints(app)
    client = TestClient(app)

    assert client.get("/ping").status_code == 200
    assert client.get("/health").status_code == 200
    assert client.get("/diagnostics").status_code == 200
    assert client.get("/metrics").status_code == 200
    assert client.get("/debug/config").status_code == 200


def test_apply_operational_middleware_adds_cors_and_logging() -> None:
    app = FastAPI()
    apply_operational_middleware(
        app,
        enable_cors=True,
        cors_origins=["http://localhost:3000"],
        enable_logging_middleware=True,
    )

    middleware_names = {entry.cls.__name__ for entry in app.user_middleware}
    assert "CORSMiddleware" in middleware_names
    assert "LoggingMiddleware" in middleware_names