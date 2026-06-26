"""Canonical read-only Primary MEM current-state resolution.

This module is the production authority for mapping immutable Primary page
revisions to one stable logical memory identity.  It intentionally understands
the existing Phase I-3 correction artifact layout, but it does not create,
repair, or mutate any store object.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from ._relaymem_primary_page_writer_common import (
    FRONT_MATTER_KEYS,
    MAX_PAGE_BYTES,
    bad_text,
    is_sha256,
    parse_page_markdown,
)
from .relaymem_primary_recall import _load_control_state, _load_validated_page

PRIMARY_CURRENT_STATE_SCHEMA = "relaylm.mem.primary_current_state.v0"
CORRECTION_PREPARED_SCHEMA = "relaylm.mem.correct_prepared.v0"
CORRECTION_RECEIPT_SCHEMA = "relaylm.mem.correct_receipt.v0"
CORRECTION_ROOT = PurePosixPath("memory/mem/corrections/v0")
_MAX_ARTIFACT_BYTES = 32_768
_MAX_REASONS = 32


class PrimaryCurrentStateError(RuntimeError):
    """Bounded resolver failure safe for translation at API boundaries."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class PrimaryCorrectionStateIndex:
    """Compatibility shape previously owned by the correction module."""

    current_by_logical: dict[str, tuple[str, int]]
    logical_by_physical: dict[str, str]
    superseded_physical: frozenset[str]
    pending_physical: frozenset[str]
    invalid_logical: frozenset[str]
    receipts_by_logical: dict[str, tuple[dict[str, Any], ...]]
    pending_logical: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True, repr=False)
class PrimaryCurrentState:
    """Internal current-state result with content-free diagnostic rendering."""

    lifecycle_state: str
    mutation_state: str
    retrieval_eligible: bool
    memory_id: str
    current_physical_id: str
    current_revision: int
    controls_valid: bool
    page_valid: bool
    bounded_reason_ids: tuple[str, ...]
    title: str = field(repr=False)
    summary: str = field(repr=False)
    metadata: Mapping[str, Any] = field(repr=False)
    page_digest: str = field(repr=False)
    relative_path: str = field(repr=False)

    @property
    def schema(self) -> str:
        return PRIMARY_CURRENT_STATE_SCHEMA

    def __repr__(self) -> str:
        return (
            "PrimaryCurrentState("
            f"lifecycle_state={self.lifecycle_state!r}, "
            f"mutation_state={self.mutation_state!r}, "
            f"retrieval_eligible={self.retrieval_eligible!r}, "
            f"current_revision={self.current_revision!r}, "
            f"controls_valid={self.controls_valid!r}, "
            f"page_valid={self.page_valid!r}, "
            f"bounded_reason_ids={self.bounded_reason_ids!r})"
        )

    def to_internal_dict(self) -> dict[str, Any]:
        return {
            "schema": PRIMARY_CURRENT_STATE_SCHEMA,
            "lifecycle_state": self.lifecycle_state,
            "mutation_state": self.mutation_state,
            "retrieval_eligible": self.retrieval_eligible,
            "memory_id": self.memory_id,
            "current_physical_id": self.current_physical_id,
            "current_revision": self.current_revision,
            "controls_valid": self.controls_valid,
            "page_valid": self.page_valid,
            "bounded_reason_ids": list(self.bounded_reason_ids),
        }

    def to_log_dict(self) -> dict[str, Any]:
        return {
            "schema": PRIMARY_CURRENT_STATE_SCHEMA,
            "lifecycle_state": self.lifecycle_state,
            "mutation_state": self.mutation_state,
            "retrieval_eligible": self.retrieval_eligible,
            "current_revision": self.current_revision,
            "controls_valid": self.controls_valid,
            "page_valid": self.page_valid,
            "bounded_reason_ids": list(self.bounded_reason_ids),
            "content_included": False,
            "path_included": False,
            "digest_included": False,
            "namespace_included": False,
            "physical_id_included": False,
        }


def load_primary_current_state_index(
    store_root: str | Path, *, namespace: str
) -> PrimaryCorrectionStateIndex:
    """Read the validated Phase I-3 revision chain without filesystem mutation."""

    root = _safe_store_root(store_root)
    base = root / CORRECTION_ROOT
    if base.is_symlink():
        return empty_primary_current_state_index(invalid={"*"})
    if not base.exists():
        return empty_primary_current_state_index()
    if not base.is_dir():
        return empty_primary_current_state_index(invalid={"*"})

    current: dict[str, tuple[str, int]] = {}
    logical_by_physical: dict[str, str] = {}
    superseded: set[str] = set()
    pending_physical: set[str] = set()
    pending_logical: set[str] = set()
    invalid: set[str] = set()
    receipts_by_logical: dict[str, tuple[dict[str, Any], ...]] = {}

    try:
        memory_dirs = sorted(base.iterdir(), key=lambda item: item.name)
    except OSError:
        return empty_primary_current_state_index(invalid={"*"})

    for memory_dir in memory_dirs:
        logical = memory_dir.name
        if not is_sha256(logical) or memory_dir.is_symlink() or not memory_dir.is_dir():
            invalid.add(logical if is_sha256(logical) else "*")
            continue

        prepared_by_operation: dict[str, dict[str, Any]] = {}
        applied: list[dict[str, Any]] = []
        correction_applied: list[dict[str, Any]] = []
        try:
            entries = sorted(memory_dir.iterdir(), key=lambda item: item.name)
        except OSError:
            invalid.add(logical)
            continue

        for path in entries:
            if path.name == ".lock":
                if path.is_symlink() or (path.exists() and not path.is_file()):
                    invalid.add(logical)
                continue
            if path.is_symlink() or not path.is_file():
                invalid.add(logical)
                continue
            if path.name.endswith(".prepared.json"):
                value = _read_json(path)
                schema = value.get("schema_version") if isinstance(value, dict) else None
                if schema == CORRECTION_PREPARED_SCHEMA:
                    valid = _valid_prepared(
                        value, namespace=namespace, memory_id=logical
                    )
                elif schema == "relaylm.mem.forget_prepared.v0":
                    from .relaymem_primary_forget_artifact import (
                        validate_forget_prepared,
                    )

                    valid = validate_forget_prepared(value)
                    valid = bool(
                        valid
                        and value.get("namespace") == namespace
                        and value.get("memory_id") == logical
                    )
                else:
                    valid = False
                if not valid:
                    invalid.add(logical)
                    continue
                operation_key = str(value["operation_key"])
                if operation_key in prepared_by_operation:
                    invalid.add(logical)
                    continue
                prepared_by_operation[operation_key] = value
            elif path.name.endswith(".applied.json"):
                value = _read_json(path)
                if not _valid_applied(value, namespace=namespace, memory_id=logical):
                    invalid.add(logical)
                    continue
                applied.append(value)
                correction_applied.append(value)
            elif path.name.endswith(".tombstone.json"):
                value = _read_json(path)
                from .relaymem_primary_forget_finalization_artifact import (
                    validate_forget_tombstone,
                )

                if (
                    not validate_forget_tombstone(value)
                    or value.get("namespace") != namespace
                    or value.get("memory_id") != logical
                ):
                    invalid.add(logical)
                    continue
                applied.append(value)
            else:
                invalid.add(logical)

        applied.sort(key=lambda item: (int(item["result_revision"]), str(item["operation_key"])))
        prior_physical = logical
        prior_revision = 1
        seen_operations: set[str] = set()
        seen_operation_ids: set[str] = set()
        chain_ok = True
        for item in applied:
            operation_key = str(item["operation_key"])
            operation_id = str(item["operation_id"])
            if (
                operation_key in seen_operations
                or operation_id in seen_operation_ids
                or int(item["prior_revision"]) != prior_revision
                or int(item["result_revision"]) != prior_revision + 1
                or item["prior_physical_id"] != prior_physical
            ):
                chain_ok = False
                break
            seen_operations.add(operation_key)
            seen_operation_ids.add(operation_id)
            superseded.add(prior_physical)
            logical_by_physical[prior_physical] = logical
            prior_physical = str(item["result_physical_id"])
            logical_by_physical[prior_physical] = logical
            prior_revision += 1

        unresolved: list[dict[str, Any]] = []
        for operation_key, item in prepared_by_operation.items():
            if operation_key in seen_operations:
                continue
            unresolved.append(item)
            successor = item.get("successor_physical_id")
            if is_sha256(successor):
                pending_physical.add(str(successor))
                logical_by_physical[str(successor)] = logical

        if len(unresolved) > 1:
            chain_ok = False
        elif unresolved:
            pending = unresolved[0]
            if (
                pending.get("prior_physical_id") != prior_physical
                or pending.get("prior_revision") != prior_revision
                or pending.get("result_revision") != prior_revision + 1
            ):
                chain_ok = False
            else:
                pending_logical.add(logical)

        if not chain_ok:
            invalid.add(logical)
            continue

        current[logical] = (prior_physical, prior_revision)
        logical_by_physical.setdefault(logical, logical)
        receipts_by_logical[logical] = tuple(correction_applied)

    return PrimaryCorrectionStateIndex(
        current_by_logical=current,
        logical_by_physical=logical_by_physical,
        superseded_physical=frozenset(superseded),
        pending_physical=frozenset(pending_physical),
        invalid_logical=frozenset(invalid),
        receipts_by_logical=receipts_by_logical,
        pending_logical=frozenset(pending_logical),
    )


def resolve_primary_current_identity(
    state: PrimaryCorrectionStateIndex, physical_identity: str
) -> tuple[str, int, bool] | None:
    """Map a physical page to stable logical identity and currentness."""

    if not is_sha256(physical_identity):
        return None
    logical = state.logical_by_physical.get(physical_identity, physical_identity)
    if "*" in state.invalid_logical or logical in state.invalid_logical:
        return None
    if physical_identity in state.pending_physical:
        return None
    current = state.current_by_logical.get(logical, (logical, 1))
    return logical, int(current[1]), physical_identity == current[0]


def resolve_primary_current_state(
    store_root: str | Path,
    *,
    namespace: str,
    memory_id: str,
    expected_revision: int | None = None,
) -> PrimaryCurrentState:
    """Resolve one exact logical Primary memory using page and control evidence."""

    root = _safe_store_root(store_root)
    if not isinstance(namespace, str) or not namespace or namespace != namespace.strip():
        raise PrimaryCurrentStateError("target_not_found")
    if not is_sha256(memory_id):
        raise PrimaryCurrentStateError("target_not_found")
    if expected_revision is not None and (
        type(expected_revision) is not int or expected_revision < 1
    ):
        raise PrimaryCurrentStateError("invalid_request")

    control, control_reasons = _load_control_state(root)
    if control is None or control_reasons:
        raise PrimaryCurrentStateError("target_corrupt")

    logical_index = [
        entry
        for entry in control["index"]
        if entry.get("idempotency_key") == memory_id
        and entry.get("namespace") == namespace
    ]
    logical_log = [
        entry
        for entry in control["log"]
        if entry.get("idempotency_key") == memory_id
        and entry.get("namespace") == namespace
    ]
    if not logical_index and not logical_log:
        raise PrimaryCurrentStateError("target_not_found")
    if len(logical_index) != 1 or len(logical_log) != 1:
        raise PrimaryCurrentStateError("target_corrupt")

    index = load_primary_current_state_index(root, namespace=namespace)
    if "*" in index.invalid_logical or memory_id in index.invalid_logical:
        return _corrupt_state(memory_id, reasons=("primary_current_chain_invalid",))

    current_physical, current_revision = index.current_by_logical.get(memory_id, (memory_id, 1))
    if expected_revision is not None and current_revision != expected_revision:
        raise PrimaryCurrentStateError("stale_revision")

    current_index = [
        entry
        for entry in control["index"]
        if entry.get("idempotency_key") == current_physical
        and entry.get("namespace") == namespace
    ]
    current_log = [
        entry
        for entry in control["log"]
        if entry.get("idempotency_key") == current_physical
        and entry.get("namespace") == namespace
    ]
    if len(current_index) != 1 or len(current_log) != 1:
        return _corrupt_state(
            memory_id,
            current_physical=current_physical,
            current_revision=current_revision,
            reasons=("primary_current_controls_invalid",),
        )
    if current_index[0].get("page_relative_path") != current_log[0].get("page_relative_path"):
        return _corrupt_state(
            memory_id,
            current_physical=current_physical,
            current_revision=current_revision,
            reasons=("primary_current_controls_ambiguous",),
        )

    relative = current_index[0].get("page_relative_path")
    loaded, blocked = _load_validated_page(
        root,
        {"path": relative},
        expected_namespace=namespace,
        control=control,
    )
    if loaded is None or blocked:
        return _corrupt_state(
            memory_id,
            current_physical=current_physical,
            current_revision=current_revision,
            reasons=("primary_current_page_invalid", *tuple(str(item) for item in blocked)),
        )

    path = root / PurePosixPath(str(relative))
    if path.is_symlink() or not path.is_file():
        return _corrupt_state(
            memory_id,
            current_physical=current_physical,
            current_revision=current_revision,
            reasons=("primary_current_page_not_regular",),
        )
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise PrimaryCurrentStateError("store_unavailable") from exc
    if not raw or len(raw) > MAX_PAGE_BYTES:
        return _corrupt_state(
            memory_id,
            current_physical=current_physical,
            current_revision=current_revision,
            reasons=("primary_current_page_size_invalid",),
        )
    try:
        markdown = raw.decode("utf-8")
    except UnicodeDecodeError:
        return _corrupt_state(
            memory_id,
            current_physical=current_physical,
            current_revision=current_revision,
            reasons=("primary_current_page_utf8_invalid",),
        )
    parsed = parse_page_markdown(markdown)
    if parsed.get("valid") is not True:
        return _corrupt_state(
            memory_id,
            current_physical=current_physical,
            current_revision=current_revision,
            reasons=("primary_current_page_schema_invalid",),
        )
    metadata = parsed["metadata"]
    if set(metadata) != set(FRONT_MATTER_KEYS):
        return _corrupt_state(
            memory_id,
            current_physical=current_physical,
            current_revision=current_revision,
            reasons=("primary_current_page_noncanonical",),
        )

    mutation_state = "prepared" if memory_id in index.pending_logical else "none"
    reasons = ("primary_mutation_prepared",) if mutation_state == "prepared" else ()
    return PrimaryCurrentState(
        lifecycle_state="active",
        mutation_state=mutation_state,
        retrieval_eligible=mutation_state == "none",
        memory_id=memory_id,
        current_physical_id=current_physical,
        current_revision=current_revision,
        controls_valid=True,
        page_valid=True,
        bounded_reason_ids=_reason_ids(reasons),
        title=str(metadata["title"]),
        summary=str(metadata["summary"]),
        metadata=dict(metadata),
        page_digest=sha256(raw).hexdigest(),
        relative_path=str(relative),
    )


def load_primary_current_target(
    store_root: str | Path,
    *,
    namespace: str,
    memory_id: str,
    expected_revision: int,
) -> dict[str, Any]:
    """Compatibility target view for mutation implementations."""

    state = resolve_primary_current_state(
        store_root,
        namespace=namespace,
        memory_id=memory_id,
        expected_revision=expected_revision,
    )
    if state.mutation_state == "corrupt" or not state.controls_valid or not state.page_valid:
        raise PrimaryCurrentStateError("target_corrupt")
    if state.lifecycle_state != "active":
        raise PrimaryCurrentStateError("target_not_active")
    return {
        "physical_id": state.current_physical_id,
        "revision": state.current_revision,
        "metadata": dict(state.metadata),
        "page_digest": state.page_digest,
        "relative_path": state.relative_path,
    }


def empty_primary_current_state_index(
    *, invalid: set[str] | None = None
) -> PrimaryCorrectionStateIndex:
    return PrimaryCorrectionStateIndex(
        {}, {}, frozenset(), frozenset(), frozenset(invalid or ()), {}, frozenset()
    )


def _corrupt_state(
    memory_id: str,
    *,
    current_physical: str | None = None,
    current_revision: int = 1,
    reasons: tuple[str, ...],
) -> PrimaryCurrentState:
    return PrimaryCurrentState(
        lifecycle_state="active",
        mutation_state="corrupt",
        retrieval_eligible=False,
        memory_id=memory_id,
        current_physical_id=current_physical or memory_id,
        current_revision=current_revision,
        controls_valid=False,
        page_valid=False,
        bounded_reason_ids=_reason_ids(reasons),
        title="",
        summary="",
        metadata={},
        page_digest="",
        relative_path="",
    )


def _valid_prepared(value: object, *, namespace: str, memory_id: str) -> bool:
    if not isinstance(value, dict):
        return False
    required = {
        "schema_version", "runtime_private", "content_included", "operation_id",
        "operation_key", "correction_id", "character_id", "namespace", "memory_id",
        "prior_revision", "result_revision", "prior_physical_id", "successor_physical_id",
        "successor_candidate_id", "source_event_kind", "memory_kind", "lineage_fingerprint",
        "prior_canonical_digest", "candidate_digest", "token_digest", "corrected_title",
        "corrected_summary", "reason", "title_changed", "summary_changed", "requested_at",
        "prepared_at", "status", "recovery_required",
    }
    return (
        set(value) == required
        and value.get("schema_version") == CORRECTION_PREPARED_SCHEMA
        and value.get("runtime_private") is True
        and value.get("content_included") is True
        and value.get("namespace") == namespace
        and value.get("memory_id") == memory_id
        and value.get("status") == "prepared"
        and value.get("recovery_required") is True
        and type(value.get("prior_revision")) is int
        and type(value.get("result_revision")) is int
        and value.get("prior_revision", 0) >= 1
        and value.get("result_revision") == value.get("prior_revision") + 1
        and all(
            is_sha256(value.get(key))
            for key in (
                "operation_key", "correction_id", "prior_physical_id",
                "successor_physical_id", "successor_candidate_id",
                "lineage_fingerprint", "prior_canonical_digest",
                "candidate_digest", "token_digest",
            )
        )
        and _bounded_text(value.get("operation_id"), 128, allow_empty=False)
        and _bounded_text(value.get("character_id"), 128, allow_empty=False)
        and _bounded_text(value.get("source_event_kind"), 128, allow_empty=False)
        and _bounded_text(value.get("corrected_title"), 160, allow_empty=True)
        and _bounded_text(value.get("corrected_summary"), 512, allow_empty=False)
        and _bounded_text(value.get("reason"), 512, allow_empty=False)
        and type(value.get("title_changed")) is bool
        and type(value.get("summary_changed")) is bool
    )


def _valid_applied(value: object, *, namespace: str, memory_id: str) -> bool:
    if not isinstance(value, dict):
        return False
    required = {
        "schema_version", "runtime_private", "content_included", "operation_id",
        "operation_key", "correction_id", "character_id", "namespace", "memory_id",
        "prior_revision", "result_revision", "prior_physical_id", "result_physical_id",
        "prior_canonical_digest", "result_canonical_digest", "candidate_digest",
        "token_digest", "requested_at", "applied_at", "reason", "status",
        "title_changed", "summary_changed", "recovery_required",
    }
    return (
        set(value) == required
        and value.get("schema_version") == CORRECTION_RECEIPT_SCHEMA
        and value.get("runtime_private") is True
        and value.get("content_included") is False
        and value.get("namespace") == namespace
        and value.get("memory_id") == memory_id
        and value.get("status") == "reconciled"
        and value.get("recovery_required") is False
        and type(value.get("prior_revision")) is int
        and type(value.get("result_revision")) is int
        and value.get("prior_revision", 0) >= 1
        and value.get("result_revision") == value.get("prior_revision") + 1
        and all(
            is_sha256(value.get(key))
            for key in (
                "operation_key", "correction_id", "prior_physical_id",
                "result_physical_id", "prior_canonical_digest",
                "result_canonical_digest", "candidate_digest", "token_digest",
            )
        )
        and _bounded_text(value.get("operation_id"), 128, allow_empty=False)
        and _bounded_text(value.get("character_id"), 128, allow_empty=False)
        and _bounded_text(value.get("reason"), 512, allow_empty=False)
        and type(value.get("title_changed")) is bool
        and type(value.get("summary_changed")) is bool
    )


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        if (
            path.is_symlink()
            or not path.is_file()
            or path.stat().st_size <= 0
            or path.stat().st_size > _MAX_ARTIFACT_BYTES
        ):
            return None
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict) or _canonical_json(value) + b"\n" != raw:
        return None
    return value


def _safe_store_root(value: str | Path) -> Path:
    if isinstance(value, Path):
        root = value
    elif isinstance(value, str) and value and value == value.strip() and "\x00" not in value:
        root = Path(value)
    else:
        raise PrimaryCurrentStateError("store_unavailable")
    if _path_has_symlink(root):
        raise PrimaryCurrentStateError("target_corrupt")
    if not root.exists() or not root.is_dir():
        raise PrimaryCurrentStateError("store_unavailable")
    return root


def _path_has_symlink(path: Path) -> bool:
    current = Path(path.anchor) if path.is_absolute() else Path()
    for part in path.parts[1:] if path.is_absolute() else path.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _canonical_json(value: Mapping[str, Any] | dict[str, Any]) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _bounded_text(value: object, limit: int, *, allow_empty: bool) -> bool:
    return (
        isinstance(value, str)
        and value == value.strip()
        and len(value) <= limit
        and (allow_empty or bool(value))
        and not bad_text(value)
        and all(ord(char) not in {0x2028, 0x2029} for char in value)
    )


def _reason_ids(values: tuple[str, ...]) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        if (
            isinstance(value, str)
            and value
            and value not in result
            and len(value) <= 128
            and len(result) < _MAX_REASONS
        ):
            result.append(value)
    return tuple(result)


__all__ = [
    "CORRECTION_ROOT",
    "PRIMARY_CURRENT_STATE_SCHEMA",
    "PrimaryCorrectionStateIndex",
    "PrimaryCurrentState",
    "PrimaryCurrentStateError",
    "empty_primary_current_state_index",
    "load_primary_current_state_index",
    "load_primary_current_target",
    "resolve_primary_current_identity",
    "resolve_primary_current_state",
]
