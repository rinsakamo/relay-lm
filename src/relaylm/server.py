from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI

from relaylm import __version__
from relaylm.api.openai import create_openai_router
from relaylm.budget_runtime import CognitiveBudgetRuntimeConfig
from relaylm.cognitive import CognitionExecutionMode
from relaylm.cognitive_profile import CognitiveProfileRegistry, CognitiveProfileRuntime
from relaylm.cognition_execution import CognitionPassRequest
from relaylm.providers.openai_compatible_two_pass import OpenAICompatibleTwoPassProvider
from relaylm.storage.cognitive_package import CognitivePackageDirectory
from relaylm.turn import EventRetrievalBudget, MemoryRetrievalBudget
from relaylm.two_pass_turn import CognitionExecutionRuntime


def create_app(
    *,
    profiles: CognitiveProfileRegistry,
    cognition_mode: CognitionExecutionMode = CognitionExecutionMode.SINGLE_PASS,
    pass1_request: CognitionPassRequest | None = None,
    pass2_request: CognitionPassRequest | None = None,
    memory_budget: MemoryRetrievalBudget | None = None,
    event_budget: EventRetrievalBudget | None = None,
    cognitive_budget: CognitiveBudgetRuntimeConfig | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            closed: set[int] = set()
            for profile in profiles.profiles:
                provider_id = id(profile.provider)
                if provider_id in closed:
                    continue
                closed.add(provider_id)
                close = getattr(profile.provider, "aclose", None)
                if close is not None:
                    await close()

    app = FastAPI(title="RelayLM", version=__version__, lifespan=lifespan)
    app.include_router(
        create_openai_router(
            profiles=profiles,
            cognition_mode=cognition_mode,
            pass1_request=pass1_request,
            pass2_request=pass2_request,
            memory_budget=memory_budget,
            event_budget=event_budget,
            cognitive_budget=cognitive_budget,
        )
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


def create_app_from_env() -> FastAPI:
    profile_name = _required_env("RELAYLM_PROFILE_NAME")
    profile_root = Path(_required_env("RELAYLM_PROFILE_ROOT")).expanduser()
    physical_model = _required_env("RELAYLM_PROVIDER_MODEL")
    provider = OpenAICompatibleTwoPassProvider(
        base_url=_required_env("RELAYLM_PROVIDER_BASE_URL"),
        model=physical_model,
        api_key=os.getenv("RELAYLM_PROVIDER_API_KEY"),
    )
    profile = CognitiveProfileRuntime(
        name=profile_name,
        package=CognitivePackageDirectory(profile_root),
        provider=provider,
        physical_model=physical_model,
        cognition_execution_runtime=CognitionExecutionRuntime(),
    )
    return create_app(
        profiles=CognitiveProfileRegistry((profile,)),
        cognition_mode=CognitionExecutionMode.TWO_PASS,
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
