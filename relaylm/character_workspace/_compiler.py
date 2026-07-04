"""CW-A2 deterministic Character Workspace compiler.

The compiler is intentionally side-effect free unless ``write=True`` is passed.
It consumes the CW-A1 parser/validation contract and emits deterministic
``.relaylm/build/**`` artifact bytes for later RelayCTX/UI/SLP consumers.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from ._constants import (
    INTERNAL_BUILD_FILES,
    OPTIONAL_SOURCE_FILENAMES,
    REQUIRED_SOURCE_FILENAMES,
    SCHEMA_VERSION as WORKSPACE_SCHEMA_VERSION,
    SOURCE_KIND_BY_FILENAME,
)
from ._parser import parse_character_source_file, parse_markdown_blocks
from ._pathing import classify_character_workspace_path
from ._types import (
    CharacterMarkdownBlock,
    CharacterSourceParseResult,
    CharacterWorkspaceValidationResult,
    CharacterWorkspaceValidationStatus,
)
from ._validation import validate_character_workspace

COMPILER_NAME = "relaylm.character_workspace_compiler"
COMPILER_SCHEMA_VERSION = "relaylm.character_workspace.compiler_result.v0"

ARTIFACT_SCHEMA_VERSIONS = {
    "character_manifest.json": "relaylm.character_workspace.character_manifest.v0",
    "style_projection.json": "relaylm.character_workspace.style_projection.v0",
    "emotion_projection.json": "relaylm.character_workspace.emotion_projection.v0",
    "scene_units.jsonl": "relaylm.character_workspace.scene_units.v0",
    "relationship_projection.json": "relaylm.character_workspace.relationship_projection.v0",
    "memory_units.jsonl": "relaylm.character_workspace.memory_units.v0",
    "context_projection.json": "relaylm.character_workspace.context_projection.v0",
    "links.jsonl": "relaylm.character_workspace.links.v0",
}

EXPECTED_ARTIFACTS = tuple(ARTIFACT_SCHEMA_VERSIONS)
TIER_ORDER = ("tier0", "tier1", "tier2", "tier3")

UPPERCASE_TIER1_SOURCES = (
    "SOUL.md",
    "STYLE.md",
    "EMOTION.md",
    "RELATIONSHIP.md",
    "MEMORY.md",
    "BOUNDARY.md",
    "LORE.md",
)
DYNAMIC_SUFFIX_OWNERS = (
    ".relaylm/state/scene_state.json",
    ".relaylm/state/emotion_state.json",
    "retrieved_memory_blocks",
    "current_short_term_ctx",
    "latest_user_input",
    "request_local_policy_flags",
)

ANCHOR_RE = re.compile(r"\^([A-Za-z0-9][A-Za-z0-9_.:-]*)")


@dataclass(frozen=True)
class CharacterWorkspaceBuildArtifact:
    """A deterministic in-memory build artifact."""

    name: str
    relative_path: str
    schema_version: str
    content: bytes
    content_hash: str

    def text(self) -> str:
        return self.content.decode("utf-8")

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "relative_path": self.relative_path,
            "schema_version": self.schema_version,
            "content_hash": self.content_hash,
            "byte_count": len(self.content),
            "content_free": True,
        }


@dataclass(frozen=True)
class CharacterWorkspaceCompileResult:
    """Compiler result containing artifact bytes and a content-free summary."""

    schema_version: str
    generated_by: str
    status: str
    is_valid: bool
    character_id: str | None
    artifacts: tuple[CharacterWorkspaceBuildArtifact, ...]
    reason_ids: tuple[str, ...]
    blocking_reason_ids: tuple[str, ...]
    content_free: bool = True

    def artifact_map(self) -> dict[str, CharacterWorkspaceBuildArtifact]:
        return {artifact.name: artifact for artifact in self.artifacts}

    def to_public_dict(self) -> dict[str, Any]:
        artifact_summaries = tuple(artifact.to_public_dict() for artifact in self.artifacts)
        tier_counts = _tier_counts_from_artifacts(self.artifacts)
        return {
            "schema_version": self.schema_version,
            "generated_by": self.generated_by,
            "status": self.status,
            "is_valid": self.is_valid,
            "character_id": self.character_id,
            "artifact_names": tuple(artifact.name for artifact in self.artifacts),
            "artifact_count": len(self.artifacts),
            "artifact_summaries": artifact_summaries,
            "tier_counts": tier_counts,
            "reason_ids": self.reason_ids,
            "blocking_reason_ids": self.blocking_reason_ids,
            "content_free": True,
        }


def compile_character_workspace(
    root: str | Path,
    *,
    write: bool = False,
) -> CharacterWorkspaceCompileResult:
    """Compile a character workspace into deterministic build artifacts.

    ``write=False`` is the default and never writes files. ``write=True`` writes
    only the expected ``.relaylm/build/**`` files after artifact bytes have been
    produced in memory.
    """

    root_path = Path(root)
    preflight_errors = _preflight_root_errors(root_path)
    character_id = root_path.name if root_path.name else None
    if preflight_errors:
        return _blocked_result(character_id, preflight_errors)

    validation = validate_character_workspace(root_path, character_id=character_id, public=False)
    assert isinstance(validation, CharacterWorkspaceValidationResult)
    if not validation.is_valid:
        reason_ids = tuple(validation.reason_ids or (validation.status.value,))
        return _blocked_result(character_id, reason_ids, status=validation.status.value)

    symlink_errors = _find_symlink_escape_errors(root_path)
    if symlink_errors:
        return _blocked_result(character_id, symlink_errors, status=CharacterWorkspaceValidationStatus.PATH_ESCAPE_REJECTED.value)

    try:
        state = _compile_state(root_path, validation)
        artifacts = _build_artifacts(state)
        result = CharacterWorkspaceCompileResult(
            schema_version=COMPILER_SCHEMA_VERSION,
            generated_by=COMPILER_NAME,
            status="valid",
            is_valid=True,
            character_id=character_id,
            artifacts=artifacts,
            reason_ids=(),
            blocking_reason_ids=(),
            content_free=True,
        )
        if write:
            write_character_workspace_build_artifacts(root_path, result)
        return result
    except _CompilerBlocked as exc:
        return _blocked_result(character_id, exc.reason_ids, status=exc.status)


def build_character_workspace_compiler_projection(
    root: str | Path,
    *,
    write: bool = False,
) -> dict[str, Any]:
    """Return a public, content-free compiler projection.

    This helper is intended for UI/API diagnostics. It never includes raw
    Markdown bodies, absolute paths, memory text, relationship bodies, scene
    bodies, queue records, or runtime-private identifiers.
    """

    return compile_character_workspace(root, write=write).to_public_dict()


def write_character_workspace_build_artifacts(
    root: str | Path,
    result: CharacterWorkspaceCompileResult,
) -> tuple[str, ...]:
    """Write compiler artifacts under ``.relaylm/build`` only."""

    if not result.is_valid:
        raise ValueError("cannot write invalid Character Workspace compile result")

    root_path = Path(root)
    build_root = _safe_build_root(root_path)
    build_root.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for artifact in result.artifacts:
        target = build_root / artifact.name
        if target.name != artifact.name or artifact.name not in EXPECTED_ARTIFACTS:
            raise ValueError("unexpected build artifact path")
        if not _is_relative_to(target.resolve(), root_path.resolve()):
            raise ValueError("build artifact write escaped workspace root")
        target.write_bytes(artifact.content)
        written.append(f".relaylm/build/{artifact.name}")
    return tuple(written)


class _CompilerBlocked(Exception):
    def __init__(self, status: str, reason_ids: Iterable[str]) -> None:
        super().__init__(status)
        self.status = status
        self.reason_ids = tuple(reason_ids)


def _blocked_result(
    character_id: str | None,
    reason_ids: Iterable[str],
    *,
    status: str = "invalid_workspace",
) -> CharacterWorkspaceCompileResult:
    reasons = tuple(dict.fromkeys(reason_ids))
    return CharacterWorkspaceCompileResult(
        schema_version=COMPILER_SCHEMA_VERSION,
        generated_by=COMPILER_NAME,
        status=status,
        is_valid=False,
        character_id=character_id,
        artifacts=(),
        reason_ids=reasons,
        blocking_reason_ids=reasons,
        content_free=True,
    )


def _compile_state(root: Path, validation: CharacterWorkspaceValidationResult) -> dict[str, Any]:
    source_results = tuple(validation.source_results)
    source_by_filename = {source.filename: source for source in source_results}

    source_files = _source_file_summaries(source_results)
    uppercase_fragments = _uppercase_fragments(source_results)
    style_fragments = tuple(fragment for fragment in uppercase_fragments if fragment["source_path"] == "STYLE.md")
    emotion_fragments = tuple(fragment for fragment in uppercase_fragments if fragment["source_path"] == "EMOTION.md")
    scene_policy_fragments = tuple(fragment for fragment in uppercase_fragments if fragment["source_path"] == "SCENE.md")
    relationship_policy_fragments = tuple(fragment for fragment in uppercase_fragments if fragment["source_path"] == "RELATIONSHIP.md")
    memory_policy_fragments = tuple(fragment for fragment in uppercase_fragments if fragment["source_path"] == "MEMORY.md")

    scene_page_units = _collect_scene_units(root)
    relationship_page_units = _collect_relationship_units(root)
    memory_page_units = _collect_memory_units(root)

    scene_policy_units = tuple(
        _policy_unit(fragment, artifact_name="scene_units.jsonl", unit_kind="scene_policy", tier="tier1")
        for fragment in scene_policy_fragments
    )
    memory_policy_units = tuple(
        _policy_unit(fragment, artifact_name="memory_units.jsonl", unit_kind="memory_policy", tier="tier1")
        for fragment in memory_policy_fragments
    )

    tier1_fragments = tuple(
        fragment
        for fragment in uppercase_fragments
        if fragment["source_path"] in UPPERCASE_TIER1_SOURCES or fragment["source_path"] == "SCENE.md"
    )
    tier2_candidate_fragments = tuple(
        unit
        for unit in (*scene_page_units, *relationship_page_units, *memory_page_units)
        if unit.get("tier") == "tier2" and unit.get("prompt_candidate") is True
    )

    lowercase_presence = {
        "relationships": _has_markdown_under(root / "relationships"),
        "scenes": _has_markdown_under(root / "scenes"),
        "memory": _has_markdown_under(root / "memory"),
    }

    return {
        "root": root,
        "character_id": validation.character_id or root.name,
        "validation": validation,
        "source_by_filename": source_by_filename,
        "source_files": source_files,
        "uppercase_fragments": uppercase_fragments,
        "style_fragments": style_fragments,
        "emotion_fragments": emotion_fragments,
        "scene_policy_units": scene_policy_units,
        "scene_page_units": scene_page_units,
        "relationship_policy_fragments": relationship_policy_fragments,
        "relationship_page_units": relationship_page_units,
        "memory_policy_units": memory_policy_units,
        "memory_page_units": memory_page_units,
        "tier1_fragments": tier1_fragments,
        "tier2_candidate_fragments": tier2_candidate_fragments,
        "lowercase_presence": lowercase_presence,
    }


def _build_artifacts(state: dict[str, Any]) -> tuple[CharacterWorkspaceBuildArtifact, ...]:
    manifest = _character_manifest_artifact(state)
    style = _style_projection_artifact(state)
    emotion = _emotion_projection_artifact(state)
    scene_units = _scene_units_artifact(state)
    relationship = _relationship_projection_artifact(state)
    memory_units = _memory_units_artifact(state)
    context = _context_projection_artifact(state)
    links = _links_artifact(state)
    return (
        _artifact("character_manifest.json", manifest),
        _artifact("style_projection.json", style),
        _artifact("emotion_projection.json", emotion),
        _artifact_jsonl("scene_units.jsonl", scene_units),
        _artifact("relationship_projection.json", relationship),
        _artifact_jsonl("memory_units.jsonl", memory_units),
        _artifact("context_projection.json", context),
        _artifact_jsonl("links.jsonl", links),
    )


def _character_manifest_artifact(state: dict[str, Any]) -> dict[str, Any]:
    validation: CharacterWorkspaceValidationResult = state["validation"]
    source_files = state["source_files"]
    fragment_count = len(state["uppercase_fragments"]) + len(state["scene_page_units"]) + len(state["relationship_page_units"]) + len(state["memory_page_units"])
    return _base_artifact_dict(
        "character_manifest.json",
        content_hash=_stable_hash(
            source_files,
            state["lowercase_presence"],
            fragment_count,
            validation.status.value,
            validation.reason_ids,
        ),
        source_fragments=tuple(fragment["fragment_id"] for fragment in state["uppercase_fragments"]),
        extra={
            "character_id": state["character_id"],
            "workspace_schema_version": WORKSPACE_SCHEMA_VERSION,
            "workspace_format": WORKSPACE_SCHEMA_VERSION,
            "required_source_presence": {
                filename: filename in source_files for filename in REQUIRED_SOURCE_FILENAMES
            },
            "optional_lore_presence": "LORE.md" in source_files,
            "lowercase_wiki_domain_presence": state["lowercase_presence"],
            "build_artifact_schema_versions": ARTIFACT_SCHEMA_VERSIONS,
            "source_file_hashes": source_files,
            "fragment_count": fragment_count,
            "tier_summary": _tier_summary(state),
            "validation_status": validation.status.value,
            "is_valid": validation.is_valid,
            "blocking_reason_ids": validation.reason_ids,
            "content_policy": {
                "contains_absolute_paths": False,
                "contains_raw_full_source_body": False,
                "contains_memory_ids": False,
                "contains_queue_records": False,
                "contains_runtime_private_payloads": False,
                "contains_timestamps": False,
            },
        },
    )


def _style_projection_artifact(state: dict[str, Any]) -> dict[str, Any]:
    fragments = tuple(_projection_fragment(fragment, "style_projection.json", "tier1") for fragment in state["style_fragments"])
    return _base_artifact_dict(
        "style_projection.json",
        content_hash=_stable_hash(fragments),
        source_fragments=tuple(fragment["fragment_id"] for fragment in state["style_fragments"]),
        extra={
            "projection_owner": "STYLE.md",
            "tier": "tier1",
            "scope": {
                "owns": (
                    "voice",
                    "tone",
                    "roleplay_flavor",
                    "formatting",
                    "response_density",
                    "output_surface_hints",
                ),
                "does_not_own": (
                    "soul_identity",
                    "memory_truth",
                    "relationship_permission",
                    "scene_selection",
                    "runtime_state",
                ),
            },
            "surface_fragments": fragments,
        },
    )


def _emotion_projection_artifact(state: dict[str, Any]) -> dict[str, Any]:
    fragments = tuple(_projection_fragment(fragment, "emotion_projection.json", "tier1") for fragment in state["emotion_fragments"])
    return _base_artifact_dict(
        "emotion_projection.json",
        content_hash=_stable_hash(fragments),
        source_fragments=tuple(fragment["fragment_id"] for fragment in state["emotion_fragments"]),
        extra={
            "projection_owner": "EMOTION.md",
            "tier": "tier1",
            "scope": {
                "owns": (
                    "emotion_profile_definitions",
                    "expression_modulation_hints",
                    "boundary_compatible_metadata",
                ),
                "does_not_own": (
                    "current_emotion_state",
                    ".relaylm/state/emotion_state.json",
                    "scene_ownership",
                    "runtime_state",
                ),
            },
            "emotion_profile_fragments": fragments,
            "state_write_policy": {
                "writes_relaylm_state": False,
                "current_emotion_state_saved": False,
            },
        },
    )


def _scene_units_artifact(state: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    units = (*state["scene_policy_units"], *state["scene_page_units"])
    return tuple(sorted(units, key=_unit_sort_key))


def _relationship_projection_artifact(state: dict[str, Any]) -> dict[str, Any]:
    policy = tuple(_projection_fragment(fragment, "relationship_projection.json", "tier1") for fragment in state["relationship_policy_fragments"])
    targets = tuple(sorted(state["relationship_page_units"], key=_unit_sort_key))
    return _base_artifact_dict(
        "relationship_projection.json",
        content_hash=_stable_hash(policy, targets),
        source_fragments=tuple(fragment["fragment_id"] for fragment in state["relationship_policy_fragments"]),
        extra={
            "projection_owner": "RELATIONSHIP.md + relationships/*.md",
            "scope": {
                "owns": (
                    "relationship_role_vocabulary",
                    "relationship_parameter_vocabulary",
                    "target_specific_relationship_summaries",
                ),
                "does_not_own": (
                    "relayrel_policy_rewrite",
                    "relationship_important_parameter_auto_apply",
                    "soul_identity",
                ),
            },
            "policy_tier": "tier1",
            "target_summary_tier": "tier2",
            "policy_fragments": policy,
            "target_relationship_units": targets,
        },
    )


def _memory_units_artifact(state: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    units = (*state["memory_policy_units"], *state["memory_page_units"])
    return tuple(sorted(units, key=_unit_sort_key))


def _context_projection_artifact(state: dict[str, Any]) -> dict[str, Any]:
    tier1 = tuple(_context_fragment(fragment) for fragment in state["tier1_fragments"])
    tier2 = tuple(_context_fragment(unit) for unit in state["tier2_candidate_fragments"])
    content_hash_summary = {
        "tier1": _hash_many(fragment["content_hash"] for fragment in tier1),
        "tier2_candidates": _hash_many(fragment["content_hash"] for fragment in tier2),
        "workspace_sources": _stable_hash(state["source_files"], state["lowercase_presence"]),
    }
    return _base_artifact_dict(
        "context_projection.json",
        content_hash=_stable_hash(tier1, tier2, content_hash_summary),
        source_fragments=tuple(fragment["fragment_id"] for fragment in state["tier1_fragments"]),
        extra={
            "tier_order": TIER_ORDER,
            "tiers": (
                {
                    "tier": "tier0",
                    "name": "runtime/system/safety wrapper",
                    "owned_by": "runtime",
                    "compiler_owns": False,
                    "position": "prefix_before_character_workspace",
                    "fragments": (),
                },
                {
                    "tier": "tier1",
                    "name": "character stable prefix",
                    "owned_by": "character_workspace",
                    "compiler_owns": True,
                    "fragments": tier1,
                },
                {
                    "tier": "tier2",
                    "name": "target/session semi-stable prefix",
                    "owned_by": "selector_or_relayctx",
                    "compiler_owns": "candidate_metadata_only",
                    "fragments": tier2,
                },
                {
                    "tier": "tier3",
                    "name": "dynamic suffix",
                    "owned_by": "runtime_request_path",
                    "compiler_owns": False,
                    "position": "last",
                    "belongs_last": True,
                    "runtime_injection_out_of_scope": True,
                    "placeholders": DYNAMIC_SUFFIX_OWNERS,
                    "fragments": (),
                },
            ),
            "stable_prefix_fragment_list": tier1,
            "semi_stable_candidate_fragment_list": tier2,
            "dynamic_suffix_contract": {
                "tier": "tier3",
                "belongs_last": True,
                "generated_by_compiler": False,
                "runtime_injection_out_of_scope": True,
                "must_follow_tier2": True,
                "placeholders": DYNAMIC_SUFFIX_OWNERS,
            },
            "byte_stability_indicators": {
                "json_sort_keys": True,
                "jsonl_stable_order": True,
                "fixed_trailing_newline": True,
                "no_time_fields": True,
                "no_mtime": True,
                "no_absolute_path": True,
                "no_random_uuid": True,
            },
            "content_hash_summary": content_hash_summary,
            "public_safe_projection_summary": {
                "content_free": True,
                "tier_order": TIER_ORDER,
                "tier1_fragment_count": len(tier1),
                "tier2_candidate_fragment_count": len(tier2),
                "dynamic_suffix_last": True,
                "runtime_prompt_injection": False,
            },
        },
    )


def _links_artifact(state: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    links: list[dict[str, Any]] = []
    for fragment in state["uppercase_fragments"]:
        links.append(_link("source_file_to_fragment", fragment["source_path"], fragment["fragment_id"], fragment["content_hash"]))
        artifact_name = _artifact_for_source(fragment["source_path"])
        links.append(_link("fragment_to_projection_artifact", fragment["fragment_id"], artifact_name, fragment["content_hash"]))

    for unit in (*state["scene_page_units"], *state["relationship_page_units"], *state["memory_page_units"]):
        links.append(_link("page_to_unit", unit["source_path"], unit["unit_id"], unit["content_hash"]))
        links.append(_link("unit_to_projection_artifact", unit["unit_id"], unit["artifact_name"], unit["content_hash"]))

    return tuple(sorted(links, key=lambda item: (item["link_type"], item["from"], item["to"])))


def _source_file_summaries(source_results: Iterable[CharacterSourceParseResult]) -> dict[str, str]:
    return {
        source.filename: source.content_hash or ""
        for source in sorted(source_results, key=lambda item: item.filename)
    }


def _uppercase_fragments(source_results: Iterable[CharacterSourceParseResult]) -> tuple[dict[str, Any], ...]:
    fragments: list[dict[str, Any]] = []
    for source in sorted(source_results, key=lambda item: item.filename):
        occurrence: dict[str, int] = {}
        for block in source.blocks:
            occurrence_key = block.anchor or _slug(block.heading or "root")
            occurrence[occurrence_key] = occurrence.get(occurrence_key, 0) + 1
            fragment_id = _stable_fragment_id(
                "source",
                source.filename,
                block,
                occurrence[occurrence_key],
            )
            fragments.append(
                {
                    "fragment_id": fragment_id,
                    "source_path": source.filename,
                    "source_kind": source.source_kind,
                    "heading": block.heading,
                    "heading_level": block.heading_level,
                    "has_anchor": block.anchor is not None,
                    "metadata": dict(sorted(block.metadata)),
                    "metadata_keys": tuple(key for key, _value in block.metadata),
                    "content_hash": block.content_hash,
                    "source_content_hash": source.content_hash,
                    "tier": _tier_for_uppercase_source(source.filename),
                    "prompt_candidate": source.filename in UPPERCASE_TIER1_SOURCES or source.filename == "SCENE.md",
                }
            )
    return tuple(fragments)


def _collect_scene_units(root: Path) -> tuple[dict[str, Any], ...]:
    units: list[dict[str, Any]] = []
    for path in _iter_markdown_files(root / "scenes"):
        relative = path.relative_to(root).as_posix()
        stage = "staging_candidate" if "/_inbox/" in f"/{relative}/" else "active"
        prompt_candidate = stage == "active"
        units.extend(
            _page_units(
                root,
                path,
                unit_domain="scene",
                unit_kind="scene_page",
                artifact_name="scene_units.jsonl",
                tier="tier2" if prompt_candidate else "staging",
                prompt_candidate=prompt_candidate,
                stage=stage,
            )
        )
    return tuple(units)


def _collect_relationship_units(root: Path) -> tuple[dict[str, Any], ...]:
    units: list[dict[str, Any]] = []
    for path in _iter_markdown_files(root / "relationships"):
        relative = path.relative_to(root).as_posix()
        stage = "proposal_candidate" if "/_inbox/" in f"/{relative}/" else "active"
        prompt_candidate = stage == "active"
        units.extend(
            _page_units(
                root,
                path,
                unit_domain="relationship",
                unit_kind="relationship_page",
                artifact_name="relationship_projection.json",
                tier="tier2" if prompt_candidate else "staging",
                prompt_candidate=prompt_candidate,
                stage=stage,
            )
        )
    return tuple(units)


def _collect_memory_units(root: Path) -> tuple[dict[str, Any], ...]:
    units: list[dict[str, Any]] = []
    for path in _iter_markdown_files(root / "memory"):
        relative = path.relative_to(root).as_posix()
        stage = _memory_stage(relative)
        prompt_candidate = False
        tier = "excluded" if stage == "forgotten_excluded" else "staging"
        if stage == "active":
            tier = "tier2"
            prompt_candidate = True
        page_units = _page_units(
            root,
            path,
            unit_domain="memory",
            unit_kind="memory_block",
            artifact_name="memory_units.jsonl",
            tier=tier,
            prompt_candidate=prompt_candidate,
            stage=stage,
            prompt_candidate_filter=_memory_prompt_candidate,
        )
        units.extend(page_units)
    return tuple(units)


def _page_units(
    root: Path,
    path: Path,
    *,
    unit_domain: str,
    unit_kind: str,
    artifact_name: str,
    tier: str,
    prompt_candidate: bool,
    stage: str,
    prompt_candidate_filter: Any | None = None,
) -> tuple[dict[str, Any], ...]:
    relative = path.relative_to(root).as_posix()
    classification = classify_character_workspace_path(relative)
    if classification.reason_ids:
        raise _CompilerBlocked("path_escape_rejected", classification.reason_ids)
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise _CompilerBlocked("malformed_markdown", ("source_file_not_utf8",)) from exc
    except OSError as exc:
        raise _CompilerBlocked("invalid_workspace", ("source_file_unreadable",)) from exc

    source_hash = _content_hash(text)
    blocks = parse_markdown_blocks(text)
    occurrence: dict[str, int] = {}
    units: list[dict[str, Any]] = []
    for block in blocks:
        occurrence_key = block.anchor or _slug(block.heading or "root")
        occurrence[occurrence_key] = occurrence.get(occurrence_key, 0) + 1
        unit_id = _stable_fragment_id(unit_domain, relative, block, occurrence[occurrence_key])
        block_prompt_candidate = prompt_candidate
        if prompt_candidate_filter is not None:
            block_prompt_candidate = bool(prompt_candidate_filter(block, stage, prompt_candidate))
        units.append(
            {
                "unit_id": unit_id,
                "fragment_id": unit_id,
                "unit_domain": unit_domain,
                "unit_kind": unit_kind,
                "source_path": relative,
                "source_stage": stage,
                "artifact_name": artifact_name,
                "heading": block.heading,
                "heading_level": block.heading_level,
                "has_anchor": block.anchor is not None,
                "metadata": dict(sorted(block.metadata)),
                "metadata_keys": tuple(key for key, _value in block.metadata),
                "content_hash": block.content_hash,
                "source_content_hash": source_hash,
                "tier": tier if block_prompt_candidate else ("excluded" if stage == "forgotten_excluded" else "staging"),
                "prompt_candidate": block_prompt_candidate,
                "candidate_only": not block_prompt_candidate,
                "raw_body_included": False,
            }
        )
    return tuple(units)


def _policy_unit(fragment: dict[str, Any], *, artifact_name: str, unit_kind: str, tier: str) -> dict[str, Any]:
    return {
        "unit_id": fragment["fragment_id"],
        "fragment_id": fragment["fragment_id"],
        "unit_domain": fragment["source_kind"],
        "unit_kind": unit_kind,
        "source_path": fragment["source_path"],
        "source_stage": "policy",
        "artifact_name": artifact_name,
        "heading": fragment["heading"],
        "heading_level": fragment["heading_level"],
        "has_anchor": fragment["has_anchor"],
        "metadata": fragment["metadata"],
        "metadata_keys": fragment["metadata_keys"],
        "content_hash": fragment["content_hash"],
        "source_content_hash": fragment["source_content_hash"],
        "tier": tier,
        "prompt_candidate": True,
        "candidate_only": False,
        "raw_body_included": False,
    }


def _memory_stage(relative: str) -> str:
    parts = PurePosixPath(relative).parts
    if len(parts) >= 2 and parts[0] == "memory" and parts[1] == "forgotten":
        return "forgotten_excluded"
    if len(parts) >= 2 and parts[0] == "memory" and parts[1] == "inbox":
        return "staging_candidate"
    return "active"


def _memory_prompt_candidate(block: CharacterMarkdownBlock, stage: str, page_prompt_candidate: bool) -> bool:
    if stage != "active" or not page_prompt_candidate:
        return False
    metadata = block.metadata_dict()
    status = metadata.get("status", "").lower()
    importance = metadata.get("importance", "").lower()
    return status in {"active", "stable"} or importance in {"high", "critical"}


def _projection_fragment(fragment: dict[str, Any], artifact_name: str, tier: str) -> dict[str, Any]:
    return {
        "fragment_id": fragment["fragment_id"],
        "source_path": fragment["source_path"],
        "source_kind": fragment["source_kind"],
        "artifact_name": artifact_name,
        "tier": tier,
        "heading": fragment["heading"],
        "metadata": fragment["metadata"],
        "metadata_keys": fragment["metadata_keys"],
        "content_hash": fragment["content_hash"],
        "source_content_hash": fragment["source_content_hash"],
        "raw_body_included": False,
    }


def _context_fragment(fragment_or_unit: dict[str, Any]) -> dict[str, Any]:
    return {
        "fragment_id": fragment_or_unit.get("fragment_id") or fragment_or_unit["unit_id"],
        "source_path": fragment_or_unit["source_path"],
        "tier": fragment_or_unit["tier"],
        "content_hash": fragment_or_unit["content_hash"],
        "source_content_hash": fragment_or_unit.get("source_content_hash"),
        "prompt_candidate": fragment_or_unit.get("prompt_candidate", True),
        "raw_body_included": False,
    }


def _base_artifact_dict(
    artifact_name: str,
    *,
    content_hash: str,
    source_fragments: tuple[str, ...],
    extra: dict[str, Any],
) -> dict[str, Any]:
    base = {
        "schema_version": ARTIFACT_SCHEMA_VERSIONS[artifact_name],
        "generated_by": COMPILER_NAME,
        "diagnostics_only": False,
        "workspace_format": WORKSPACE_SCHEMA_VERSION,
        "content_hash": content_hash,
        "source_fragments": source_fragments,
    }
    base.update(extra)
    return base


def _artifact(artifact_name: str, payload: dict[str, Any]) -> CharacterWorkspaceBuildArtifact:
    content = _json_bytes(payload)
    return CharacterWorkspaceBuildArtifact(
        name=artifact_name,
        relative_path=f".relaylm/build/{artifact_name}",
        schema_version=ARTIFACT_SCHEMA_VERSIONS[artifact_name],
        content=content,
        content_hash=_bytes_hash(content),
    )


def _artifact_jsonl(artifact_name: str, rows: tuple[dict[str, Any], ...]) -> CharacterWorkspaceBuildArtifact:
    content = _jsonl_bytes(rows)
    return CharacterWorkspaceBuildArtifact(
        name=artifact_name,
        relative_path=f".relaylm/build/{artifact_name}",
        schema_version=ARTIFACT_SCHEMA_VERSIONS[artifact_name],
        content=content,
        content_hash=_bytes_hash(content),
    )


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _jsonl_bytes(rows: Iterable[dict[str, Any]]) -> bytes:
    return b"".join(_json_bytes(row) for row in rows)


def _content_hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _bytes_hash(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _stable_hash(*values: Any) -> str:
    return _bytes_hash(_json_bytes(values))


def _hash_many(values: Iterable[str | None]) -> str:
    return _stable_hash(tuple(sorted(value or "" for value in values)))


def _stable_fragment_id(domain: str, relative_path: str, block: CharacterMarkdownBlock, occurrence: int) -> str:
    anchor = block.anchor
    if anchor:
        return _safe_id(f"{domain}:{anchor.lstrip('^')}")
    heading = _slug(block.heading or "root")
    return _safe_id(f"{domain}:{relative_path}:{heading}:{occurrence}")


def _safe_id(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.:-]+", "-", value.strip())
    return safe.strip("-").lower()


def _slug(value: str) -> str:
    stripped = value.strip().lower()
    stripped = re.sub(r"\s+", "-", stripped)
    stripped = re.sub(r"[^a-z0-9_.:-]+", "-", stripped)
    return stripped.strip("-") or "root"


def _tier_for_uppercase_source(filename: str) -> str:
    if filename in UPPERCASE_TIER1_SOURCES or filename == "SCENE.md":
        return "tier1"
    return "out_of_scope"


def _artifact_for_source(source_path: str) -> str:
    return {
        "STYLE.md": "style_projection.json",
        "EMOTION.md": "emotion_projection.json",
        "SCENE.md": "scene_units.jsonl",
        "RELATIONSHIP.md": "relationship_projection.json",
        "MEMORY.md": "memory_units.jsonl",
    }.get(source_path, "context_projection.json")


def _unit_sort_key(unit: dict[str, Any]) -> tuple[str, str, str]:
    return (unit.get("source_path", ""), unit.get("unit_id", ""), unit.get("content_hash", ""))


def _tier_summary(state: dict[str, Any]) -> dict[str, int]:
    return {
        "tier0": 1,
        "tier1": len(state["tier1_fragments"]),
        "tier2_candidates": len(state["tier2_candidate_fragments"]),
        "tier3_placeholders": len(DYNAMIC_SUFFIX_OWNERS),
    }


def _tier_counts_from_artifacts(artifacts: tuple[CharacterWorkspaceBuildArtifact, ...]) -> dict[str, int]:
    if not artifacts:
        return {}
    context = next((artifact for artifact in artifacts if artifact.name == "context_projection.json"), None)
    if context is None:
        return {}
    try:
        payload = json.loads(context.text())
    except json.JSONDecodeError:
        return {}
    return {
        "tier0": 1,
        "tier1": len(payload.get("stable_prefix_fragment_list", ())),
        "tier2_candidates": len(payload.get("semi_stable_candidate_fragment_list", ())),
        "tier3_placeholders": len(payload.get("dynamic_suffix_contract", {}).get("placeholders", ())),
    }


def _link(link_type: str, source: str, target: str, content_hash: str) -> dict[str, Any]:
    link_id = _safe_id(f"{link_type}:{source}:{target}")
    return {
        "schema_version": ARTIFACT_SCHEMA_VERSIONS["links.jsonl"],
        "generated_by": COMPILER_NAME,
        "link_id": link_id,
        "link_type": link_type,
        "from": source,
        "to": target,
        "content_hash": content_hash,
        "contains_absolute_path": False,
        "content_free": True,
    }


def _iter_markdown_files(root: Path) -> tuple[Path, ...]:
    if not root.exists():
        return ()
    if not root.is_dir():
        raise _CompilerBlocked("invalid_workspace", ("reserved_path_conflict",))
    return tuple(sorted((path for path in root.rglob("*.md") if path.is_file()), key=lambda item: item.as_posix()))


def _has_markdown_under(root: Path) -> bool:
    return bool(_iter_markdown_files(root))


def _preflight_root_errors(root: Path) -> tuple[str, ...]:
    raw = str(root).replace("\\", "/")
    if any(part == ".." for part in raw.split("/")):
        return ("path_traversal_rejected",)
    if not root.exists() or not root.is_dir():
        return ("workspace_root_missing_or_not_directory",)
    return ()


def _find_symlink_escape_errors(root: Path) -> tuple[str, ...]:
    resolved_root = root.resolve()
    for path in root.rglob("*"):
        if not path.is_symlink():
            continue
        try:
            resolved = path.resolve()
        except OSError:
            return ("symlink_escape_rejected",)
        if not _is_relative_to(resolved, resolved_root):
            return ("symlink_escape_rejected",)
    return ()


def _safe_build_root(root: Path) -> Path:
    resolved_root = root.resolve()
    relaylm_dir = root / ".relaylm"
    if relaylm_dir.exists() and relaylm_dir.is_symlink():
        raise ValueError(".relaylm symlink escape rejected")
    build_root = relaylm_dir / "build"
    if build_root.exists() and build_root.is_symlink():
        raise ValueError(".relaylm/build symlink escape rejected")
    resolved_build = build_root.resolve() if build_root.exists() else (relaylm_dir.resolve() / "build" if relaylm_dir.exists() else resolved_root / ".relaylm" / "build")
    if not _is_relative_to(resolved_build, resolved_root):
        raise ValueError("build directory escaped workspace root")
    return build_root


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
