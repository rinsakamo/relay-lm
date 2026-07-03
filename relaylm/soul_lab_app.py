"""RelayLM ASGI wrapper with loopback-only SOUL Lab management routes."""
from __future__ import annotations

import argparse
import json
import os
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from relaylm.app import create_app as create_core_app
from relaylm.config import RelayLMConfig, load_config
from relaylm.lab_held_governance_api import install_held_governance_routes
from relaylm.relaymem_primary_correction import (
    PrimaryCorrectionError,
    apply_primary_memory_correction,
    list_primary_memory_corrections,
    preflight_primary_memory_correction,
)
from relaylm.relaymem_primary_forget import (
    PrimaryForgetError,
    apply_primary_memory_forget,
    list_primary_memory_forget_history,
    preflight_primary_memory_forget,
)
from relaylm.soul_lab_forget_projection_history import (
    build_lab_active_recent_memory_projection,
    build_lab_forget_history_projection,
)
from relaylm.soul_lab_lifecycle_visibility_projection import (
    build_lab_lifecycle_visibility_projection,
)
from relaylm.soul_lab_management import (
    build_lab_characters_projection,
    build_lab_settings_projection,
    is_loopback_host,
)
from relaylm.soul_lab_memory_correction import (
    LabMemoryCorrectApplyRequest,
    LabMemoryCorrectPreflightRequest,
)
from relaylm.soul_lab_memory_forget import (
    LabMemoryForgetApplyRequest,
    LabMemoryForgetPreflightRequest,
)
from relaylm.soul_lab_memory_pin_routes import install_primary_memory_pin_routes
from relaylm.soul_lab_observation import (
    LabObservationResponseMiddleware,
    install_lab_observation_runtime_hook,
)
from relaylm.soul_lab_observation_projection import (
    build_lab_last_run_projection,
    build_lab_memory_held_projection,
    build_lab_memory_used_projection,
    resolve_lab_observation_scope,
)
from relaylm.soul_lab_used_memory_lifecycle_projection import (
    build_lab_memory_used_lifecycle_projection,
)

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


def create_app(config_path: str | None = None) -> FastAPI:
    install_lab_observation_runtime_hook()
    app = create_core_app(config_path)
    app.add_middleware(LabObservationResponseMiddleware)
    config: RelayLMConfig = app.state.relaylm_config
    configured_loopback = is_loopback_host(config.listen.host)

    def require_loopback_management(request: Request) -> None:
        peer_host = request.client.host if request.client is not None else ""
        if not configured_loopback or not is_loopback_host(peer_host):
            raise HTTPException(
                status_code=403,
                detail="lab_management_requires_loopback_access",
            )

    def observation_scope(character_id: str, namespace: str):
        scope = resolve_lab_observation_scope(
            config,
            character_id=character_id,
            namespace=namespace,
        )
        if not scope.known:
            raise HTTPException(status_code=404, detail="lab_character_not_found")
        return scope

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

    def forget_failure(error: PrimaryForgetError) -> HTTPException:
        code = error.code if error.code in _ERROR_STATUS else "store_unavailable"
        return HTTPException(status_code=_ERROR_STATUS[code], detail=code)

    def safe_forget_preflight_projection(result: dict[str, Any]) -> dict[str, Any]:
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
                "effects": {
                    key: bool(effects.get(key)) for key in sorted(_FORGET_EFFECT_KEYS)
                },
                "apply_token": result["apply_token"],
                "expires_at": result["expires_at"],
            }
        except (KeyError, TypeError, ValueError):
            raise HTTPException(status_code=503, detail="store_unavailable") from None

    def safe_forget_apply_projection(memory_id: str, result: Any) -> dict[str, Any]:
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

    install_held_governance_routes(
        app,
        require_loopback_management=require_loopback_management,
        observation_scope=correction_scope,
        exact_json=exact_json,
    )

    @app.get("/lab/api/characters", response_model=None)
    async def lab_characters(request: Request) -> JSONResponse:
        require_loopback_management(request)
        projection = build_lab_characters_projection(config)
        return JSONResponse(
            content=projection.model_dump(mode="json"),
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/lab/api/settings", response_model=None)
    async def lab_settings(request: Request) -> JSONResponse:
        require_loopback_management(request)
        projection = build_lab_settings_projection(config)
        return JSONResponse(
            content=projection.model_dump(mode="json"),
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/lab/api/characters/{character_id}/lab/last-run", response_model=None)
    async def lab_last_run(
        character_id: str,
        request: Request,
        namespace: str = Query(min_length=1, max_length=128),
    ) -> JSONResponse:
        require_loopback_management(request)
        projection = build_lab_last_run_projection(observation_scope(character_id, namespace))
        return JSONResponse(content=projection.model_dump(mode="json"), headers={"Cache-Control": "no-store"})

    @app.get("/lab/api/characters/{character_id}/memory/recent", response_model=None)
    async def lab_recent_memory(
        character_id: str,
        request: Request,
        namespace: str = Query(min_length=1, max_length=128),
        limit: int = Query(default=20, ge=1, le=50),
    ) -> JSONResponse:
        require_loopback_management(request)
        projection = build_lab_active_recent_memory_projection(observation_scope(character_id, namespace), limit=limit)
        return JSONResponse(content=projection.model_dump(mode="json"), headers={"Cache-Control": "no-store"})

    @app.get("/lab/api/characters/{character_id}/memory/held", response_model=None)
    async def lab_held_memory(
        character_id: str,
        request: Request,
        namespace: str = Query(min_length=1, max_length=128),
        limit: int = Query(default=20, ge=1, le=50),
    ) -> JSONResponse:
        require_loopback_management(request)
        projection = build_lab_memory_held_projection(observation_scope(character_id, namespace), limit=limit)
        return JSONResponse(content=projection.model_dump(mode="json"), headers={"Cache-Control": "no-store"})

    @app.get(
        "/lab/api/characters/{character_id}/lab/last-run/memory/used",
        response_model=None,
    )
    async def lab_used_memory(
        character_id: str,
        request: Request,
        namespace: str = Query(min_length=1, max_length=128),
    ) -> JSONResponse:
        require_loopback_management(request)
        projection = build_lab_memory_used_projection(observation_scope(character_id, namespace))
        return JSONResponse(content=projection.model_dump(mode="json"), headers={"Cache-Control": "no-store"})

    @app.get(
        "/lab/api/characters/{character_id}/lab/last-run/memory/used-lifecycle",
        response_model=None,
    )
    async def lab_used_memory_lifecycle(
        character_id: str,
        request: Request,
        namespace: str = Query(min_length=1, max_length=128),
    ) -> JSONResponse:
        require_loopback_management(request)
        projection = build_lab_memory_used_lifecycle_projection(observation_scope(character_id, namespace))
        return JSONResponse(content=projection.model_dump(mode="json"), headers={"Cache-Control": "no-store"})

    @app.get(
        "/lab/api/characters/{character_id}/lab/lifecycle-visibility",
        response_model=None,
    )
    async def lab_lifecycle_visibility(
        character_id: str,
        request: Request,
        namespace: str = Query(min_length=1, max_length=128),
    ) -> JSONResponse:
        require_loopback_management(request)
        projection = build_lab_lifecycle_visibility_projection(
            observation_scope(character_id, namespace),
            config=config,
        )
        return JSONResponse(content=projection.model_dump(mode="json"), headers={"Cache-Control": "no-store"})

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
        payload = await exact_json(request, LabMemoryForgetPreflightRequest)
        scope = correction_scope(character_id, namespace)
        try:
            result = preflight_primary_memory_forget(
                store_root=scope.store_root,
                character_id=character_id,
                namespace=namespace,
                memory_id=memory_id,
                expected_revision=payload.expected_revision,
                expected_lifecycle_state=payload.expected_lifecycle_state,
                reason=payload.reason,
                operation_id=payload.operation_id,
            )
        except PrimaryForgetError as error:
            raise forget_failure(error) from None
        projection = safe_forget_preflight_projection(result)
        return JSONResponse(content=projection, headers={"Cache-Control": "no-store"})

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
        payload = await exact_json(request, LabMemoryForgetApplyRequest)
        scope = correction_scope(character_id, namespace)
        try:
            result = apply_primary_memory_forget(
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
        except PrimaryForgetError as error:
            raise forget_failure(error) from None
        projection = safe_forget_apply_projection(memory_id, result)
        return JSONResponse(content=projection, headers={"Cache-Control": "no-store"})

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
        require_loopback_management(request)
        scope = correction_scope(character_id, namespace)
        try:
            result = list_primary_memory_forget_history(
                store_root=scope.store_root,
                namespace=namespace,
                memory_id=memory_id,
            )
            projection = build_lab_forget_history_projection(
                store_root=scope.store_root,
                namespace=namespace,
                memory_id=memory_id,
                base=result,
            )
        except PrimaryForgetError as error:
            raise forget_failure(error) from None
        return JSONResponse(content=projection, headers={"Cache-Control": "no-store"})

    install_primary_memory_pin_routes(
        app=app,
        config=config,
        configured_loopback=configured_loopback,
    )

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run RelayLM with SOUL Lab management API")
    parser.add_argument("--config", default=None, help="Path to config.yaml")
    args = parser.parse_args()

    if args.config:
        os.environ["RELAYLM_CONFIG"] = args.config

    config = load_config(args.config)
    uvicorn.run(
        "relaylm.soul_lab_app:create_app",
        factory=True,
        host=config.listen.host,
        port=config.listen.port,
    )


if __name__ == "__main__":
    main()
