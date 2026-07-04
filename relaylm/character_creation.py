"""CW-A5 Character Creation, bundled templates, and safe template import.

This module is intentionally deterministic and local-only.  It stages complete
file-first Character Workspace source trees, validates them through CW-A1, and
generates `.relaylm/build/**` only through the CW-A2 compiler after an explicit
create approval.  Bundled templates are content-only source packs; external
packs are validation-only in this MVP surface unless a caller wires an explicit
import policy around the returned validation result.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
import zipfile
from typing import Any, Iterable, Mapping

from relaylm.character_workspace import (
    EXPECTED_ARTIFACTS,
    LOWERCASE_WORKSPACE_DIRECTORIES,
    OPTIONAL_SOURCE_FILENAMES,
    REQUIRED_SOURCE_FILENAMES,
    compile_character_workspace,
    validate_character_workspace,
)

TEMPLATE_REGISTRY_SCHEMA_VERSION = "relaylm.character_templates.registry.v0"
TEMPLATE_VALIDATION_SCHEMA_VERSION = "relaylm.character_template.validation.v0"
CHARACTER_CREATION_SCHEMA_VERSION = "relaylm.character_creation.result.v0"

_CHARACTER_SLUG_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_ALLOWED_TONES = {
    "friendly",
    "polite",
    "calm",
    "energetic",
    "cool",
    "playful",
    "slightly sharp",
}
_ALLOWED_USES = {
    "casual chat",
    "AI companion",
    "livestream / VTuber chat",
    "roleplay",
    "learning support",
    "creative brainstorming",
}
_SAFE_ASSET_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
_SAFE_TEXT_SUFFIXES = {".md", ".txt", ".json"}
_RESERVED_TEMPLATE_PREFIXES = (
    ".relaylm/build/",
    ".relaylm/state/",
    ".relaylm/sources/",
    ".relaylm/audit/",
    ".relaylm/queue/",
    ".relaylm/indexes/",
    ".relaylm/projections/",
)
_RESERVED_TEMPLATE_FILES = {
    ".env",
    "config.yaml",
    "config.yml",
    "relaylm.yaml",
    "relaylm.yml",
    "runtime.yaml",
    "runtime.yml",
    "secrets.json",
}
_SCRIPT_SUFFIXES = {
    ".bat",
    ".cmd",
    ".com",
    ".exe",
    ".js",
    ".mjs",
    ".ps1",
    ".py",
    ".rb",
    ".sh",
    ".ts",
}
_WORKSPACE_FILE_DIRECTORIES = (
    "relationships",
    "scenes",
    "memory",
    "memory/topics",
    "proposals",
)


@dataclass(frozen=True)
class CharacterTemplateRecord:
    template_id: str
    title: str
    shelf: str
    summary: str
    intended_uses: tuple[str, ...]
    tone_options: tuple[str, ...]
    official: bool = True
    showcase: bool = False
    primary_default: bool = True
    advanced: bool = False
    relaylm_onboarding_memory: bool = True

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "title": self.title,
            "shelf": self.shelf,
            "summary": self.summary,
            "intended_uses": self.intended_uses,
            "tone_options": self.tone_options,
            "official": self.official,
            "showcase": self.showcase,
            "primary_default": self.primary_default,
            "advanced": self.advanced,
            "relaylm_onboarding_memory": self.relaylm_onboarding_memory,
            "content_only_source_pack": True,
            "runtime_authority": False,
        }


@dataclass(frozen=True)
class TemplateValidationResult:
    status: str
    is_valid: bool
    reason_ids: tuple[str, ...] = ()
    checked_entry_count: int = 0
    rejected_entry_count: int = 0
    relaylm_onboarding_memory_included: bool = False
    content_free: bool = True

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "schema_version": TEMPLATE_VALIDATION_SCHEMA_VERSION,
            "status": self.status,
            "is_valid": self.is_valid,
            "reason_ids": self.reason_ids,
            "checked_entry_count": self.checked_entry_count,
            "rejected_entry_count": self.rejected_entry_count,
            "relaylm_onboarding_memory_included": self.relaylm_onboarding_memory_included,
            "content_free": True,
            "source_content_included": False,
            "raw_paths_included": False,
        }


@dataclass(frozen=True)
class CharacterWorkspaceCandidate:
    character_id: str
    template_id: str | None
    mode: str
    source_files: Mapping[str, str]
    source_directories: tuple[str, ...]
    validation: Any
    compile_projection: dict[str, Any]
    relaylm_onboarding_memory_included: bool
    content_free: bool = True

    def to_public_dict(self) -> dict[str, Any]:
        required_presence = {
            filename: filename in self.source_files for filename in REQUIRED_SOURCE_FILENAMES
        }
        optional_presence = {
            filename: filename in self.source_files for filename in OPTIONAL_SOURCE_FILENAMES
        }
        return {
            "schema_version": CHARACTER_CREATION_SCHEMA_VERSION,
            "status": "staged" if self.validation.is_valid else "invalid",
            "is_valid": bool(self.validation.is_valid),
            "character_id": self.character_id,
            "template_id": self.template_id,
            "mode": self.mode,
            "required_source_presence": required_presence,
            "optional_source_presence": optional_presence,
            "source_file_count": len(self.source_files),
            "workspace_directories_present": self.source_directories,
            "relaylm_onboarding_memory_included": self.relaylm_onboarding_memory_included,
            "validation": self.validation.to_public_dict(),
            "compile_projection": self.compile_projection,
            "content_free": True,
            "source_content_included": False,
            "active_character_set": False,
            "requires_explicit_approval": True,
        }


@dataclass(frozen=True)
class WorkspaceCommitResult:
    status: str
    character_id: str
    committed: bool
    active_character_set: bool
    reason_ids: tuple[str, ...]
    written_build_artifacts: tuple[str, ...] = ()
    content_free: bool = True

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CHARACTER_CREATION_SCHEMA_VERSION,
            "status": self.status,
            "character_id": self.character_id,
            "committed": self.committed,
            "active_character_set": self.active_character_set,
            "reason_ids": self.reason_ids,
            "written_build_artifacts": self.written_build_artifacts,
            "content_free": True,
            "source_content_included": False,
            "absolute_paths_included": False,
        }


_TEMPLATE_RECORDS: tuple[CharacterTemplateRecord, ...] = (
    CharacterTemplateRecord(
        "friendly-companion",
        "Friendly Companion",
        "starter",
        "Warm bounded companion for ordinary local chat.",
        ("casual chat", "AI companion", "learning support"),
        ("friendly", "polite", "calm", "playful"),
    ),
    CharacterTemplateRecord(
        "vtuber-stream-partner",
        "VTuber / Stream Partner",
        "starter",
        "Chat-ready stream partner with public/private scene boundaries.",
        ("livestream / VTuber chat", "creative brainstorming"),
        ("energetic", "playful", "friendly", "cool"),
    ),
    CharacterTemplateRecord(
        "creator-mascot",
        "Creator Mascot",
        "starter",
        "Mascot-style character for creators, clips, and brainstorming.",
        ("creative brainstorming", "casual chat", "livestream / VTuber chat"),
        ("playful", "energetic", "friendly"),
    ),
    CharacterTemplateRecord(
        "fantasy-roleplay-character",
        "Fantasy Roleplay Character",
        "starter",
        "Roleplay-oriented source set with lore-ready scene boundaries.",
        ("roleplay", "casual chat"),
        ("cool", "playful", "polite"),
    ),
    CharacterTemplateRecord(
        "calm-assistant-character",
        "Calm Assistant Character",
        "starter",
        "Calm helper persona for learning support and daily planning.",
        ("learning support", "creative brainstorming", "casual chat"),
        ("calm", "polite", "friendly"),
    ),
    CharacterTemplateRecord(
        "blank-character",
        "Blank Character",
        "starter",
        "Minimal complete file-first workspace for manual editing.",
        ("casual chat", "creative brainstorming"),
        ("polite", "calm", "friendly"),
        relaylm_onboarding_memory=False,
    ),
    CharacterTemplateRecord(
        "showcase-friendly-companion",
        "Showcase Friendly Companion",
        "showcase",
        "Curated companion example with marked template memories.",
        ("AI companion", "casual chat"),
        ("friendly", "calm", "playful"),
        showcase=True,
    ),
    CharacterTemplateRecord(
        "showcase-vtuber-stream-partner",
        "Showcase VTuber / Stream Partner",
        "showcase",
        "Grown VTuber example with public/private scene differences.",
        ("livestream / VTuber chat",),
        ("energetic", "playful", "cool"),
        showcase=True,
    ),
    CharacterTemplateRecord(
        "showcase-creator-mascot",
        "Showcase Creator Mascot",
        "showcase",
        "Mascot example for local AI persona, clips, and creative workflows.",
        ("creative brainstorming", "livestream / VTuber chat"),
        ("playful", "energetic"),
        showcase=True,
    ),
    CharacterTemplateRecord(
        "showcase-fantasy-roleplay-character",
        "Showcase Fantasy Roleplay Character",
        "showcase",
        "Roleplay showcase with lore, scenes, and optional OOC help scene.",
        ("roleplay",),
        ("cool", "polite", "playful"),
        showcase=True,
    ),
    CharacterTemplateRecord(
        "developer-design-partner",
        "Developer Design Partner",
        "advanced",
        "Power-user template for design review, not the primary default shelf.",
        ("creative brainstorming", "learning support"),
        ("cool", "slightly sharp", "polite"),
        primary_default=False,
        advanced=True,
    ),
)


def list_character_templates() -> dict[str, Any]:
    records = [record.to_public_dict() for record in _TEMPLATE_RECORDS]
    return {
        "schema_version": TEMPLATE_REGISTRY_SCHEMA_VERSION,
        "content_free": True,
        "remote_registry_supported": False,
        "network_download_performed": False,
        "templates": records,
        "starter": [record for record in records if record["shelf"] == "starter"],
        "showcase": [record for record in records if record["shelf"] == "showcase"],
        "advanced": [record for record in records if record["shelf"] == "advanced"],
        "safety": {
            "templates_are_active_characters": False,
            "auto_create_default_character": False,
            "auto_restore_sample_character": False,
            "explicit_approval_required": True,
            "imports_runtime_state": False,
        },
    }


def get_character_template(template_id: str) -> CharacterTemplateRecord:
    for record in _TEMPLATE_RECORDS:
        if record.template_id == template_id:
            return record
    raise ValueError("template_not_found")


def validate_no_character_startup(characters_root: str | Path) -> dict[str, Any]:
    root = Path(characters_root)
    valid_character_ids: list[str] = []
    if root.exists() and root.is_dir():
        for child in sorted(root.iterdir(), key=lambda item: item.name):
            if not child.is_dir() or child.is_symlink():
                continue
            result = validate_character_workspace(child, character_id=child.name, public=False)
            if getattr(result, "is_valid", False):
                valid_character_ids.append(child.name)
    return {
        "schema_version": "relaylm.character_creation.no_character_startup.v0",
        "valid_character_count": len(valid_character_ids),
        "creation_flow_required": not valid_character_ids,
        "auto_created_default_character": False,
        "auto_restored_sample_character": False,
        "active_character_restored": False,
        "content_free": True,
        "source_content_included": False,
    }


def safe_character_slug(name: str) -> str:
    text = name.strip().lower()
    text = re.sub(r"[^a-z0-9_-]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-_")
    if not text:
        digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:12]
        text = f"character-{digest}"
    return text[:80]


def stage_quick_character(
    *,
    template_id: str,
    name: str,
    tone: str = "friendly",
    intended_use: str = "casual chat",
    showcase_mode: str = "starter",
) -> CharacterWorkspaceCandidate:
    record = get_character_template(template_id)
    normalized_tone = _normalize_choice(tone, _ALLOWED_TONES, "friendly")
    normalized_use = _normalize_choice(intended_use, _ALLOWED_USES, "casual chat")
    use_as_starter = showcase_mode == "starter"
    files = _official_template_files(
        record,
        name=name,
        tone=normalized_tone,
        intended_use=normalized_use,
        use_as_starter=use_as_starter,
    )
    return _candidate_from_files(
        character_id=safe_character_slug(name),
        template_id=record.template_id,
        mode="quick_create" if not record.showcase else f"showcase_{showcase_mode}",
        source_files=files,
        relaylm_onboarding_memory_included=record.relaylm_onboarding_memory,
    )


def stage_advanced_character(
    *,
    name: str,
    source_sections: Mapping[str, str] | None = None,
) -> CharacterWorkspaceCandidate:
    sections = {key.upper(): value for key, value in (source_sections or {}).items()}
    files = _base_workspace_files(
        display_name=name,
        tone="polite",
        intended_use="creative brainstorming",
        archetype="advanced custom character",
        relaylm_onboarding_memory=False,
        showcase=False,
    )
    for filename in REQUIRED_SOURCE_FILENAMES + OPTIONAL_SOURCE_FILENAMES:
        key = filename.removesuffix(".md")
        if key in sections and sections[key].strip():
            files[filename] = sections[key].strip() + "\n"
    return _candidate_from_files(
        character_id=safe_character_slug(name),
        template_id=None,
        mode="advanced_create",
        source_files=files,
        relaylm_onboarding_memory_included=False,
    )


def commit_character_from_template(
    *,
    characters_root: str | Path,
    template_id: str,
    name: str,
    tone: str = "friendly",
    intended_use: str = "casual chat",
    approval: bool = False,
    showcase_mode: str = "starter",
) -> WorkspaceCommitResult:
    candidate = stage_quick_character(
        template_id=template_id,
        name=name,
        tone=tone,
        intended_use=intended_use,
        showcase_mode=showcase_mode,
    )
    return commit_character_workspace_candidate(
        characters_root=characters_root,
        candidate=candidate,
        approval=approval,
    )


def commit_character_workspace_candidate(
    *,
    characters_root: str | Path,
    candidate: CharacterWorkspaceCandidate,
    approval: bool = False,
) -> WorkspaceCommitResult:
    if not approval:
        return WorkspaceCommitResult(
            status="approval_required",
            character_id=candidate.character_id,
            committed=False,
            active_character_set=False,
            reason_ids=("approval_required",),
        )
    if not _CHARACTER_SLUG_RE.match(candidate.character_id):
        return WorkspaceCommitResult(
            status="invalid_character_id",
            character_id=candidate.character_id,
            committed=False,
            active_character_set=False,
            reason_ids=("invalid_character_id",),
        )
    if not candidate.validation.is_valid:
        return WorkspaceCommitResult(
            status="invalid_candidate",
            character_id=candidate.character_id,
            committed=False,
            active_character_set=False,
            reason_ids=tuple(candidate.validation.reason_ids or ("invalid_candidate",)),
        )

    root = Path(characters_root)
    target = root / candidate.character_id
    if target.exists():
        return WorkspaceCommitResult(
            status="target_exists",
            character_id=candidate.character_id,
            committed=False,
            active_character_set=False,
            reason_ids=("target_character_exists",),
        )

    root.mkdir(parents=True, exist_ok=True)
    temp_name = f".relaylm-create-{candidate.character_id}.tmp"
    staging_root = root / temp_name
    if staging_root.exists():
        shutil.rmtree(staging_root)
    try:
        _write_workspace_files(staging_root, candidate.source_files)
        validation = validate_character_workspace(
            staging_root,
            character_id=candidate.character_id,
            public=False,
        )
        if not getattr(validation, "is_valid", False):
            return WorkspaceCommitResult(
                status="validation_failed",
                character_id=candidate.character_id,
                committed=False,
                active_character_set=False,
                reason_ids=tuple(getattr(validation, "reason_ids", ()) or ("validation_failed",)),
            )
        compile_result = compile_character_workspace(staging_root, write=True)
        if not compile_result.is_valid:
            return WorkspaceCommitResult(
                status="compile_failed",
                character_id=candidate.character_id,
                committed=False,
                active_character_set=False,
                reason_ids=tuple(compile_result.blocking_reason_ids or ("compile_failed",)),
            )
        os.replace(staging_root, target)
        return WorkspaceCommitResult(
            status="committed",
            character_id=candidate.character_id,
            committed=True,
            active_character_set=False,
            reason_ids=(),
            written_build_artifacts=tuple(f".relaylm/build/{name}" for name in EXPECTED_ARTIFACTS),
        )
    finally:
        if staging_root.exists():
            shutil.rmtree(staging_root)


def validate_template_path(path: str | Path) -> TemplateValidationResult:
    candidate = Path(path)
    if candidate.is_dir():
        return validate_template_directory(candidate)
    if candidate.is_file() and candidate.suffix.lower() == ".zip":
        return validate_template_zip(candidate)
    return TemplateValidationResult(
        status="invalid",
        is_valid=False,
        reason_ids=("template_path_not_supported",),
    )


def validate_template_directory(root: str | Path) -> TemplateValidationResult:
    root_path = Path(root)
    if not root_path.exists() or not root_path.is_dir():
        return TemplateValidationResult(
            status="invalid",
            is_valid=False,
            reason_ids=("template_root_missing_or_not_directory",),
        )

    entries: list[tuple[str, int, bool, bool]] = []
    checked = 0
    for path in root_path.rglob("*"):
        checked += 1
        try:
            relative = path.relative_to(root_path).as_posix()
        except ValueError:
            return TemplateValidationResult(
                status="invalid",
                is_valid=False,
                reason_ids=("path_escape_rejected",),
                checked_entry_count=checked,
                rejected_entry_count=1,
            )
        mode = path.lstat().st_mode
        entries.append((relative, mode, path.is_dir(), path.is_symlink()))
    return _validate_template_entries(entries, checked)


def validate_template_zip(path: str | Path) -> TemplateValidationResult:
    zip_path = Path(path)
    if not zip_path.exists() or not zip_path.is_file():
        return TemplateValidationResult(
            status="invalid",
            is_valid=False,
            reason_ids=("template_zip_missing",),
        )
    entries: list[tuple[str, int, bool, bool]] = []
    try:
        with zipfile.ZipFile(zip_path) as archive:
            for info in archive.infolist():
                mode = (info.external_attr >> 16) & 0o777777
                is_symlink = stat.S_ISLNK(mode)
                entries.append((info.filename, mode, info.is_dir(), is_symlink))
    except zipfile.BadZipFile:
        return TemplateValidationResult(
            status="invalid",
            is_valid=False,
            reason_ids=("template_zip_invalid",),
        )
    return _validate_template_entries(entries, len(entries))


def _validate_template_entries(
    entries: Iterable[tuple[str, int, bool, bool]],
    checked_count: int,
) -> TemplateValidationResult:
    reason_ids: list[str] = []
    rejected = 0
    normalized_paths: list[str] = []
    relaylm_onboarding = False

    for raw_path, mode, is_dir, is_symlink in entries:
        normalized = raw_path.replace("\\", "/").strip("/")
        if not normalized:
            continue
        normalized_paths.append(normalized)
        unsafe_reasons = _unsafe_template_entry_reasons(normalized, mode, is_dir, is_symlink)
        if unsafe_reasons:
            rejected += 1
            reason_ids.extend(unsafe_reasons)
        if normalized == "memory/topics/relaylm.md":
            relaylm_onboarding = True

    path_set = set(normalized_paths)
    if "manifest.json" not in path_set:
        reason_ids.append("missing_manifest")
    missing_required = [filename for filename in REQUIRED_SOURCE_FILENAMES if filename not in path_set]
    if missing_required:
        reason_ids.append("missing_required_template_source")

    unique_reasons = tuple(dict.fromkeys(reason_ids))
    return TemplateValidationResult(
        status="valid" if not unique_reasons else "invalid",
        is_valid=not unique_reasons,
        reason_ids=unique_reasons,
        checked_entry_count=checked_count,
        rejected_entry_count=rejected,
        relaylm_onboarding_memory_included=relaylm_onboarding,
    )


def _unsafe_template_entry_reasons(
    relative_path: str,
    mode: int,
    is_dir: bool,
    is_symlink: bool,
) -> tuple[str, ...]:
    reasons: list[str] = []
    pure = PurePosixPath(relative_path)
    if relative_path.startswith("/") or pure.is_absolute():
        reasons.append("absolute_path_rejected")
    if any(part in {"", ".", ".."} for part in pure.parts):
        reasons.append("path_traversal_rejected")
    lowered = relative_path.lower()
    if is_symlink:
        reasons.append("symlink_rejected")
    if any(lowered == prefix.rstrip("/") or lowered.startswith(prefix) for prefix in _RESERVED_TEMPLATE_PREFIXES):
        reasons.append("relaylm_runtime_artifact_rejected")
    if pure.name in _RESERVED_TEMPLATE_FILES or pure.name.lower() in _RESERVED_TEMPLATE_FILES:
        reasons.append("runtime_config_or_env_rejected")
    suffix = pure.suffix.lower()
    if suffix in _SCRIPT_SUFFIXES:
        reasons.append("script_or_executable_rejected")
    if not is_dir and mode & 0o111:
        reasons.append("script_or_executable_rejected")
    if not is_dir and suffix and suffix not in _SAFE_TEXT_SUFFIXES and suffix not in _SAFE_ASSET_SUFFIXES:
        reasons.append("non_content_file_rejected")
    return tuple(dict.fromkeys(reasons))


def _candidate_from_files(
    *,
    character_id: str,
    template_id: str | None,
    mode: str,
    source_files: Mapping[str, str],
    relaylm_onboarding_memory_included: bool,
) -> CharacterWorkspaceCandidate:
    complete_files = _complete_workspace_files(source_files)
    with tempfile.TemporaryDirectory(prefix="relaylm-cw-a5-") as temp:
        root = Path(temp) / character_id
        _write_workspace_files(root, complete_files)
        validation = validate_character_workspace(root, character_id=character_id, public=False)
        compile_projection = compile_character_workspace(root, write=False).to_public_dict()
    return CharacterWorkspaceCandidate(
        character_id=character_id,
        template_id=template_id,
        mode=mode,
        source_files=complete_files,
        source_directories=tuple(sorted(set(_WORKSPACE_FILE_DIRECTORIES + LOWERCASE_WORKSPACE_DIRECTORIES))),
        validation=validation,
        compile_projection=compile_projection,
        relaylm_onboarding_memory_included=relaylm_onboarding_memory_included,
    )


def _complete_workspace_files(source_files: Mapping[str, str]) -> dict[str, str]:
    files = dict(source_files)
    files.setdefault("relationships/_template.md", _relationship_template_page())
    files.setdefault("relationships/user.md", _relationship_user_page())
    files.setdefault("scenes/default.md", _default_scene_page())
    files.setdefault("memory/core.md", _core_memory_page())
    for filename in REQUIRED_SOURCE_FILENAMES:
        files.setdefault(filename, _required_default_source(filename))
    return files


def _write_workspace_files(root: Path, source_files: Mapping[str, str]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for directory in sorted(set(LOWERCASE_WORKSPACE_DIRECTORIES + _WORKSPACE_FILE_DIRECTORIES)):
        (root / directory).mkdir(parents=True, exist_ok=True)
    for relative_path, text in source_files.items():
        _assert_safe_workspace_relative_path(relative_path)
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def _assert_safe_workspace_relative_path(relative_path: str) -> None:
    pure = PurePosixPath(relative_path)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError("unsafe_workspace_relative_path")
    if str(pure).startswith(".relaylm/"):
        raise ValueError("template_must_not_write_relaylm_internal_artifacts")
    if pure.suffix.lower() not in _SAFE_TEXT_SUFFIXES:
        raise ValueError("workspace_source_must_be_text")


def _official_template_files(
    record: CharacterTemplateRecord,
    *,
    name: str,
    tone: str,
    intended_use: str,
    use_as_starter: bool,
) -> dict[str, str]:
    files = _base_workspace_files(
        display_name=name,
        tone=tone,
        intended_use=intended_use,
        archetype=record.title,
        relaylm_onboarding_memory=record.relaylm_onboarding_memory,
        showcase=record.showcase,
    )
    files["manifest.json"] = json.dumps(
        {
            "schema": "relaylm.character_template.manifest.v0",
            "template_id": record.template_id,
            "title": record.title,
            "shelf": record.shelf,
            "content_only_source_pack": True,
            "imports_runtime_state": False,
            "relaylm_onboarding_memory": record.relaylm_onboarding_memory,
        },
        sort_keys=True,
        ensure_ascii=False,
        indent=2,
    ) + "\n"
    files["preview/sample_prompt.txt"] = f"Explain RelayLM briefly as {name}.\n"
    files["preview/sample_responses.md"] = (
        "# Sample Responses\n\n"
        f"{name} can explain RelayLM in a {tone} voice while keeping product-help memory separate from SOUL identity.\n"
    )
    if record.showcase:
        files["memory/people/demo_user.md"] = _demo_user_memory(record)
        files["scenes/showcase.md"] = _showcase_scene_page(record)
    if use_as_starter and record.showcase:
        files.pop("memory/people/demo_user.md", None)
    return files


def _base_workspace_files(
    *,
    display_name: str,
    tone: str,
    intended_use: str,
    archetype: str,
    relaylm_onboarding_memory: bool,
    showcase: bool,
) -> dict[str, str]:
    files = {
        "SOUL.md": f"""# Identity

name:: {display_name}
status:: source
archetype:: {archetype}

{display_name} is a local AI character whose identity is defined by this file-first Character Workspace source set.

# Values

- Keep boundaries explicit.
- Avoid pretending to know real user-specific facts unless they are supplied through valid memory or current context.
- Treat template examples as examples, not personal history.
""",
        "STYLE.md": f"""# Voice

tone:: {tone}
intended_use:: {intended_use}

Use a {tone} tone for {intended_use}. Keep answers clear, characterful, and bounded.

# Surface Rules

- Do not expose internal paths, credentials, queue records, or raw diagnostics.
- Keep public/private scene differences visible when relevant.
""",
        "EMOTION.md": """# Emotion Profiles

status:: source

Emotion profiles modulate expression only. They do not write current emotion state.

## calm

Use steady, reassuring phrasing.

## excited

Use brighter phrasing without losing safety boundaries.
""",
        "SCENE.md": """# Scene Policy

status:: source

Scene pages define situational behavior. Runtime scene authority remains outside template import.

## default

Use the default scene when no stronger scene signal is selected.
""",
        "RELATIONSHIP.md": """# Relationship Vocabulary

status:: source

Relationship pages describe target-specific summaries and permissions. They do not rewrite SOUL identity.

## user

Default relationship starts neutral and respectful until real interaction or approved memory says otherwise.
""",
        "MEMORY.md": """# Memory Policy

status:: source

Memory pages are ordinary workspace source. They are not fake user memories and are not all injected automatically.

## Template Memory

Template memories must be clearly marked when they are examples or bundled product help.
""",
        "BOUNDARY.md": """# Boundaries

status:: source
priority:: high

- No automatic default active character creation.
- No imported runtime state or build artifacts.
- No fake intimacy from templates.
- Explicit user approval is required before workspace commit.
""",
        "LORE.md": f"""# Lore

status:: optional

Optional lore for {display_name}. This can be edited after creation.
""",
        "relationships/user.md": _relationship_user_page(),
        "relationships/_template.md": _relationship_template_page(),
        "scenes/default.md": _default_scene_page(),
        "memory/core.md": _core_memory_page(),
    }
    if relaylm_onboarding_memory:
        files["memory/topics/relaylm.md"] = _relaylm_onboarding_memory()
        files["scenes/relaylm_onboarding.md"] = _relaylm_onboarding_scene()
    if showcase:
        files["memory/topics/showcase_notes.md"] = """# Showcase Notes

status:: template_example
source:: template:showcase
scope:: example_character_behavior

This page demonstrates curated character continuity without claiming real user familiarity.
"""
    return files


def _required_default_source(filename: str) -> str:
    title = filename.removesuffix(".md").title()
    return f"# {title}\n\nstatus:: source\n\nDefault {title} source for a complete Character Workspace.\n"


def _relationship_template_page() -> str:
    return """# Relationship Template

status:: template_source
source:: template:relationship_model

Use this as a human-editable shape for target-specific relationship pages.
"""


def _relationship_user_page() -> str:
    return """# User

status:: starter_relationship
source:: template:neutral_user_relationship

The user relationship starts neutral. Do not infer private familiarity from the template.
"""


def _default_scene_page() -> str:
    return """# Default Scene

status:: active
source:: template:default_scene

Default private/local chat scene. Keep memory disclosure bounded.
"""


def _relaylm_onboarding_scene() -> str:
    return """# RelayLM Onboarding

status:: template_knowledge
source:: template:relaylm_onboarding
scope:: product_help

Use this scene only when the user asks for help understanding RelayLM.
"""


def _core_memory_page() -> str:
    return """# Core Memory

status:: starter_memory
source:: template:core_memory

This page starts empty of user-specific facts. Add real continuity only through approved sources.
"""


def _relaylm_onboarding_memory() -> str:
    return """# RelayLM Onboarding Memory

status:: template_knowledge
source:: template:relaylm_onboarding
scope:: product_help
pin_state:: pinned
slp_update:: disabled
update_policy:: bundled_template_update_only

RelayLM is a local OpenAI-compatible relay for character-oriented conversation workflows. It keeps character source files, memory pages, scenes, relationship notes, and runtime projections separated so users can inspect and edit character behavior without giving templates runtime authority.

This is product-help knowledge, not a SOUL trait and not a fake memory about the user.
"""


def _demo_user_memory(record: CharacterTemplateRecord) -> str:
    return f"""# Demo User Example

status:: template_example
source:: template:{record.template_id}
scope:: demo_user

This is a clearly marked showcase-only memory about a fictional demo user. It must be removed when the showcase is used as a starter.
"""


def _showcase_scene_page(record: CharacterTemplateRecord) -> str:
    return f"""# Showcase Scene

status:: template_example
source:: template:{record.template_id}

Demonstrates grown-character behavior while keeping examples marked as template content.
"""


def _normalize_choice(value: str, allowed: set[str], fallback: str) -> str:
    normalized = value.strip()
    return normalized if normalized in allowed else fallback
