from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI

from relaylm import __version__
from relaylm.api.openai import create_openai_router
from relaylm.budget_runtime import CognitiveBudgetRuntimeConfig
from relaylm.cognitive import CognitiveProvider, CognitionExecutionMode
from relaylm.cognition_execution import CognitionPassRequest
from relaylm.providers.openai_compatible_two_pass import OpenAICompatibleTwoPassProvider
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.turn import (
    ContinuityRuntime,
    EventRetrievalBudget,
    MemoryRetrievalBudget,
)
from relaylm.two_pass_turn import CognitionExecutionRuntime


def create_app(
    *,
    character: CharacterDirectory,
    provider: CognitiveProvider,
    cognition_mode: CognitionExecutionMode = CognitionExecutionMode.SINGLE_PASS,
    cognition_execution_runtime: CognitionExecutionRuntime | None = None,
    pass1_request: CognitionPassRequest | None = None,
    pass2_request: CognitionPassRequest | None = None,
    memory_budget: MemoryRetrievalBudget | None = None,
    event_budget: EventRetrievalBudget | None = None,
    continuity_runtime: ContinuityRuntime | None = None,
    cognitive_budget: CognitiveBudgetRuntimeConfig | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            close = getattr(provider, "aclose", None)
            if close is not None:
                await close()

    app = FastAPI(title="RelayLM", version=__version__, lifespan=lifespan)
    app.include_router(
        create_openai_router(
            character=character,
            provider=provider,
            cognition_mode=cognition_mode,
            cognition_execution_runtime=cognition_execution_runtime,
            pass1_request=pass1_request,
            pass2_request=pass2_request,
            memory_budget=memory_budget,
            event_budget=event_budget,
            continuity_runtime=continuity_runtime,
            cognitive_budget=cognitive_budget,
        )
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


def create_app_from_env() -> FastAPI:
    character_dir = Path(_required_env("RELAYLM_CHARACTER_DIR")).expanduser()
    provider = OpenAICompatibleTwoPassProvider(
        base_url=_required_env("RELAYLM_PROVIDER_BASE_URL"),
        model=_required_env("RELAYLM_PROVIDER_MODEL"),
        api_key=os.getenv("RELAYLM_PROVIDER_API_KEY"),
    )
    return create_app(
        character=CharacterDirectory(character_dir),
        provider=provider,
        cognition_mode=CognitionExecutionMode.TWO_PASS,
        cognition_execution_runtime=CognitionExecutionRuntime(),
        pass1_request=CognitionPassRequest(),
        pass2_request=CognitionPassRequest(),
    )


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
