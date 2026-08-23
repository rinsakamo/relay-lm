from __future__ import annotations

import asyncio
import json
import time
from contextlib import suppress
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, StrictBool

from relaylm.budget_runtime import CognitiveBudgetRuntimeConfig
from relaylm.cognitive import CognitiveProvider
from relaylm.providers.openai_compatible import ProviderProtocolError
from relaylm.storage.filesystem import CharacterDataError, CharacterDirectory
from relaylm.turn import (
    ContinuityRuntime,
    EventRetrievalBudget,
    MemoryRetrievalBudget,
    run_user_turn,
    run_user_turn_streaming,
)


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="allow")

    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str
    messages: list[ChatMessage] = Field(min_length=1)
    stream: StrictBool = False


class AssistantMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: str


class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: AssistantMessage
    finish_reason: Literal["stop"] = "stop"


class ChatCompletionResponse(BaseModel):
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]


def create_openai_router(
    *,
    character: CharacterDirectory,
    provider: CognitiveProvider,
    memory_budget: MemoryRetrievalBudget | None = None,
    event_budget: EventRetrievalBudget | None = None,
    continuity_runtime: ContinuityRuntime | None = None,
    cognitive_budget: CognitiveBudgetRuntimeConfig | None = None,
) -> APIRouter:
    router = APIRouter()
    turn_lock = asyncio.Lock()

    @router.post("/v1/chat/completions", response_model=ChatCompletionResponse)
    async def chat_completions(request: ChatCompletionRequest):
        content = _last_user_content(request.messages)
        if request.stream:
            if getattr(provider, "stream_generate", None) is None:
                raise HTTPException(
                    status_code=400,
                    detail="streaming is not available for the configured cognitive provider",
                )
            completion_id = f"chatcmpl-{uuid4().hex}"
            created = int(time.time())
            return StreamingResponse(
                _stream_chat_completion(
                    character=character,
                    provider=provider,
                    turn_lock=turn_lock,
                    content=content,
                    completion_id=completion_id,
                    created=created,
                    model=request.model,
                    memory_budget=memory_budget,
                    event_budget=event_budget,
                    continuity_runtime=continuity_runtime,
                    cognitive_budget=cognitive_budget,
                ),
                media_type="text/event-stream",
            )

        async with turn_lock:
            try:
                result = await run_user_turn(
                    character=character,
                    provider=provider,
                    content=content,
                    memory_budget=memory_budget,
                    event_budget=event_budget,
                    continuity_runtime=continuity_runtime,
                    cognitive_budget=cognitive_budget,
                )
            except ProviderProtocolError as exc:
                raise HTTPException(status_code=502, detail="upstream cognitive provider failed") from exc
            except CharacterDataError as exc:
                raise HTTPException(status_code=500, detail="character package is invalid") from exc

        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid4().hex}",
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    message=AssistantMessage(content=result.response),
                )
            ],
        )

    return router


async def _stream_chat_completion(
    *,
    character: CharacterDirectory,
    provider: CognitiveProvider,
    turn_lock: asyncio.Lock,
    content: str,
    completion_id: str,
    created: int,
    model: str,
    memory_budget: MemoryRetrievalBudget | None = None,
    event_budget: EventRetrievalBudget | None = None,
    continuity_runtime: ContinuityRuntime | None = None,
    cognitive_budget: CognitiveBudgetRuntimeConfig | None = None,
):
    queue: asyncio.Queue[tuple[str, object]] = asyncio.Queue()

    async def emit_response_delta(text: str) -> None:
        if text:
            await queue.put(("delta", text))

    async def produce() -> None:
        try:
            async with turn_lock:
                result = await run_user_turn_streaming(
                    character=character,
                    provider=provider,
                    content=content,
                    emit_response_delta=emit_response_delta,
                    memory_budget=memory_budget,
                    event_budget=event_budget,
                    continuity_runtime=continuity_runtime,
                    cognitive_budget=cognitive_budget,
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            await queue.put(("error", exc))
        else:
            await queue.put(("complete", result))

    task = asyncio.create_task(produce())
    first_delta = True
    try:
        while True:
            kind, payload = await queue.get()
            if kind == "delta":
                delta: dict[str, str] = {"content": str(payload)}
                if first_delta:
                    delta["role"] = "assistant"
                    first_delta = False
                yield _sse_payload(
                    {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": delta,
                                "finish_reason": None,
                            }
                        ],
                    }
                )
                continue
            if kind == "complete":
                yield _sse_payload(
                    {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {},
                                "finish_reason": "stop",
                            }
                        ],
                    }
                )
                yield b"data: [DONE]\n\n"
                return
            if kind == "error":
                if not isinstance(payload, (ProviderProtocolError, CharacterDataError)):
                    raise payload  # type: ignore[misc]
                return
    finally:
        if not task.done():
            task.cancel()
        with suppress(asyncio.CancelledError):
            await task


def _sse_payload(payload: dict[str, object]) -> bytes:
    return (
        "data: "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + "\n\n"
    ).encode("utf-8")


def _last_user_content(messages: list[ChatMessage]) -> str:
    for message in reversed(messages):
        if message.role == "user" and message.content.strip():
            return message.content
    raise HTTPException(status_code=400, detail="a non-empty user message is required")
