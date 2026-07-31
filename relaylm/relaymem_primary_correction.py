"""Auditable Primary MEM correction through bounded behavior-preserving owners."""
from __future__ import annotations

import base64
import hmac
import json
import os
import secrets
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any, Iterator, Mapping, Sequence

from ._relaymem_primary_page_writer_common import (
    FRONT_MATTER_KEYS, KIND_TARGET, MAX_PAGE_BYTES, MAX_SUMMARY, MAX_TITLE,
    TARGET_DIR, bad_text, is_sha256, parse_page_markdown, stable_hash,
)
from .relaymem_primary_index_log_apply import apply_relaymem_primary_index_log_reconciliation
from .relaymem_primary_index_log_reconciliation import build_relaymem_primary_index_log_reconciliation_preflight
from .relaymem_primary_page_candidate import build_relaymem_governed_experience_summary, build_relaymem_primary_page_candidate_dry_run
from .relaymem_primary_page_writer import apply_relaymem_primary_page_write
from .relaymem_primary_recall import _load_control_state, _load_validated_page
from .relaymem_primary_current_state import (
    PrimaryCorrectionStateIndex, PrimaryCurrentStateError,
    empty_primary_current_state_index, load_primary_current_state_index,
    load_primary_current_target, resolve_primary_current_identity,
)
from .relaymem_primary_mutation_coordinator import (
    PrimaryMutationCoordinatorError, ensure_primary_memory_mutation_available,
    primary_memory_mutation_lock,
)
from .relaymem_primary_write_preflight import build_relaymem_primary_write_preflight_dry_run
from .relaymem_primary_writer_handoff import build_relaymem_primary_writer_handoff_preflight
from ._relaymem_primary_correction_preflight import (
    APPLY_REQUEST_SCHEMA, APPLY_RESPONSE_SCHEMA, HISTORY_SCHEMA,
    PREFLIGHT_REQUEST_SCHEMA, PREFLIGHT_RESPONSE_SCHEMA, PREPARED_SCHEMA,
    RECEIPT_SCHEMA, PreflightDependencies as _PreflightDependencies, PrimaryCorrectionError, _MAX_OPERATION_ID, _MAX_REASON,
    _TOKEN_SECRET, _TOKEN_TTL, _b64, _candidate_digest, _canonical_json,
    _decode_token, _encode_token, _iso, _path_has_symlink, _safe_store_root,
    _semantic_text, _shared_error_code, _unb64, _unsafe_text, _utc,
    _validate_scope_tokens, _validate_token_claims,
)
from ._relaymem_primary_correction_history import (
    CorrectionState, _bounded, _empty_state, _load_current_target,
    _load_scoped_control_state, list_primary_memory_corrections,
    load_primary_correction_state, resolve_primary_correction_identity,
)
from ._relaymem_primary_correction_publication import PublicationDependencies as _PublicationDependencies, publish_prepared_successor as _publish_prepared_successor
from ._relaymem_primary_correction_apply import (
    ApplyDependencies as _ApplyDependencies,    _build_prepared_receipt, _ensure_no_other_pending, _ensure_private_dir,
    _memory_lock, _operation_key, _operation_path, _public_apply_result,
    _read_json, _read_operation_receipt, _valid_applied, _valid_prepared,
    _validate_prepared_replay, _validate_replay, _write_immutable_json,
)
from ._relaymem_primary_correction_apply import apply_primary_memory_correction as _apply
from ._relaymem_primary_correction_recovery import recover_primary_memory_corrections as _recover
from ._relaymem_primary_correction_preflight import preflight_primary_memory_correction as _preflight

_CORRECTION_ROOT = PurePosixPath("memory/mem/corrections/v0")


def _publication_dependencies() -> _PublicationDependencies:
    return _PublicationDependencies(apply_primary_page_write=apply_relaymem_primary_page_write)


def preflight_primary_memory_correction(
    *, store_root: str, character_id: str, namespace: str, memory_id: str,
    expected_revision: int, corrected_title: str, corrected_summary: str,
    reason: str, operation_id: str, now: datetime | None = None,
) -> dict[str, Any]:
    return _preflight(
        store_root=store_root, character_id=character_id, namespace=namespace,
        memory_id=memory_id, expected_revision=expected_revision,
        corrected_title=corrected_title, corrected_summary=corrected_summary,
        reason=reason, operation_id=operation_id, now=now,
        _dependencies=_PreflightDependencies(
            load_state=load_primary_correction_state, load_target=_load_current_target
        ),
    )


def apply_primary_memory_correction(
    *,
    store_root: str,
    character_id: str,
    namespace: str,
    memory_id: str,
    expected_revision: int,
    operation_id: str,
    apply_token: str,
    now: datetime | None = None,
    fault_at: str | None = None,
) -> dict[str, Any]:
    return _apply(
        store_root=store_root, character_id=character_id, namespace=namespace,
        memory_id=memory_id, expected_revision=expected_revision,
        operation_id=operation_id, apply_token=apply_token, now=now,
        fault_at=fault_at, _dependencies=_ApplyDependencies(
            publication=_publication_dependencies(), utc=_utc
        ),
    )


def recover_primary_memory_corrections(
    *, store_root: str, namespace: str
) -> dict[str, int]:
    return _recover(
        store_root=store_root, namespace=namespace,
        _publication_dependencies=_publication_dependencies(),
    )


__all__ = [
    "APPLY_REQUEST_SCHEMA", "APPLY_RESPONSE_SCHEMA", "HISTORY_SCHEMA",
    "PREFLIGHT_REQUEST_SCHEMA", "PREFLIGHT_RESPONSE_SCHEMA",
    "PrimaryCorrectionError", "apply_primary_memory_correction",
    "list_primary_memory_corrections", "load_primary_correction_state",
    "preflight_primary_memory_correction", "recover_primary_memory_corrections",
    "resolve_primary_correction_identity",
]
