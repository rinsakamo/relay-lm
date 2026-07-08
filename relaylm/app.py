"""FastAPI entrypoint for RelayLM MVP-0."""

from __future__ import annotations

import argparse
import os
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from relaylm.config import RelayLMConfig, load_config
from relaylm.managed_chat_runtime import handle_managed_chat_completion
from relaylm.relaymem_slp_primary_worker_source_registry import (
    RelayMEMSLPPrimaryWorkerSourceRegistry,
)
from relaylm.routing import list_model_ids


def create_app(config_path: str | None = None) -> FastAPI:
    config = load_config(config_path)
    app = FastAPI(title="RelayLM", version="0.1.0")
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
