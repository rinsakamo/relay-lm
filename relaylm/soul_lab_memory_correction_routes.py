"""Loopback-only SOUL Lab routes for Primary MEM Correct."""
from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from relaylm.config import RelayLMConfig
from relaylm.relaymem_primary_correction import (
    PrimaryCorrectionError,
    apply_primary_memory_correction,
    list_primary_memory_corrections,
    preflight_primary_memory_correction,
)
from relaylm.soul_lab_management import is_loopback_host
from relaylm.soul_lab_memory_correction import (
    LabMemoryCorrectApplyRequest,
    LabMemoryCorrectPreflightRequest,
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
    "store_unavailable": 503,
    "access_refused": 403,
    "response_lost": 503,
    "already_hidden": 409,
}


def install_primary_memory_correction_routes(
    *,
    app: FastAPI,
    config: RelayLMConfig,
    configured_loopback: bool,
) -> None:
    """Install Primary MEM Correct routes without widening non-lab app authority."""

    def require_loopback_management(request: Request) -> None:
        peer_host = request.client.host if request.client is not None else ""
        if not configured_loopback or not is_loopback_host(peer_host):
            raise HTTPException(
                status_code=403,
                detail="lab_management_requires_loopback_access",
            )

    def correction_scope(character_id: str, namespace: str):
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

    def correction_failure(error: PrimaryCorrectionError) -> HTTPException:
        code = error.code if error.code in _ERROR_STATUS else "store_unavailable"
        return HTTPException(status_code=_ERROR_STATUS[code], detail=code)

    @app.post(
        "/lab/api/characters/{character_id}/memory/{memory_id}/correct/preflight",
        response_model=None,
    )
    async def lab_memory_correct_preflight(
        character_id: str,
        memory_id: str,
        request: Request,
        namespace: str = Query(min_length=1, max_length=128),
    ) -> JSONResponse:
        payload = await exact_json(request, LabMemoryCorrectPreflightRequest)
        scope = correction_scope(character_id, namespace)
        try:
            result = preflight_primary_memory_correction(
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
        except PrimaryCorrectionError as error:
            raise correction_failure(error) from None
        return JSONResponse(content=result, headers={"Cache-Control": "no-store"})

    @app.post(
        "/lab/api/characters/{character_id}/memory/{memory_id}/correct",
        response_model=None,
    )
    async def lab_memory_correct_apply(
        character_id: str,
        memory_id: str,
        request: Request,
        namespace: str = Query(min_length=1, max_length=128),
    ) -> JSONResponse:
        payload = await exact_json(request, LabMemoryCorrectApplyRequest)
        scope = correction_scope(character_id, namespace)
        try:
            result = apply_primary_memory_correction(
                store_root=scope.store_root,
                character_id=character_id,
                namespace=namespace,
                memory_id=memory_id,
                expected_revision=payload.expected_revision,
                operation_id=payload.operation_id,
                apply_token=payload.apply_token,
            )
        except PrimaryCorrectionError as error:
            raise correction_failure(error) from None
        return JSONResponse(content=result, headers={"Cache-Control": "no-store"})

    @app.get(
        "/lab/api/characters/{character_id}/memory/{memory_id}/corrections",
        response_model=None,
    )
    async def lab_memory_corrections(
        character_id: str,
        memory_id: str,
        request: Request,
        namespace: str = Query(min_length=1, max_length=128),
    ) -> JSONResponse:
        require_loopback_management(request)
        scope = correction_scope(character_id, namespace)
        try:
            result = list_primary_memory_corrections(
                store_root=scope.store_root,
                namespace=namespace,
                memory_id=memory_id,
            )
        except PrimaryCorrectionError as error:
            raise correction_failure(error) from None
        return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
