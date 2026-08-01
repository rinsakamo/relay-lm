"""Request execution for the Primary MEM Forget Soul Lab routes."""
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
_FORGET_EFFECT_KEYS = {
    "ordinary_retrieval_excluded",
    "relayctx_injection_excluded",
    "physical_deletion",
    "audit_evidence_retained",
    "historical_used_memory_unchanged",
}


@dataclass(frozen=True)
class ForgetRuntimeDependencies:
    config: Any
    resolve_scope: Callable[..., Any]
    preflight: Callable[..., Any]
    apply: Callable[..., Any]
    list_history: Callable[..., Any]
    build_history_projection: Callable[..., Any]
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


def _scope(deps: ForgetRuntimeDependencies, character_id: str, namespace: str):
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


def _safe_preflight_projection(result: dict[str, Any]) -> dict[str, Any]:
    try:
        effects = result["effects"]
        if not isinstance(effects, dict):
            raise KeyError("effects")
        return {
            "schema": "relaylm.lab.memory_forget_preflight.v0",
            "status": result["status"],
            "read_only": result["read_only"],
            "memory_id": result["memory_id"],
            "current_revision": result["current_revision"],
            "current_lifecycle_state": result["current_lifecycle_state"],
            "target_revision": result["target_revision"],
            "target_lifecycle_state": result["target_lifecycle_state"],
            "effects": {key: bool(effects.get(key)) for key in sorted(_FORGET_EFFECT_KEYS)},
            "apply_token": result["apply_token"],
            "expires_at": result["expires_at"],
        }
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=503, detail="store_unavailable") from None


def _safe_apply_projection(memory_id: str, result: Any) -> dict[str, Any]:
    try:
        raw = result.to_log_dict()
        return {
            "schema": "relaylm.lab.memory_forget_apply.v0",
            "status": raw["status"],
            "memory_id": memory_id,
            "prior_revision": raw["prior_revision"],
            "result_revision": raw["result_revision"],
            "lifecycle_state": raw["lifecycle_state"],
            "mutation_state": raw["mutation_state"],
            "retrieval_eligible": raw["retrieval_eligible"],
            "ordinary_retrieval_excluded": raw["retrieval_eligible"] is False,
            "relayctx_injection_excluded": raw["retrieval_eligible"] is False,
            "physical_deletion": False,
            "audit_evidence_retained": True,
            "historical_used_memory_unchanged": True,
            "page_converged": raw["page_converged"],
            "index_converged": raw["index_converged"],
            "log_converged": raw["log_converged"],
            "tombstone_present": raw["tombstone_present"],
            "tombstone_created": raw["tombstone_created"],
            "idempotent_replay": raw["idempotent_replay"],
            "recovery_required": raw["recovery_required"],
            "reason_ids": list(raw["reason_ids"]),
        }
    except (AttributeError, KeyError, TypeError, ValueError):
        raise HTTPException(status_code=503, detail="store_unavailable") from None


async def execute_forget_preflight(
    request: Request,
    character_id: str,
    memory_id: str,
    namespace: str,
    deps: ForgetRuntimeDependencies,
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
            expected_lifecycle_state=payload.expected_lifecycle_state,
            reason=payload.reason,
            operation_id=payload.operation_id,
        )
    except deps.error_type as error:
        raise _failure(error) from None
    return JSONResponse(
        content=_safe_preflight_projection(result),
        headers={"Cache-Control": "no-store"},
    )


async def execute_forget_apply(
    request: Request,
    character_id: str,
    memory_id: str,
    namespace: str,
    deps: ForgetRuntimeDependencies,
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
            expected_lifecycle_state=payload.expected_lifecycle_state,
            reason=payload.reason,
            operation_id=payload.operation_id,
            apply_token=payload.apply_token,
        )
    except deps.error_type as error:
        raise _failure(error) from None
    return JSONResponse(
        content=_safe_apply_projection(memory_id, result),
        headers={"Cache-Control": "no-store"},
    )


def execute_forget_history(
    character_id: str,
    memory_id: str,
    namespace: str,
    deps: ForgetRuntimeDependencies,
) -> JSONResponse:
    scope = _scope(deps, character_id, namespace)
    try:
        result = deps.list_history(
            store_root=scope.store_root,
            namespace=namespace,
            memory_id=memory_id,
        )
        projection = deps.build_history_projection(
            store_root=scope.store_root,
            namespace=namespace,
            memory_id=memory_id,
            base=result,
        )
    except deps.error_type as error:
        raise _failure(error) from None
    return JSONResponse(content=projection, headers={"Cache-Control": "no-store"})
