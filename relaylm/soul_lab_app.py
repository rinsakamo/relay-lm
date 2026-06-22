"""RelayLM ASGI wrapper with read-only SOUL Lab management routes."""

from __future__ import annotations

import argparse
import os

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from relaylm.app import create_app as create_core_app
from relaylm.config import RelayLMConfig, load_config
from relaylm.soul_lab_management import (
    build_lab_characters_projection,
    build_lab_settings_projection,
)


def create_app(config_path: str | None = None) -> FastAPI:
    app = create_core_app(config_path)
    config: RelayLMConfig = app.state.relaylm_config

    @app.get("/lab/api/characters", response_model=None)
    async def lab_characters() -> JSONResponse:
        projection = build_lab_characters_projection(config)
        return JSONResponse(
            content=projection.model_dump(mode="json"),
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/lab/api/settings", response_model=None)
    async def lab_settings() -> JSONResponse:
        projection = build_lab_settings_projection(config)
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
