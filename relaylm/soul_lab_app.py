"""RelayLM ASGI wrapper with read-only SOUL Lab management routes."""

from __future__ import annotations

import argparse
import os

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from relaylm.app import create_app as create_core_app
from relaylm.config import RelayLMConfig, load_config
from relaylm.soul_lab_management import (
    build_lab_characters_projection,
    build_lab_settings_projection,
    is_loopback_host,
)
from relaylm.soul_lab_observation import (
    LabObservationResponseMiddleware,
    install_lab_observation_runtime_hook,
)
from relaylm.soul_lab_observation_projection import (
    build_lab_last_run_projection,
    build_lab_memory_held_projection,
    build_lab_memory_used_projection,
    build_lab_recent_memory_projection,
    resolve_lab_observation_scope,
)


def create_app(config_path: str | None = None) -> FastAPI:
    install_lab_observation_runtime_hook()
    app = create_core_app(config_path)
    app.add_middleware(LabObservationResponseMiddleware)
    config: RelayLMConfig = app.state.relaylm_config
    configured_loopback = is_loopback_host(config.listen.host)

    def require_loopback_management(request: Request) -> None:
        peer_host = request.client.host if request.client is not None else ""
        if not configured_loopback or not is_loopback_host(peer_host):
            raise HTTPException(
                status_code=403,
                detail="lab_management_requires_loopback_access",
            )

    def observation_scope(character_id: str, namespace: str):
        scope = resolve_lab_observation_scope(
            config,
            character_id=character_id,
            namespace=namespace,
        )
        if not scope.known:
            raise HTTPException(status_code=404, detail="lab_character_not_found")
        return scope

    @app.get("/lab/api/characters", response_model=None)
    async def lab_characters(request: Request) -> JSONResponse:
        require_loopback_management(request)
        projection = build_lab_characters_projection(config)
        return JSONResponse(
            content=projection.model_dump(mode="json"),
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/lab/api/settings", response_model=None)
    async def lab_settings(request: Request) -> JSONResponse:
        require_loopback_management(request)
        projection = build_lab_settings_projection(config)
        return JSONResponse(
            content=projection.model_dump(mode="json"),
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/lab/api/characters/{character_id}/lab/last-run", response_model=None)
    async def lab_last_run(
        character_id: str,
        request: Request,
        namespace: str = Query(min_length=1, max_length=128),
    ) -> JSONResponse:
        require_loopback_management(request)
        projection = build_lab_last_run_projection(
            observation_scope(character_id, namespace)
        )
        return JSONResponse(
            content=projection.model_dump(mode="json"),
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/lab/api/characters/{character_id}/memory/recent", response_model=None)
    async def lab_recent_memory(
        character_id: str,
        request: Request,
        namespace: str = Query(min_length=1, max_length=128),
        limit: int = Query(default=20, ge=1, le=50),
    ) -> JSONResponse:
        require_loopback_management(request)
        projection = build_lab_recent_memory_projection(
            observation_scope(character_id, namespace),
            limit=limit,
        )
        return JSONResponse(
            content=projection.model_dump(mode="json"),
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/lab/api/characters/{character_id}/memory/held", response_model=None)
    async def lab_held_memory(
        character_id: str,
        request: Request,
        namespace: str = Query(min_length=1, max_length=128),
        limit: int = Query(default=20, ge=1, le=50),
    ) -> JSONResponse:
        require_loopback_management(request)
        projection = build_lab_memory_held_projection(
            observation_scope(character_id, namespace),
            limit=limit,
        )
        return JSONResponse(
            content=projection.model_dump(mode="json"),
            headers={"Cache-Control": "no-store"},
        )

    @app.get(
        "/lab/api/characters/{character_id}/lab/last-run/memory/used",
        response_model=None,
    )
    async def lab_used_memory(
        character_id: str,
        request: Request,
        namespace: str = Query(min_length=1, max_length=128),
    ) -> JSONResponse:
        require_loopback_management(request)
        projection = build_lab_memory_used_projection(
            observation_scope(character_id, namespace)
        )
        return JSONResponse(
            content=projection.model_dump(mode="json"),
            headers={"Cache-Control": "no-store"},
        )

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run RelayLM with SOUL Lab management API")
    parser.add_argument("--config", default=None, help="Path to config.yaml")
    args = parser.parse_args()

    if args.config:
        os.environ["RELAYLM_CONFIG"] = args.config

    config = load_config(args.config)
    uvicorn.run(
        "relaylm.soul_lab_app:create_app",
        factory=True,
        host=config.listen.host,
        port=config.listen.port,
    )


if __name__ == "__main__":
    main()
