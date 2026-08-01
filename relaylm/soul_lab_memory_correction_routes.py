"""Loopback-only SOUL Lab routes for Primary MEM Correct."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

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
from relaylm.soul_lab_memory_correction_runtime import (
    CorrectionRuntimeDependencies,
    execute_correction_apply,
    execute_correction_history,
    execute_correction_preflight,
)
from relaylm.soul_lab_observation_projection import resolve_lab_observation_scope


def _require_loopback_management(
    request: Request, *, configured_loopback: bool
) -> None:
    peer_host = request.client.host if request.client is not None else ""
    if not configured_loopback or not is_loopback_host(peer_host):
        raise HTTPException(
            status_code=403,
            detail="lab_management_requires_loopback_access",
        )


def _runtime_dependencies(config: RelayLMConfig) -> CorrectionRuntimeDependencies:
    """Resolve current route-module patch seams for one request."""
    return CorrectionRuntimeDependencies(
        config=config,
        resolve_scope=resolve_lab_observation_scope,
        preflight=preflight_primary_memory_correction,
        apply=apply_primary_memory_correction,
        list_history=list_primary_memory_corrections,
        error_type=PrimaryCorrectionError,
        preflight_model=LabMemoryCorrectPreflightRequest,
        apply_model=LabMemoryCorrectApplyRequest,
    )


def install_primary_memory_correction_routes(
    *,
    app: FastAPI,
    config: RelayLMConfig,
    configured_loopback: bool,
) -> None:
    """Install Primary MEM Correct routes without widening non-lab app authority."""

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
        _require_loopback_management(request, configured_loopback=configured_loopback)
        return await execute_correction_preflight(
            request, character_id, memory_id, namespace, _runtime_dependencies(config)
        )

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
        _require_loopback_management(request, configured_loopback=configured_loopback)
        return await execute_correction_apply(
            request, character_id, memory_id, namespace, _runtime_dependencies(config)
        )

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
        _require_loopback_management(request, configured_loopback=configured_loopback)
        return execute_correction_history(
            character_id, memory_id, namespace, _runtime_dependencies(config)
        )
