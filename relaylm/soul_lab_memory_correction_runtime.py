"""Request execution for the Primary MEM Correct Soul Lab routes."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

_MAX_MUTATION_BODY_BYTES = 16_384
_ERROR_STATUS = {
    "invalid_request": 422,
    "target_not_found": 404,
    "not_found_or_wrong_scope": 404,
    "stale_revision": 409,
    "target_not_active": 409,
    "operation_conflict": 409,
    "preflight_required": 409,
    "token_expired": 409,
    "token_invalid": 403,
    "target_corrupt": 409,
    "reconciliation_required": 503,
    "store_unavailable": 503,
    "access_refused": 403,
    "response_lost": 503,
    "already_hidden": 409,
}


@dataclass(frozen=True)
class CorrectionRuntimeDependencies:
    config: Any
    resolve_scope: Callable[..., Any]
    preflight: Callable[..., Any]
    apply: Callable[..., Any]
    list_history: Callable[..., Any]
    error_type: type[Exception]
    preflight_model: Any
    apply_model: Any


async def _exact_json(request: Request, model_type: Any) -> Any:
    if request.headers.get("content-type", "").lower() != "application/json":
        raise HTTPException(status_code=415, detail="invalid_request")
    body = await request.body()
    if not body or len(body) > _MAX_MUTATION_BODY_BYTES:
        raise HTTPException(status_code=422, detail="invalid_request")
    try:
        return model_type.model_validate(json.loads(body.decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError, ValidationError):
        raise HTTPException(status_code=422, detail="invalid_request") from None


def _scope(deps: CorrectionRuntimeDependencies, character_id: str, namespace: str):
    scope = deps.resolve_scope(
        deps.config, character_id=character_id, namespace=namespace
    )
    if not scope.known or not scope.available or scope.store_root is None:
        raise HTTPException(status_code=404, detail="not_found_or_wrong_scope")
    return scope


def _failure(error: Exception) -> HTTPException:
    error_code = getattr(error, "code", "store_unavailable")
    code = error_code if error_code in _ERROR_STATUS else "store_unavailable"
    return HTTPException(status_code=_ERROR_STATUS[code], detail=code)


async def execute_correction_preflight(
    request: Request,
    character_id: str,
    memory_id: str,
    namespace: str,
    deps: CorrectionRuntimeDependencies,
) -> JSONResponse:
    payload = await _exact_json(request, deps.preflight_model)
    scope = _scope(deps, character_id, namespace)
    try:
        result = deps.preflight(
            store_root=scope.store_root,
            character_id=character_id,
            namespace=namespace,
            memory_id=memory_id,
            expected_revision=payload.expected_revision,
            corrected_title=payload.corrected_title,
            corrected_summary=payload.corrected_summary,
            reason=payload.reason,
            operation_id=payload.operation_id,
        )
    except deps.error_type as error:
        raise _failure(error) from None
    return JSONResponse(content=result, headers={"Cache-Control": "no-store"})


async def execute_correction_apply(
    request: Request,
    character_id: str,
    memory_id: str,
    namespace: str,
    deps: CorrectionRuntimeDependencies,
) -> JSONResponse:
    payload = await _exact_json(request, deps.apply_model)
    scope = _scope(deps, character_id, namespace)
    try:
        result = deps.apply(
            store_root=scope.store_root,
            character_id=character_id,
            namespace=namespace,
            memory_id=memory_id,
            expected_revision=payload.expected_revision,
            operation_id=payload.operation_id,
            apply_token=payload.apply_token,
        )
    except deps.error_type as error:
        raise _failure(error) from None
    return JSONResponse(content=result, headers={"Cache-Control": "no-store"})


def execute_correction_history(
    character_id: str,
    memory_id: str,
    namespace: str,
    deps: CorrectionRuntimeDependencies,
) -> JSONResponse:
    scope = _scope(deps, character_id, namespace)
    try:
        result = deps.list_history(
            store_root=scope.store_root,
            namespace=namespace,
            memory_id=memory_id,
        )
    except deps.error_type as error:
        raise _failure(error) from None
    return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
