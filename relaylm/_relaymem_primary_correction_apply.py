"""Apply, replay, locking, and receipt ownership for Primary correction."""
from __future__ import annotations
import json, os, secrets
from contextlib import contextmanager
from datetime import datetime
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterator, Mapping
from ._relaymem_primary_page_writer_common import KIND_TARGET, is_sha256, stable_hash
from .relaymem_primary_mutation_coordinator import PrimaryMutationCoordinatorError, ensure_primary_memory_mutation_available, primary_memory_mutation_lock
from ._relaymem_primary_correction_preflight import (APPLY_RESPONSE_SCHEMA, PREPARED_SCHEMA, RECEIPT_SCHEMA, PrimaryCorrectionError, _canonical_json, _decode_token, _iso, _safe_store_root, _shared_error_code, _validate_scope_tokens, _validate_token_claims)
from ._relaymem_primary_correction_history import load_primary_correction_state, _load_current_target
from ._relaymem_primary_correction_publication import PublicationDependencies, publish_prepared_successor
from .subjective_mem_retrieval_cutover import primary_writer_decision_permits_write
_CORRECTION_ROOT = PurePosixPath("memory/mem/corrections/v0")


class ApplyDependencies:
    def __init__(self, *, publication: PublicationDependencies, utc: Callable[..., Any]):
        self.publication = publication
        self.utc = utc


def apply_primary_memory_correction(
    *, store_root: str, character_id: str, namespace: str, memory_id: str,
    expected_revision: int, operation_id: str, apply_token: str,
    primary_writer_decision: object,
    now: datetime | None = None, fault_at: str | None = None,
    _dependencies: ApplyDependencies,
) -> dict[str, Any]:
    """Apply one exact preflight candidate and converge through M3e-M3g."""
    try:
        permitted = primary_writer_decision_permits_write(primary_writer_decision)
    except Exception:  # noqa: BLE001 - malformed authority must fail closed
        permitted = False
    if not permitted:
        raise PrimaryCorrectionError("reconciliation_required")
    _validate_scope_tokens(character_id, namespace, memory_id, operation_id)
    if type(expected_revision) is not int or expected_revision < 1:
        raise PrimaryCorrectionError("invalid_request")
    if not isinstance(apply_token, str) or not apply_token or len(apply_token) > 8192:
        raise PrimaryCorrectionError("token_invalid")
    root = _safe_store_root(store_root)
    token_digest = sha256(apply_token.encode("utf-8")).hexdigest()
    operation_key = _operation_key(operation_id)
    with _memory_lock(root, memory_id):
        replay, prepared = _load_or_prepare_operation(
            root=root, character_id=character_id, namespace=namespace,
            memory_id=memory_id, expected_revision=expected_revision,
            operation_id=operation_id, operation_key=operation_key,
            apply_token=apply_token, token_digest=token_digest, now=now,
            dependencies=_dependencies,
        )
        if replay is not None:
            return _public_apply_result(replay, idempotent_replay=True)
        assert prepared is not None
        return _publish_and_finalize(
            root=root, memory_id=memory_id, operation_key=operation_key,
            prepared=prepared, now=now, fault_at=fault_at,
            dependencies=_dependencies,
        )


def _load_or_prepare_operation(
    *, root: Path, character_id: str, namespace: str, memory_id: str,
    expected_revision: int, operation_id: str, operation_key: str,
    apply_token: str, token_digest: str, now: datetime | None,
    dependencies: ApplyDependencies,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    replay = _read_operation_receipt(root, memory_id, operation_key, "applied")
    if replay is not None:
        _validate_replay(replay, character_id=character_id, namespace=namespace,
            memory_id=memory_id, expected_revision=expected_revision,
            operation_id=operation_id, token_digest=token_digest)
        return replay, None
    claims = _decode_token(apply_token)
    _validate_token_claims(claims, character_id=character_id, namespace=namespace,
        memory_id=memory_id, expected_revision=expected_revision,
        operation_id=operation_id, now=dependencies.utc(now))
    prepared = _read_operation_receipt(root, memory_id, operation_key, "prepared")
    if prepared is not None:
        _validate_prepared_replay(prepared, claims=claims, token_digest=token_digest)
        return None, prepared
    _ensure_no_other_pending(root, memory_id, operation_key,
        operation_id=operation_id, binding_digest=str(claims["candidate_digest"]))
    state = load_primary_correction_state(root, namespace=namespace)
    target = _load_current_target(root, namespace=namespace,
        logical_memory_id=memory_id, expected_revision=expected_revision, state=state)
    if target["physical_id"] != claims["current_physical_id"]:
        raise PrimaryCorrectionError("stale_revision")
    prepared = _build_prepared_receipt(
        character_id=character_id, namespace=namespace, memory_id=memory_id,
        operation_id=operation_id, operation_key=operation_key,
        token_digest=token_digest, claims=claims, target=target,
        requested_at=str(claims["issued_at"]), prepared_at=_iso(dependencies.utc(now)))
    _write_immutable_json(_operation_path(root, memory_id, operation_key, "prepared"), prepared)
    return None, prepared


def _publish_and_finalize(
    *, root: Path, memory_id: str, operation_key: str,
    prepared: Mapping[str, Any], now: datetime | None, fault_at: str | None,
    dependencies: ApplyDependencies,
) -> dict[str, Any]:
    if fault_at == "after_audit_prepared":
        raise PrimaryCorrectionError("reconciliation_required")
    result = publish_prepared_successor(
        root, prepared, fault_at=fault_at, dependencies=dependencies.publication)
    applied = build_applied_receipt(
        prepared=prepared, result=result, applied_at=_iso(dependencies.utc(now)))
    _write_immutable_json(_operation_path(root, memory_id, operation_key, "applied"), applied)
    if fault_at == "after_audit_finalization":
        raise PrimaryCorrectionError("response_lost")
    return _public_apply_result(applied, idempotent_replay=False)


def build_applied_receipt(*, prepared: Mapping[str, Any], result: Mapping[str, Any], applied_at: str) -> dict[str, Any]:
    return {
        "schema_version": RECEIPT_SCHEMA, "runtime_private": True, "content_included": False,
        "operation_id": str(prepared["operation_id"]), "operation_key": str(prepared["operation_key"]),
        "correction_id": str(prepared["correction_id"]), "character_id": str(prepared["character_id"]),
        "namespace": str(prepared["namespace"]), "memory_id": str(prepared["memory_id"]),
        "prior_revision": int(prepared["prior_revision"]), "result_revision": int(prepared["result_revision"]),
        "prior_physical_id": str(prepared["prior_physical_id"]), "result_physical_id": str(result["result_physical_id"]),
        "prior_canonical_digest": str(prepared["prior_canonical_digest"]), "result_canonical_digest": str(result["result_canonical_digest"]),
        "candidate_digest": str(prepared["candidate_digest"]), "token_digest": str(prepared["token_digest"]),
        "requested_at": str(prepared["requested_at"]), "applied_at": applied_at, "reason": str(prepared["reason"]),
        "status": "reconciled", "title_changed": bool(prepared["title_changed"]),
        "summary_changed": bool(prepared["summary_changed"]), "recovery_required": False,
    }


def _build_prepared_receipt(
    *,
    character_id: str,
    namespace: str,
    memory_id: str,
    operation_id: str,
    operation_key: str,
    token_digest: str,
    claims: Mapping[str, Any],
    target: Mapping[str, Any],
    requested_at: str,
    prepared_at: str,
) -> dict[str, Any]:
    successor_candidate_id = stable_hash(
        (
            "relaymem-primary-correction-candidate-v0",
            memory_id,
            operation_id,
            str(claims["candidate_digest"]),
            str(claims["candidate_revision"]),
        )
    )
    successor_identity = stable_hash(
        (
            "relaymem-primary-write-preflight-v0",
            namespace,
            str(target["metadata"]["source_event_kind"]),
            str(target["metadata"]["lineage_fingerprint"]),
            successor_candidate_id,
            str(target["metadata"]["source_event_kind"]),
            "primary",
            str(target["metadata"]["memory_kind"]),
            "free_to_update",
        )
    )
    return {
        "schema_version": PREPARED_SCHEMA,
        "runtime_private": True,
        "content_included": True,
        "operation_id": operation_id,
        "operation_key": operation_key,
        "correction_id": stable_hash(("relaymem-primary-correction-v0", memory_id, operation_id)),
        "character_id": character_id,
        "namespace": namespace,
        "memory_id": memory_id,
        "prior_revision": int(claims["current_revision"]),
        "result_revision": int(claims["candidate_revision"]),
        "prior_physical_id": str(target["physical_id"]),
        "successor_physical_id": successor_identity,
        "successor_candidate_id": successor_candidate_id,
        "source_event_kind": str(target["metadata"]["source_event_kind"]),
        "memory_kind": str(target["metadata"]["memory_kind"]),
        "lineage_fingerprint": str(target["metadata"]["lineage_fingerprint"]),
        "prior_canonical_digest": str(target["page_digest"]),
        "candidate_digest": str(claims["candidate_digest"]),
        "token_digest": token_digest,
        "corrected_title": str(claims["corrected_title"]),
        "corrected_summary": str(claims["corrected_summary"]),
        "reason": str(claims["reason"]),
        "title_changed": str(claims["corrected_title"]) != str(target["metadata"]["title"]),
        "summary_changed": str(claims["corrected_summary"]) != str(target["metadata"]["summary"]),
        "requested_at": requested_at,
        "prepared_at": prepared_at,
        "status": "prepared",
        "recovery_required": True,
    }


def _validate_replay(
    receipt: Mapping[str, Any],
    *,
    character_id: str,
    namespace: str,
    memory_id: str,
    expected_revision: int,
    operation_id: str,
    token_digest: str,
) -> None:
    expected = {
        "character_id": character_id,
        "namespace": namespace,
        "memory_id": memory_id,
        "prior_revision": expected_revision,
        "operation_id": operation_id,
        "token_digest": token_digest,
    }
    if any(receipt.get(key) != value for key, value in expected.items()):
        raise PrimaryCorrectionError("operation_conflict")


def _validate_prepared_replay(
    prepared: Mapping[str, Any], *, claims: Mapping[str, Any], token_digest: str
) -> None:
    expected = {
        "operation_id": claims["operation_id"],
        "memory_id": claims["memory_id"],
        "prior_revision": claims["current_revision"],
        "result_revision": claims["candidate_revision"],
        "candidate_digest": claims["candidate_digest"],
        "token_digest": token_digest,
    }
    if any(prepared.get(key) != value for key, value in expected.items()):
        raise PrimaryCorrectionError("operation_conflict")


def _public_apply_result(receipt: Mapping[str, Any], *, idempotent_replay: bool) -> dict[str, Any]:
    return {
        "schema": APPLY_RESPONSE_SCHEMA,
        "status": "applied",
        "memory_id": str(receipt["memory_id"]),
        "prior_revision": int(receipt["prior_revision"]),
        "result_revision": int(receipt["result_revision"]),
        "correction_id": str(receipt["correction_id"]),
        "reconciled": receipt.get("status") == "reconciled",
        "recovery_required": bool(receipt.get("recovery_required")),
        "idempotent_replay": idempotent_replay,
        "applied_at": str(receipt["applied_at"]),
    }


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
        and value.get("schema_version") == PREPARED_SCHEMA
        and value.get("runtime_private") is True
        and value.get("content_included") is True
        and value.get("namespace") == namespace
        and value.get("memory_id") == memory_id
        and value.get("status") == "prepared"
        and value.get("recovery_required") is True
        and type(value.get("prior_revision")) is int
        and type(value.get("result_revision")) is int
        and value.get("result_revision") == value.get("prior_revision") + 1
        and all(
            is_sha256(value.get(key))
            for key in (
                "operation_key", "correction_id", "prior_physical_id", "successor_physical_id",
                "successor_candidate_id", "lineage_fingerprint", "prior_canonical_digest",
                "candidate_digest", "token_digest",
            )
        )
        and isinstance(value.get("operation_id"), str)
        and isinstance(value.get("character_id"), str)
        and value.get("memory_kind") in KIND_TARGET
        and isinstance(value.get("source_event_kind"), str)
        and isinstance(value.get("corrected_title"), str)
        and isinstance(value.get("corrected_summary"), str)
        and isinstance(value.get("reason"), str)
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
        "prior_canonical_digest", "result_canonical_digest", "candidate_digest", "token_digest",
        "requested_at", "applied_at", "reason", "status", "title_changed", "summary_changed",
        "recovery_required",
    }
    return (
        set(value) == required
        and value.get("schema_version") == RECEIPT_SCHEMA
        and value.get("runtime_private") is True
        and value.get("content_included") is False
        and value.get("namespace") == namespace
        and value.get("memory_id") == memory_id
        and value.get("status") == "reconciled"
        and value.get("recovery_required") is False
        and type(value.get("prior_revision")) is int
        and type(value.get("result_revision")) is int
        and value.get("result_revision") == value.get("prior_revision") + 1
        and all(
            is_sha256(value.get(key))
            for key in (
                "operation_key", "correction_id", "prior_physical_id", "result_physical_id",
                "prior_canonical_digest", "result_canonical_digest", "candidate_digest", "token_digest",
            )
        )
        and isinstance(value.get("operation_id"), str)
        and isinstance(value.get("character_id"), str)
        and isinstance(value.get("reason"), str)
        and type(value.get("title_changed")) is bool
        and type(value.get("summary_changed")) is bool
    )


def _read_operation_receipt(
    root: Path, memory_id: str, operation_key: str, state: str
) -> dict[str, Any] | None:
    path = _operation_path(root, memory_id, operation_key, state)
    if not path.exists():
        return None
    if path.is_symlink() or not path.is_file():
        raise PrimaryCorrectionError("target_corrupt")
    value = _read_json(path)
    validator = _valid_applied if state == "applied" else _valid_prepared
    namespace = value.get("namespace") if isinstance(value, dict) else ""
    if not validator(value, namespace=str(namespace), memory_id=memory_id):
        raise PrimaryCorrectionError("target_corrupt")
    return value


def _ensure_no_other_pending(
    root: Path,
    memory_id: str,
    operation_key: str,
    *,
    operation_id: str,
    binding_digest: str,
) -> None:
    del operation_key
    try:
        ensure_primary_memory_mutation_available(
            root,
            memory_id=memory_id,
            operation_kind="correct",
            operation_id=operation_id,
            binding_digest=binding_digest,
        )
    except PrimaryMutationCoordinatorError as exc:
        raise PrimaryCorrectionError(_shared_error_code(exc.code)) from exc


def _operation_path(root: Path, memory_id: str, operation_key: str, state: str) -> Path:
    if not is_sha256(memory_id) or not is_sha256(operation_key) or state not in {"prepared", "applied"}:
        raise PrimaryCorrectionError("invalid_request")
    memory_dir = root / _CORRECTION_ROOT / memory_id
    _ensure_private_dir(root, memory_dir)
    return memory_dir / f"{operation_key}.{state}.json"


def _operation_key(operation_id: str) -> str:
    return stable_hash(("relaymem-primary-correction-operation-v0", operation_id))


@contextmanager
def _memory_lock(root: Path, memory_id: str) -> Iterator[None]:
    try:
        with primary_memory_mutation_lock(root, memory_id):
            yield
    except PrimaryMutationCoordinatorError as exc:
        raise PrimaryCorrectionError(_shared_error_code(exc.code)) from exc


def _write_immutable_json(path: Path, value: Mapping[str, Any]) -> None:
    payload = _canonical_json(value) + b"\n"
    if path.exists():
        existing = _read_json(path)
        if existing == dict(value):
            return
        raise PrimaryCorrectionError("operation_conflict")
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        descriptor = os.open(temporary, flags, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except FileExistsError:
        existing = _read_json(path) if path.exists() else None
        if existing != dict(value):
            raise PrimaryCorrectionError("operation_conflict") from None
    except OSError as exc:
        raise PrimaryCorrectionError("store_unavailable") from exc
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 32768:
            return None
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict) or _canonical_json(value) + b"\n" != raw:
        return None
    return value


def _ensure_private_dir(root: Path, directory: Path) -> None:
    try:
        directory.relative_to(root)
    except ValueError:
        raise PrimaryCorrectionError("target_corrupt") from None
    current = root
    for part in directory.relative_to(root).parts:
        current = current / part
        if current.is_symlink():
            raise PrimaryCorrectionError("target_corrupt")
        if current.exists() and not current.is_dir():
            raise PrimaryCorrectionError("target_corrupt")
        current.mkdir(mode=0o700, exist_ok=True)
