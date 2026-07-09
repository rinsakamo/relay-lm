"""FastAPI entrypoint for RelayLM MVP-0."""

from __future__ import annotations

import argparse
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from relaylm.app_response_finalization import HTTP_CLIENT_STATE_ATTR
from relaylm.config import RelayLMConfig, load_config
from relaylm.managed_chat_runtime import handle_managed_chat_completion
from relaylm.relaymem_slp_primary_worker_source_registry import (
    RelayMEMSLPPrimaryWorkerSourceRegistry,
)
from relaylm.routing import list_model_ids


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Own the shared backend ``httpx.AsyncClient`` for the app's lifetime.

    One client is created here and reused for every backend request
    (connection pooling/keep-alive) instead of opening a fresh client per
    request. Per-route backend timeouts are applied per request in
    ``relaylm.adapter``, so this client is deliberately timeout-neutral.

    Note: test setups that instantiate ``TestClient(app)`` without a context
    manager never run this lifespan. ``get_shared_http_client`` (see
    ``relaylm.app_response_finalization``) lazily creates the same client on
    first use in that case, so both paths converge on a single instance.
    """
    setattr(app.state, HTTP_CLIENT_STATE_ATTR, httpx.AsyncClient())
    try:
        yield
    finally:
        client: httpx.AsyncClient = getattr(app.state, HTTP_CLIENT_STATE_ATTR)
        await client.aclose()


def create_app(config_path: str | None = None) -> FastAPI:
    config = load_config(config_path)
    app = FastAPI(title="RelayLM", version="0.1.0", lifespan=_lifespan)
    app.state.relaylm_config = config
    app.state.relaymem_slp_primary_worker_source_registry = (
        RelayMEMSLPPrimaryWorkerSourceRegistry(
            max_entries=config.relaymem_slp_source_registry_max_entries,
            ttl_seconds=config.relaymem_slp_source_registry_ttl_seconds,
        )
    )

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/v1/models")
    async def models() -> dict[str, Any]:
        return {
            "object": "list",
            "data": [
                {"id": model_id, "object": "model", "owned_by": "relaylm"}
                for model_id in list_model_ids(config)
            ],
        }

    @app.post("/v1/chat/completions", response_model=None)
    async def chat_completions(request: Request) -> JSONResponse | StreamingResponse:
        return await handle_managed_chat_completion(
            request=request,
            config=config,
            source_registry=app.state.relaymem_slp_primary_worker_source_registry,
        )

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run RelayLM")
    parser.add_argument("--config", default=None, help="Path to config.yaml")
    args = parser.parse_args()

    if args.config:
        os.environ["RELAYLM_CONFIG"] = args.config

    config: RelayLMConfig = load_config(args.config)
    uvicorn.run(
        "relaylm.app:create_app",
        factory=True,
        host=config.listen.host,
        port=config.listen.port,
    )


if __name__ == "__main__":
    main()
