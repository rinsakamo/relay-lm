"""Loopback-only CW-A5 character template and creation API routes."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from relaylm.character_creation import (
    TemplateValidationResult,
    commit_character_from_template,
    get_character_template,
    list_character_templates,
    stage_quick_character,
    validate_template_path,
)
from relaylm.config import RelayLMConfig


class LabCharacterTemplateValidateRequest(BaseModel):
    template_id: str | None = Field(default=None, min_length=1, max_length=128)
    import_path: str | None = Field(default=None, min_length=1, max_length=512)


class LabCharacterCreateFromTemplateRequest(BaseModel):
    template_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=128)
    tone: str = Field(default="friendly", min_length=1, max_length=64)
    intended_use: str = Field(default="casual chat", min_length=1, max_length=128)
    showcase_mode: Literal["starter", "as_is"] = "starter"
    approval: bool = False


class LabCharacterImportTemplateRequest(BaseModel):
    import_path: str = Field(min_length=1, max_length=512)


def install_character_creation_routes(
    app: FastAPI,
    *,
    config: RelayLMConfig,
    require_loopback_management,
    exact_json,
) -> None:
    @app.get("/lab/api/character-templates", response_model=None)
    async def lab_character_templates(request: Request) -> JSONResponse:
        require_loopback_management(request)
        return JSONResponse(content=list_character_templates(), headers={"Cache-Control": "no-store"})

    @app.post("/lab/api/character-templates/validate", response_model=None)
    async def lab_character_template_validate(request: Request) -> JSONResponse:
        payload = await exact_json(request, LabCharacterTemplateValidateRequest)
        if payload.template_id:
            projection = _validate_bundled_template(payload.template_id)
            return JSONResponse(content=projection.to_public_dict(), headers={"Cache-Control": "no-store"})
        if payload.import_path:
            projection = _validate_local_import(payload.import_path)
            return JSONResponse(content=projection.to_public_dict(), headers={"Cache-Control": "no-store"})
        projection = TemplateValidationResult(
            status="invalid",
            is_valid=False,
            reason_ids=("template_id_or_import_path_required",),
        )
        return JSONResponse(content=projection.to_public_dict(), headers={"Cache-Control": "no-store"})

    @app.post("/lab/api/characters/create-from-template", response_model=None)
    async def lab_character_create_from_template(request: Request) -> JSONResponse:
        payload = await exact_json(request, LabCharacterCreateFromTemplateRequest)
        try:
            result = commit_character_from_template(
                characters_root=_characters_root(config),
                template_id=payload.template_id,
                name=payload.name,
                tone=payload.tone,
                intended_use=payload.intended_use,
                approval=payload.approval,
                showcase_mode=payload.showcase_mode,
            )
        except ValueError:
            result = TemplateValidationResult(
                status="invalid",
                is_valid=False,
                reason_ids=("template_not_found",),
            )
            return JSONResponse(content=result.to_public_dict(), status_code=404, headers={"Cache-Control": "no-store"})
        return JSONResponse(content=result.to_public_dict(), headers={"Cache-Control": "no-store"})

    @app.post("/lab/api/characters/import-template", response_model=None)
    async def lab_character_import_template(request: Request) -> JSONResponse:
        payload = await exact_json(request, LabCharacterImportTemplateRequest)
        projection = _validate_local_import(payload.import_path)
        content = projection.to_public_dict()
        content["workspace_commit_supported"] = False
        content["reason_ids"] = tuple(content["reason_ids"]) + ("external_import_commit_pending",)
        return JSONResponse(content=content, headers={"Cache-Control": "no-store"})


def _validate_bundled_template(template_id: str) -> TemplateValidationResult:
    try:
        record = get_character_template(template_id)
        candidate = stage_quick_character(
            template_id=template_id,
            name="Preview Character",
            tone=(record.tone_options[0] if record.tone_options else "friendly"),
            intended_use=(record.intended_uses[0] if record.intended_uses else "casual chat"),
            showcase_mode="as_is" if record.showcase else "starter",
        )
    except ValueError:
        return TemplateValidationResult(
            status="invalid",
            is_valid=False,
            reason_ids=("template_not_found",),
        )
    return TemplateValidationResult(
        status="valid" if candidate.validation.is_valid else "invalid",
        is_valid=bool(candidate.validation.is_valid),
        reason_ids=tuple(candidate.validation.reason_ids),
        checked_entry_count=len(candidate.source_files),
        rejected_entry_count=0,
        relaylm_onboarding_memory_included=candidate.relaylm_onboarding_memory_included,
    )


def _validate_local_import(import_path: str) -> TemplateValidationResult:
    if Path(import_path).is_absolute():
        return TemplateValidationResult(
            status="invalid",
            is_valid=False,
            reason_ids=("absolute_import_path_rejected",),
        )
    import_root_value = os.environ.get("RELAYLM_CHARACTER_TEMPLATE_IMPORT_ROOT")
    if not import_root_value:
        return TemplateValidationResult(
            status="invalid",
            is_valid=False,
            reason_ids=("local_import_disabled",),
        )
    import_root = Path(import_root_value).resolve()
    candidate = (import_root / import_path).resolve()
    if not _is_relative_to(candidate, import_root):
        return TemplateValidationResult(
            status="invalid",
            is_valid=False,
            reason_ids=("path_traversal_rejected",),
        )
    return validate_template_path(candidate)


def _characters_root(config: RelayLMConfig) -> Path:
    override = os.environ.get("RELAYLM_CHARACTER_WORKSPACE_ROOT")
    if override:
        return Path(override)
    if config.memory.root_path:
        return Path(config.memory.root_path) / "characters"
    return Path("characters")


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
