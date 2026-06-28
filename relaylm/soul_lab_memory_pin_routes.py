"""Loopback-only SOUL Lab routes for Primary MEM Pin / Unpin."""
from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from relaylm.config import RelayLMConfig
from relaylm.relaymem_primary_pin import PrimaryPinError
from relaylm.relaymem_primary_pin_apply import (
    apply_primary_memory_pin,
    apply_primary_memory_unpin,
    list_primary_memory_pin_history,
    list_primary_memory_unpin_history,
    preflight_primary_memory_pin_apply,
    preflight_primary_memory_unpin_apply,
)
from relaylm.soul_lab_management import is_loopback_host
from relaylm.soul_lab_memory_pin import (
    LabMemoryPinApplyRequest,
    LabMemoryPinPreflightRequest,
    LabMemoryUnpinApplyRequest,
    LabMemoryUnpinPreflightRequest,
)
from relaylm.soul_lab_observation_projection import resolve_lab_observation_scope

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
    "recovery_required": 503,
    "store_unavailable": 503,
    "access_refused": 403,
    "already_pinned": 409,
    "already_unpinned": 409,
}
_PIN_EFFECT_KEYS = {
    "audit_evidence_retained",
    "future_priority_hint_contract",
    "ordinary_retrieval_deleted",
    "ordinary_retrieval_excluded",
    "physical_deletion",
    "semantic_content_changed",
}


def install_primary_memory_pin_routes(
    *,
    app: FastAPI,
    config: RelayLMConfig,
    configured_loopback: bool,
) -> None:
    """Install I-5B Pin / Unpin routes without widening non-lab app authority."""

    def require_loopback_management(request: Request) -> None:
        peer_host = request.client.host if request.client is not None else ""
        if not configured_loopback or not is_loopback_host(peer_host):
            raise HTTPException(
                status_code=403,
                detail="lab_management_requires_loopback_access",
            )

    def pin_scope(character_id: str, namespace: str):
        scope = resolve_lab_observation_scope(
            config,
            character_id=character_id,
            namespace=namespace,
        )
        if not scope.known or not scope.available or scope.store_root is None:
            raise HTTPException(status_code=404, detail="not_found_or_wrong_scope")
        return scope

    async def exact_json(request: Request, model_type):
        require_loopback_management(request)
        if request.headers.get("content-type", "").lower() != "application/json":
            raise HTTPException(status_code=415, detail="invalid_request")
        body = await request.body()
        if not body or len(body) > _MAX_MUTATION_BODY_BYTES:
            raise HTTPException(status_code=422, detail="invalid_request")
        try:
            value = json.loads(body.decode("utf-8"))
            return model_type.model_validate(value)
        except (UnicodeDecodeError, json.JSONDecodeError, ValidationError):
            raise HTTPException(status_code=422, detail="invalid_request") from None

    def pin_failure(error: PrimaryPinError) -> HTTPException:
        code = error.code if error.code in _ERROR_STATUS else "store_unavailable"
        return HTTPException(status_code=_ERROR_STATUS[code], detail=code)

    def safe_pin_preflight_projection(result: dict[str, Any]) -> dict[str, Any]:
        try:
            effects = result["effects"]
            if not isinstance(effects, dict):
                raise KeyError("effects")
            return {
                "schema": result["schema"],
                "status": result["status"],
                "operation_kind": result["operation_kind"],
                "read_only": result["read_only"],
                "memory_id": result["memory_id"],
                "current_revision": result["current_revision"],
                "current_lifecycle_state": result["current_lifecycle_state"],
                "current_mutation_state": result["current_mutation_state"],
                "current_pin_state": result["current_pin_state"],
                "target_pin_state": result["target_pin_state"],
                "pin_state_contract_only": result["pin_state_contract_only"],
                "effects": {
                    key: bool(effects.get(key)) for key in sorted(_PIN_EFFECT_KEYS)
                },
                "apply_token": result["apply_token"],
                "expires_at": result["expires_at"],
            }
        except (KeyError, TypeError, ValueError):
            raise HTTPException(status_code=503, detail="store_unavailable") from None

    def safe_pin_apply_projection(memory_id: str, result: Any) -> dict[str, Any]:
        try:
            raw = result.to_log_dict()
            return {
                "schema": raw["schema"],
                "status": raw["status"],
                "operation_kind": raw["operation_kind"],
                "memory_id": memory_id,
                "current_revision": raw["current_revision"],
                "current_lifecycle_state": raw["current_lifecycle_state"],
                "current_mutation_state": raw["current_mutation_state"],
                "prior_pin_state": raw["prior_pin_state"],
                "target_pin_state": raw["target_pin_state"],
                "retrieval_eligible": raw["retrieval_eligible"],
                "ordinary_retrieval_excluded": raw["ordinary_retrieval_excluded"],
                "priority_hint_enabled": raw["priority_hint_enabled"],
                "semantic_content_changed": raw["semantic_content_changed"],
                "physical_deletion": raw["physical_deletion"],
                "audit_evidence_retained": raw["audit_evidence_retained"],
                "idempotent_replay": raw["idempotent_replay"],
                "effect_applied": raw["effect_applied"],
                "receipt_id": raw["receipt_id"],
                "content_included": raw["content_included"],
                "path_included": raw["path_included"],
                "physical_id_included": raw["physical_id_included"],
                "reason_included": raw["reason_included"],
                "token_included": raw["token_included"],
            }
        except (AttributeError, KeyError, TypeError, ValueError):
            raise HTTPException(status_code=503, detail="store_unavailable") from None

    @app.post(
        "/lab/api/characters/{character_id}/memory/{memory_id}/pin/preflight",
        response_model=None,
    )
    async def lab_memory_pin_preflight(
        character_id: str,
        memory_id: str,
        request: Request,
        namespace: str = Query(min_length=1, max_length=128),
    ) -> JSONResponse:
        payload = await exact_json(request, LabMemoryPinPreflightRequest)
        scope = pin_scope(character_id, namespace)
        try:
            result = preflight_primary_memory_pin_apply(
                store_root=scope.store_root,
                character_id=character_id,
                namespace=namespace,
                memory_id=memory_id,
                expected_revision=payload.expected_revision,
                reason=payload.reason,
                operation_id=payload.operation_id,
            )
        except PrimaryPinError as error:
            raise pin_failure(error) from None
        return JSONResponse(
            content=safe_pin_preflight_projection(result),
            headers={"Cache-Control": "no-store"},
        )

    @app.post("/lab/api/characters/{character_id}/memory/{memory_id}/pin", response_model=None)
    async def lab_memory_pin_apply(
        character_id: str,
        memory_id: str,
        request: Request,
        namespace: str = Query(min_length=1, max_length=128),
    ) -> JSONResponse:
        payload = await exact_json(request, LabMemoryPinApplyRequest)
        scope = pin_scope(character_id, namespace)
        try:
            result = apply_primary_memory_pin(
                store_root=scope.store_root,
                character_id=character_id,
                namespace=namespace,
                memory_id=memory_id,
                expected_revision=payload.expected_revision,
                reason=payload.reason,
                operation_id=payload.operation_id,
                apply_token=payload.apply_token,
            )
        except PrimaryPinError as error:
            raise pin_failure(error) from None
        return JSONResponse(
            content=safe_pin_apply_projection(memory_id, result),
            headers={"Cache-Control": "no-store"},
        )

    @app.get(
        "/lab/api/characters/{character_id}/memory/{memory_id}/pin-history",
        response_model=None,
    )
    async def lab_memory_pin_history(
        character_id: str,
        memory_id: str,
        request: Request,
        namespace: str = Query(min_length=1, max_length=128),
    ) -> JSONResponse:
        require_loopback_management(request)
        scope = pin_scope(character_id, namespace)
        try:
            result = list_primary_memory_pin_history(
                store_root=scope.store_root,
                namespace=namespace,
                memory_id=memory_id,
            )
        except PrimaryPinError as error:
            raise pin_failure(error) from None
        return JSONResponse(content=result, headers={"Cache-Control": "no-store"})

    @app.post(
        "/lab/api/characters/{character_id}/memory/{memory_id}/unpin/preflight",
        response_model=None,
    )
    async def lab_memory_unpin_preflight(
        character_id: str,
        memory_id: str,
        request: Request,
        namespace: str = Query(min_length=1, max_length=128),
    ) -> JSONResponse:
        payload = await exact_json(request, LabMemoryUnpinPreflightRequest)
        scope = pin_scope(character_id, namespace)
        try:
            result = preflight_primary_memory_unpin_apply(
                store_root=scope.store_root,
                character_id=character_id,
                namespace=namespace,
                memory_id=memory_id,
                expected_revision=payload.expected_revision,
                reason=payload.reason,
                operation_id=payload.operation_id,
            )
        except PrimaryPinError as error:
            raise pin_failure(error) from None
        return JSONResponse(
            content=safe_pin_preflight_projection(result),
            headers={"Cache-Control": "no-store"},
        )

    @app.post("/lab/api/characters/{character_id}/memory/{memory_id}/unpin", response_model=None)
    async def lab_memory_unpin_apply(
        character_id: str,
        memory_id: str,
        request: Request,
        namespace: str = Query(min_length=1, max_length=128),
    ) -> JSONResponse:
        payload = await exact_json(request, LabMemoryUnpinApplyRequest)
        scope = pin_scope(character_id, namespace)
        try:
            result = apply_primary_memory_unpin(
                store_root=scope.store_root,
                character_id=character_id,
                namespace=namespace,
                memory_id=memory_id,
                expected_revision=payload.expected_revision,
                reason=payload.reason,
                operation_id=payload.operation_id,
                apply_token=payload.apply_token,
            )
        except PrimaryPinError as error:
            raise pin_failure(error) from None
        return JSONResponse(
            content=safe_pin_apply_projection(memory_id, result),
            headers={"Cache-Control": "no-store"},
        )

    @app.get(
        "/lab/api/characters/{character_id}/memory/{memory_id}/unpin-history",
        response_model=None,
    )
    async def lab_memory_unpin_history(
        character_id: str,
        memory_id: str,
        request: Request,
        namespace: str = Query(min_length=1, max_length=128),
    ) -> JSONResponse:
        require_loopback_management(request)
        scope = pin_scope(character_id, namespace)
        try:
            result = list_primary_memory_unpin_history(
                store_root=scope.store_root,
                namespace=namespace,
                memory_id=memory_id,
            )
        except PrimaryPinError as error:
            raise pin_failure(error) from None
        return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
