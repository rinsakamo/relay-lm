from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI

from relaylm.api.openai import create_openai_router
from relaylm.cognitive import CognitiveProvider
from relaylm.providers.openai_compatible import OpenAICompatibleProvider
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.turn import ContinuityRuntime


def create_app(
    *,
    character: CharacterDirectory,
    provider: CognitiveProvider,
    continuity_runtime: ContinuityRuntime | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            close = getattr(provider, "aclose", None)
            if close is not None:
                await close()

    app = FastAPI(title="RelayLM", version="1.0.0.dev0", lifespan=lifespan)
    app.include_router(
        create_openai_router(
            character=character,
            provider=provider,
            continuity_runtime=continuity_runtime,
        )
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


def create_app_from_env() -> FastAPI:
    character_dir = Path(_required_env("RELAYLM_CHARACTER_DIR")).expanduser()
    provider = OpenAICompatibleProvider(
        base_url=_required_env("RELAYLM_PROVIDER_BASE_URL"),
        model=_required_env("RELAYLM_PROVIDER_MODEL"),
        api_key=os.getenv("RELAYLM_PROVIDER_API_KEY"),
    )
    return create_app(character=CharacterDirectory(character_dir), provider=provider)


def main() -> None:
    import uvicorn

    uvicorn.run(
        create_app_from_env(),
        host=os.getenv("RELAYLM_HOST", "127.0.0.1"),
        port=int(os.getenv("RELAYLM_PORT", "8090")),
    )


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise RuntimeError(f"required environment variable is missing: {name}")
    return value