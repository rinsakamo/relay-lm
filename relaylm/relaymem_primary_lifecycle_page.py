"""Canonical hidden-successor Primary page representation and read-only resolution.

Active ``relaymem.primary_page.v0`` pages remain byte-for-byte compatible.  I-4C1
adds one strict hidden-only schema whose metadata is lifecycle authority; reason and
token material remain only in the runtime-private prepared artifact.
"""
from __future__ import annotations

import json
import stat
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from ._relaymem_primary_current_state_impl import PrimaryCurrentState
from ._relaymem_primary_page_writer_common import (
    HIDDEN_FRONT_MATTER_KEYS,
    HIDDEN_PAGE_SCHEMA,
    KIND_TARGET,
    PAGE_SCHEMA,
    TARGET_DIR,
    is_sha256,
    parse_page_markdown,
)
from .relaymem_primary_forget_artifact import (
    PrimaryForgetArtifactError,
    scan_forget_prepared,
)
from .relaymem_primary_recall import _load_control_state

HIDDEN_PAGE_BODY = "# Primary memory lifecycle\n\nLifecycle state: hidden.\n"
HIDDEN_PAGE_SUMMARY = "Hidden Primary memory lifecycle successor."


def build_hidden_primary_page_markdown(
    *,
    memory_kind: str,
    source_event_kind: str,
    namespace: str,
    lineage_fingerprint: str,
    successor_physical_id: str,
    memory_id: str,
    revision: int,
    prior_revision: int,
    prior_physical_id: str,
    operation_key: str,
    binding_digest: str,
) -> str:
    metadata = {
        "summary": HIDDEN_PAGE_SUMMARY,
        "schema_version": HIDDEN_PAGE_SCHEMA,
        "memory_layer": "primary",
        "memory_kind": memory_kind,
        "source_event_kind": source_event_kind,
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
        "namespace": namespace,
        "lineage_fingerprint": lineage_fingerprint,
        "idempotency_key": successor_physical_id,
        "summary_origin": "lifecycle_projection",
        "content_role": "lifecycle",
        "title": "",
        "lifecycle_state": "hidden",
        "memory_id": memory_id,
        "revision": str(revision),
        "prior_revision": str(prior_revision),
        "prior_physical_id": prior_physical_id,
        "operation_kind": "forget",
        "operation_key": operation_key,
        "binding_digest": binding_digest,
    }
    if not validate_hidden_primary_metadata(metadata):
        raise ValueError("invalid hidden lifecycle metadata")
    front_matter = "\n".join(
        f"{key}: {json.dumps(str(metadata[key]), ensure_ascii=False)}"
        for key in HIDDEN_FRONT_MATTER_KEYS
    )
    return f"---\n{front_matter}\n---\n{HIDDEN_PAGE_BODY}"


def validate_hidden_primary_metadata(
    metadata: object,
    *,
    expected_namespace: str | None = None,
    expected_memory_kind: str | None = None,
    expected_source_event_kind: str | None = None,
    expected_lineage_fingerprint: str | None = None,
    expected_physical_id: str | None = None,
) -> bool:
    if not isinstance(metadata, Mapping) or tuple(metadata.keys()) != HIDDEN_FRONT_MATTER_KEYS:
        return False
    if (
        metadata.get("schema_version") != HIDDEN_PAGE_SCHEMA
        or metadata.get("memory_layer") != "primary"
        or metadata.get("promotion_policy") != "free_to_update"
        or metadata.get("safety_scope") != "ordinary_memory"
        or metadata.get("summary_origin") != "lifecycle_projection"
        or metadata.get("content_role") != "lifecycle"
        or metadata.get("lifecycle_state") != "hidden"
        or metadata.get("operation_kind") != "forget"
        or metadata.get("summary") != HIDDEN_PAGE_SUMMARY
        or metadata.get("title") != ""
    ):
        return False
    memory_kind = metadata.get("memory_kind")
    if memory_kind not in KIND_TARGET:
        return False
    for key in (
        "lineage_fingerprint",
        "idempotency_key",
        "memory_id",
        "prior_physical_id",
        "operation_key",
        "binding_digest",
    ):
        if not is_sha256(metadata.get(key)):
            return False
    try:
        revision = int(str(metadata.get("revision")))
        prior_revision = int(str(metadata.get("prior_revision")))
    except ValueError:
        return False
    if revision < 2 or prior_revision < 1 or revision != prior_revision + 1:
        return False
    expected = {
        "namespace": expected_namespace,
        "memory_kind": expected_memory_kind,
        "source_event_kind": expected_source_event_kind,
        "lineage_fingerprint": expected_lineage_fingerprint,
        "idempotency_key": expected_physical_id,
    }
    for key, value in expected.items():
        if value is not None and metadata.get(key) != value:
            return False
    return True


def hidden_relative_path(*, memory_kind: str, physical_id: str) -> str:
    category = KIND_TARGET.get(memory_kind)
    if category is None or not is_sha256(physical_id):
        raise ValueError("invalid hidden target")
    return f"{TARGET_DIR[category]}/{physical_id}.md"


def resolve_forget_current_state(
    store_root: str | Path,
    *,
    namespace: str,
    memory_id: str,
) -> PrimaryCurrentState | None:
    """Resolve I-4C1 prepared/hidden state before the legacy correction index.

    ``None`` means no Forget evidence exists and the caller should use the I-4B
    active/correction resolver unchanged.
    """

    try:
        prepared, artifact_corrupt = scan_forget_prepared(
            store_root, memory_id=memory_id
        )
    except PrimaryForgetArtifactError:
        return _corrupt(memory_id, "primary_forget_artifact_unavailable")
    if prepared is None and not artifact_corrupt:
        return None
    if artifact_corrupt or prepared is None:
        return _corrupt(memory_id, "primary_forget_artifact_corrupt")
    if prepared.get("namespace") != namespace or prepared.get("memory_id") != memory_id:
        return _corrupt(memory_id, "primary_forget_scope_mismatch")

    root = Path(store_root)
    prior = _load_prior_active(root, prepared)
    if prior is None:
        return _corrupt(
            memory_id,
            "primary_forget_prior_invalid",
            current_physical=str(prepared.get("prior_physical_id", memory_id)),
            current_revision=int(prepared.get("prior_revision", 1)),
        )

    successor_relative = str(prepared["successor_relative_path"])
    expected_relative = hidden_relative_path(
        memory_kind=str(prepared["memory_kind"]),
        physical_id=str(prepared["successor_physical_id"]),
    )
    if successor_relative != expected_relative:
        return _corrupt(memory_id, "primary_forget_successor_path_mismatch")
    successor_path = root / PurePosixPath(successor_relative)
    if not successor_path.exists() and not successor_path.is_symlink():
        return PrimaryCurrentState(
            lifecycle_state="active",
            mutation_state="forget_prepared",
            retrieval_eligible=False,
            memory_id=memory_id,
            current_physical_id=str(prepared["prior_physical_id"]),
            current_revision=int(prepared["prior_revision"]),
            controls_valid=True,
            page_valid=True,
            bounded_reason_ids=("primary_forget_prepared",),
            title=str(prior["metadata"]["title"]),
            summary=str(prior["metadata"]["summary"]),
            metadata=dict(prior["metadata"]),
            page_digest=str(prior["digest"]),
            relative_path=str(prior["relative_path"]),
        )

    hidden = _read_page(successor_path)
    if hidden is None:
        return _corrupt(
            memory_id,
            "primary_forget_hidden_page_invalid",
            current_physical=str(prepared["successor_physical_id"]),
            current_revision=int(prepared["result_revision"]),
        )
    parsed = hidden["parsed"]
    metadata = parsed["metadata"]
    if (
        parsed.get("body") != HIDDEN_PAGE_BODY
        or hidden["digest"] != prepared["successor_expected_canonical_digest"]
        or not validate_hidden_primary_metadata(
            metadata,
            expected_namespace=namespace,
            expected_memory_kind=str(prepared["memory_kind"]),
            expected_source_event_kind=str(prepared["source_event_kind"]),
            expected_lineage_fingerprint=str(prepared["lineage_fingerprint"]),
            expected_physical_id=str(prepared["successor_physical_id"]),
        )
        or metadata.get("memory_id") != memory_id
        or metadata.get("prior_physical_id") != prepared["prior_physical_id"]
        or metadata.get("operation_key") != prepared["operation_key"]
        or metadata.get("binding_digest") != prepared["binding_digest"]
        or metadata.get("revision") != str(prepared["result_revision"])
        or metadata.get("prior_revision") != str(prepared["prior_revision"])
    ):
        return _corrupt(
            memory_id,
            "primary_forget_hidden_chain_mismatch",
            current_physical=str(prepared["successor_physical_id"]),
            current_revision=int(prepared["result_revision"]),
        )

    return PrimaryCurrentState(
        lifecycle_state="hidden",
        mutation_state="recovery_required",
        retrieval_eligible=False,
        memory_id=memory_id,
        current_physical_id=str(prepared["successor_physical_id"]),
        current_revision=int(prepared["result_revision"]),
        controls_valid=False,
        page_valid=True,
        bounded_reason_ids=(
            "primary_forget_hidden_committed",
            "primary_mutation_recovery_required",
        ),
        title="",
        summary=HIDDEN_PAGE_SUMMARY,
        metadata=dict(metadata),
        page_digest=str(hidden["digest"]),
        relative_path=successor_relative,
    )


def verify_hidden_page_against_prepared(
    store_root: str | Path, *, prepared: Mapping[str, Any]
) -> bool:
    state = resolve_forget_current_state(
        store_root,
        namespace=str(prepared["namespace"]),
        memory_id=str(prepared["memory_id"]),
    )
    return (
        state is not None
        and state.lifecycle_state == "hidden"
        and state.mutation_state == "recovery_required"
        and state.current_physical_id == prepared["successor_physical_id"]
        and state.current_revision == prepared["result_revision"]
        and state.page_digest == prepared["successor_expected_canonical_digest"]
    )


def _load_prior_active(root: Path, prepared: Mapping[str, Any]) -> dict[str, Any] | None:
    control, reasons = _load_control_state(root)
    if control is None or reasons:
        return None
    physical_id = str(prepared["prior_physical_id"])
    namespace = str(prepared["namespace"])
    index = [
        item
        for item in control["index"]
        if item.get("idempotency_key") == physical_id
        and item.get("namespace") == namespace
    ]
    log = [
        item
        for item in control["log"]
        if item.get("idempotency_key") == physical_id
        and item.get("namespace") == namespace
    ]
    if len(index) != 1 or len(log) != 1:
        return None
    relative = index[0].get("page_relative_path")
    if relative != log[0].get("page_relative_path") or not isinstance(relative, str):
        return None
    page = _read_page(root / PurePosixPath(relative))
    if page is None:
        return None
    metadata = page["parsed"]["metadata"]
    if (
        metadata.get("schema_version") != PAGE_SCHEMA
        or metadata.get("idempotency_key") != physical_id
        or metadata.get("namespace") != namespace
        or metadata.get("memory_kind") != prepared["memory_kind"]
        or metadata.get("source_event_kind") != prepared["source_event_kind"]
        or metadata.get("lineage_fingerprint") != prepared["lineage_fingerprint"]
        or page["digest"] != prepared["prior_canonical_digest"]
    ):
        return None
    return {
        "metadata": metadata,
        "digest": page["digest"],
        "relative_path": relative,
    }


def _read_page(path: Path) -> dict[str, Any] | None:
    try:
        info = path.lstat()
        if (
            stat.S_ISLNK(info.st_mode)
            or not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or info.st_size <= 0
            or info.st_size > 8192
        ):
            return None
        raw = path.read_bytes()
        markdown = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    parsed = parse_page_markdown(markdown)
    if parsed.get("valid") is not True:
        return None
    return {"parsed": parsed, "digest": sha256(raw).hexdigest(), "raw": raw}


def _corrupt(
    memory_id: str,
    reason: str,
    *,
    current_physical: str | None = None,
    current_revision: int = 1,
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
        bounded_reason_ids=(reason,),
        title="",
        summary="",
        metadata={},
        page_digest="",
        relative_path="",
    )


__all__ = [
    "HIDDEN_PAGE_BODY",
    "HIDDEN_PAGE_SCHEMA",
    "HIDDEN_PAGE_SUMMARY",
    "build_hidden_primary_page_markdown",
    "hidden_relative_path",
    "resolve_forget_current_state",
    "validate_hidden_primary_metadata",
    "verify_hidden_page_against_prepared",
]
