"""Loopback-only SOUL Lab routes for Primary MEM Forget."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from relaylm.config import RelayLMConfig
from relaylm.relaymem_primary_forget import (
    PrimaryForgetError,
    apply_primary_memory_forget,
    list_primary_memory_forget_history,
    preflight_primary_memory_forget,
)
from relaylm.soul_lab_forget_projection_history import build_lab_forget_history_projection
from relaylm.soul_lab_management import is_loopback_host
from relaylm.soul_lab_memory_forget import (
    LabMemoryForgetApplyRequest,
    LabMemoryForgetPreflightRequest,
)
from relaylm.soul_lab_memory_forget_runtime import (
    ForgetRuntimeDependencies,
    execute_forget_apply,
    execute_forget_history,
    execute_forget_preflight,
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


def _runtime_dependencies(config: RelayLMConfig) -> ForgetRuntimeDependencies:
    """Resolve current route-module patch seams for one request."""
    return ForgetRuntimeDependencies(
        config=config,
        resolve_scope=resolve_lab_observation_scope,
        preflight=preflight_primary_memory_forget,
        apply=apply_primary_memory_forget,
        list_history=list_primary_memory_forget_history,
        build_history_projection=build_lab_forget_history_projection,
        error_type=PrimaryForgetError,
        preflight_model=LabMemoryForgetPreflightRequest,
        apply_model=LabMemoryForgetApplyRequest,
    )


def install_primary_memory_forget_routes(
    *,
    app: FastAPI,
    config: RelayLMConfig,
    configured_loopback: bool,
) -> None:
    """Install Primary MEM Forget routes without widening non-lab app authority."""

    @app.post(
        "/lab/api/characters/{character_id}/memory/{memory_id}/forget/preflight",
        response_model=None,
    )
    async def lab_memory_forget_preflight(
        character_id: str,
        memory_id: str,
        request: Request,
        namespace: str = Query(min_length=1, max_length=128),
    ) -> JSONResponse:
        _require_loopback_management(request, configured_loopback=configured_loopback)
        return await execute_forget_preflight(
            request, character_id, memory_id, namespace, _runtime_dependencies(config)
        )

    @app.post(
        "/lab/api/characters/{character_id}/memory/{memory_id}/forget",
        response_model=None,
    )
    async def lab_memory_forget_apply(
        character_id: str,
        memory_id: str,
        request: Request,
        namespace: str = Query(min_length=1, max_length=128),
    ) -> JSONResponse:
        _require_loopback_management(request, configured_loopback=configured_loopback)
        return await execute_forget_apply(
            request, character_id, memory_id, namespace, _runtime_dependencies(config)
        )

    @app.get(
        "/lab/api/characters/{character_id}/memory/{memory_id}/forget-history",
        response_model=None,
    )
    async def lab_memory_forget_history(
        character_id: str,
        memory_id: str,
        request: Request,
        namespace: str = Query(min_length=1, max_length=128),
    ) -> JSONResponse:
        _require_loopback_management(request, configured_loopback=configured_loopback)
        return execute_forget_history(
            character_id, memory_id, namespace, _runtime_dependencies(config)
        )
