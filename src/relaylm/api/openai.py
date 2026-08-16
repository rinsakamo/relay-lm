from __future__ import annotations

import asyncio
import time
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from relaylm.cognitive import CognitiveProvider
from relaylm.providers.openai_compatible import ProviderProtocolError
from relaylm.storage.filesystem import CharacterDataError, CharacterDirectory
from relaylm.turn import run_user_turn


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="allow")

    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str
    messages: list[ChatMessage] = Field(min_length=1)
    stream: bool = False


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
) -> APIRouter:
    router = APIRouter()
    turn_lock = asyncio.Lock()

    @router.post("/v1/chat/completions", response_model=ChatCompletionResponse)
    async def chat_completions(request: ChatCompletionRequest) -> ChatCompletionResponse:
        if request.stream:
            raise HTTPException(
                status_code=400,
                detail="streaming is not available in the RelayLM 1.0 M3 complete-response API",
            )

        content = _last_user_content(request.messages)
        async with turn_lock:
            try:
                result = await run_user_turn(
                    character=character,
                    provider=provider,
                    content=content,
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


def _last_user_content(messages: list[ChatMessage]) -> str:
    for message in reversed(messages):
        if message.role == "user" and message.content.strip():
            return message.content
    raise HTTPException(status_code=400, detail="a non-empty user message is required")
