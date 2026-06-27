"""Loopback-only SOUL Lab API routes for I-7C held governance."""
from __future__ import annotations

from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from relaylm.relaymem_held_governance import (
    HeldGovernanceRuntimeError,
    apply_held_governance_decision,
    list_held_governance_history,
    preflight_held_governance_decision,
)
from relaylm.soul_lab_held_governance import (
    LabHeldGovernanceDecisionRequest,
    LabHeldGovernancePreflightRequest,
)

_ERROR_STATUS = {
    "invalid_request": 422,
    "target_not_found": 404,
    "not_found_or_wrong_scope": 404,
    "not_held": 409,
    "not_governable": 409,
    "operation_conflict": 409,
    "stale_candidate": 409,
    "preflight_required": 409,
    "token_expired": 409,
    "token_invalid": 403,
    "source_missing": 409,
    "source_corrupt": 409,
    "source_ambiguous": 409,
    "store_unavailable": 503,
    "access_refused": 403,
    "response_lost": 503,
}

_FORBIDDEN_PUBLIC_TOKENS = (
    "source_evidence_digest",
    "candidate_digest",
    "reason_digest",
    "token_digest",
    "source_path",
    "protected_source",
)


def install_held_governance_routes(
    app: FastAPI,
    *,
    require_loopback_management: Callable[[Request], None],
    observation_scope: Callable[[str, str], Any],
    exact_json: Callable[[Request, Any], Any],
) -> None:
    """Install I-7C routes into the existing SOUL Lab management boundary."""

    def failure(error: HeldGovernanceRuntimeError) -> HTTPException:
        code = error.code if error.code in _ERROR_STATUS else "store_unavailable"
        return HTTPException(status_code=_ERROR_STATUS[code], detail=code)

    def safe_projection(value: dict[str, Any]) -> dict[str, Any]:
        serialized = repr(value)
        if any(token in serialized for token in _FORBIDDEN_PUBLIC_TOKENS):
            raise HTTPException(status_code=503, detail="response_lost")
        return value

    def scope_for(character_id: str, namespace: str):
        scope = observation_scope(character_id, namespace)
        if not getattr(scope, "available", False) or getattr(scope, "store_root", None) is None:
            raise HTTPException(status_code=404, detail="not_found_or_wrong_scope")
        return scope

    @app.post(
        "/lab/api/characters/{character_id}/held/{candidate_id}/apply/preflight",
        response_model=None,
    )
    async def lab_held_apply_preflight(
        character_id: str,
        candidate_id: str,
        request: Request,
        namespace: str = Query(min_length=1, max_length=128),
        scope: str = Query(default="primary_formation", min_length=1, max_length=128),
    ) -> JSONResponse:
        payload = await exact_json(request, LabHeldGovernancePreflightRequest)
        resolved = scope_for(character_id, namespace)
        try:
            result = preflight_held_governance_decision(
                resolved.store_root,
                candidate_id=candidate_id,
                action="apply",
                expected_character_id=character_id,
                expected_namespace=namespace,
                expected_scope=scope,
                operation_id=payload.operation_id,
                reason=payload.reason,
            )
        except HeldGovernanceRuntimeError as error:
            raise failure(error) from None
        return JSONResponse(content=safe_projection(result), headers={"Cache-Control": "no-store"})

    @app.post(
        "/lab/api/characters/{character_id}/held/{candidate_id}/apply",
        response_model=None,
    )
    async def lab_held_apply(
        character_id: str,
        candidate_id: str,
        request: Request,
        namespace: str = Query(min_length=1, max_length=128),
        scope: str = Query(default="primary_formation", min_length=1, max_length=128),
    ) -> JSONResponse:
        payload = await exact_json(request, LabHeldGovernanceDecisionRequest)
        resolved = scope_for(character_id, namespace)
        try:
            result = apply_held_governance_decision(
                resolved.store_root,
                candidate_id=candidate_id,
                action="apply",
                expected_character_id=character_id,
                expected_namespace=namespace,
                expected_scope=scope,
                operation_id=payload.operation_id,
                reason=payload.reason,
                apply_token=payload.apply_token,
            )
        except HeldGovernanceRuntimeError as error:
            raise failure(error) from None
        return JSONResponse(content=safe_projection(result), headers={"Cache-Control": "no-store"})

    @app.post(
        "/lab/api/characters/{character_id}/held/{candidate_id}/discard/preflight",
        response_model=None,
    )
    async def lab_held_discard_preflight(
        character_id: str,
        candidate_id: str,
        request: Request,
        namespace: str = Query(min_length=1, max_length=128),
        scope: str = Query(default="primary_formation", min_length=1, max_length=128),
    ) -> JSONResponse:
        payload = await exact_json(request, LabHeldGovernancePreflightRequest)
        resolved = scope_for(character_id, namespace)
        try:
            result = preflight_held_governance_decision(
                resolved.store_root,
                candidate_id=candidate_id,
                action="discard",
                expected_character_id=character_id,
                expected_namespace=namespace,
                expected_scope=scope,
                operation_id=payload.operation_id,
                reason=payload.reason,
            )
        except HeldGovernanceRuntimeError as error:
            raise failure(error) from None
        return JSONResponse(content=safe_projection(result), headers={"Cache-Control": "no-store"})

    @app.post(
        "/lab/api/characters/{character_id}/held/{candidate_id}/discard",
        response_model=None,
    )
    async def lab_held_discard(
        character_id: str,
        candidate_id: str,
        request: Request,
        namespace: str = Query(min_length=1, max_length=128),
        scope: str = Query(default="primary_formation", min_length=1, max_length=128),
    ) -> JSONResponse:
        payload = await exact_json(request, LabHeldGovernanceDecisionRequest)
        resolved = scope_for(character_id, namespace)
        try:
            result = apply_held_governance_decision(
                resolved.store_root,
                candidate_id=candidate_id,
                action="discard",
                expected_character_id=character_id,
                expected_namespace=namespace,
                expected_scope=scope,
                operation_id=payload.operation_id,
                reason=payload.reason,
                apply_token=payload.apply_token,
            )
        except HeldGovernanceRuntimeError as error:
            raise failure(error) from None
        return JSONResponse(content=safe_projection(result), headers={"Cache-Control": "no-store"})

    @app.get(
        "/lab/api/characters/{character_id}/held/{candidate_id}/history",
        response_model=None,
    )
    async def lab_held_history(
        character_id: str,
        candidate_id: str,
        request: Request,
        namespace: str = Query(min_length=1, max_length=128),
    ) -> JSONResponse:
        require_loopback_management(request)
        resolved = scope_for(character_id, namespace)
        try:
            result = list_held_governance_history(resolved.store_root, candidate_id=candidate_id)
        except HeldGovernanceRuntimeError as error:
            raise failure(error) from None
        return JSONResponse(content=safe_projection(result), headers={"Cache-Control": "no-store"})


__all__ = ["install_held_governance_routes"]
