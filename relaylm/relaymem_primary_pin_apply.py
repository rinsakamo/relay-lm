"""Phase I-5B durable Primary MEM Pin / Unpin apply authority."""
from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from ._relaymem_primary_page_writer_common import is_sha256, stable_hash
from .relaymem_primary_current_state import PrimaryCurrentStateError, resolve_primary_current_state
from .relaymem_primary_mutation_coordinator import (
    PrimaryMutationCoordinatorError,
    inspect_primary_memory_operations,
    primary_memory_mutation_lock,
)
from .relaymem_primary_pin import (
    PIN_HISTORY_SCHEMA,
    PIN_PREFLIGHT_RESPONSE_SCHEMA,
    UNPIN_HISTORY_SCHEMA,
    UNPIN_PREFLIGHT_RESPONSE_SCHEMA,
    PrimaryPinError,
    _map_error as _contract_map_error,
    preflight_primary_memory_pin,
    preflight_primary_memory_unpin,
    validate_primary_memory_pin_token,
    validate_primary_memory_unpin_token,
)

PIN_RECEIPT_SCHEMA = "relaylm.mem.primary_pin_receipt.v0"
PIN_STATE_SCHEMA = "relaylm.mem.primary_pin_state.v0"
PIN_APPLY_RESPONSE_SCHEMA = "relaylm.lab.memory_pin_apply.v0"
UNPIN_APPLY_RESPONSE_SCHEMA = "relaylm.lab.memory_unpin_apply.v0"
PIN_ROOT = PurePosixPath("memory/mem/pins/v0")
_MAX_ARTIFACT_BYTES = 32_768
_MAX_HISTORY_ITEMS = 50


@dataclass(frozen=True, repr=False)
class PrimaryPinApplyResult:
    status: str
    operation_kind: str
    memory_id: str
    current_revision: int
    current_lifecycle_state: str
    current_mutation_state: str
    prior_pin_state: str
    target_pin_state: str
    retrieval_eligible: bool
    priority_hint_enabled: bool
    idempotent_replay: bool
    effect_applied: bool
    receipt_id: str

    def to_log_dict(self) -> dict[str, Any]:
        return {
            "schema": PIN_APPLY_RESPONSE_SCHEMA if self.operation_kind == "pin" else UNPIN_APPLY_RESPONSE_SCHEMA,
            "status": self.status,
            "operation_kind": self.operation_kind,
            "memory_id": self.memory_id,
            "current_revision": self.current_revision,
            "current_lifecycle_state": self.current_lifecycle_state,
            "current_mutation_state": self.current_mutation_state,
            "prior_pin_state": self.prior_pin_state,
            "target_pin_state": self.target_pin_state,
            "retrieval_eligible": self.retrieval_eligible,
            "ordinary_retrieval_excluded": False,
            "priority_hint_enabled": self.priority_hint_enabled,
            "semantic_content_changed": False,
            "physical_deletion": False,
            "audit_evidence_retained": True,
            "idempotent_replay": self.idempotent_replay,
            "effect_applied": self.effect_applied,
            "receipt_id": self.receipt_id,
            "content_included": False,
            "path_included": False,
            "physical_id_included": False,
            "reason_included": False,
            "token_included": False,
        }


@dataclass(frozen=True, repr=False)
class PrimaryPinStateIndex:
    pinned_memory_ids: frozenset[str]
    corrupt_memory_ids: frozenset[str]
    bounded_reason_ids: tuple[str, ...]

    def is_pinned(self, memory_id: str) -> bool:
        return memory_id in self.pinned_memory_ids and memory_id not in self.corrupt_memory_ids

    def to_log_dict(self) -> dict[str, Any]:
        return {
            "schema": "relaylm.mem.primary_pin_state_index.v0",
            "pinned_count": len(self.pinned_memory_ids),
            "corrupt_count": len(self.corrupt_memory_ids),
            "bounded_reason_ids": list(self.bounded_reason_ids),
            "content_included": False,
            "path_included": False,
            "operation_id_included": False,
        }


def preflight_primary_memory_pin_apply(**kwargs: Any) -> dict[str, Any]:
    return _preflight_operation("pin", **kwargs)


def preflight_primary_memory_unpin_apply(**kwargs: Any) -> dict[str, Any]:
    return _preflight_operation("unpin", **kwargs)


def apply_primary_memory_pin(**kwargs: Any) -> PrimaryPinApplyResult:
    return _apply_operation("pin", **kwargs)


def apply_primary_memory_unpin(**kwargs: Any) -> PrimaryPinApplyResult:
    return _apply_operation("unpin", **kwargs)


def get_primary_memory_pin_state(store_root: str | Path, *, namespace: str, memory_id: str) -> str:
    root = _safe_root(store_root)
    _validate_namespace(namespace)
    _validate_memory_id(memory_id)
    state = _read_state(root, namespace=namespace, memory_id=memory_id)
    if state is not None:
        return str(state["current_pin_state"])
    receipts = _read_receipts(root, namespace=namespace, memory_id=memory_id)
    if receipts.corrupt:
        raise PrimaryPinError("target_corrupt")
    return str(receipts.items[-1]["target_pin_state"]) if receipts.items else "unpinned"


def load_primary_pin_state_index(store_root: str | Path, *, namespace: str) -> PrimaryPinStateIndex:
    root = _safe_root(store_root)
    _validate_namespace(namespace)
    base = root / PIN_ROOT
    if not base.exists() and not base.is_symlink():
        return PrimaryPinStateIndex(frozenset(), frozenset(), ())
    if base.is_symlink() or not base.is_dir():
        return PrimaryPinStateIndex(frozenset(), frozenset({"*"}), ("primary_pin_root_invalid",))
    pinned: set[str] = set()
    corrupt: set[str] = set()
    reasons: list[str] = []
    try:
        entries = sorted(base.iterdir(), key=lambda item: item.name)
    except OSError:
        return PrimaryPinStateIndex(frozenset(), frozenset({"*"}), ("primary_pin_root_unreadable",))
    for memory_dir in entries:
        memory_id = memory_dir.name
        if not is_sha256(memory_id) or memory_dir.is_symlink() or not memory_dir.is_dir():
            corrupt.add(memory_id if is_sha256(memory_id) else "*")
            reasons.append("primary_pin_memory_dir_invalid")
            continue
        try:
            if get_primary_memory_pin_state(root, namespace=namespace, memory_id=memory_id) == "pinned":
                pinned.add(memory_id)
        except PrimaryPinError:
            corrupt.add(memory_id)
            reasons.append("primary_pin_state_invalid")
    return PrimaryPinStateIndex(frozenset(pinned), frozenset(corrupt), tuple(dict.fromkeys(reasons))[:32])


def list_primary_memory_pin_history(*, store_root: str, namespace: str, memory_id: str) -> dict[str, Any]:
    return _list_history("pin", store_root=store_root, namespace=namespace, memory_id=memory_id)


def list_primary_memory_unpin_history(*, store_root: str, namespace: str, memory_id: str) -> dict[str, Any]:
    return _list_history("unpin", store_root=store_root, namespace=namespace, memory_id=memory_id)


def _preflight_operation(operation_kind: str, **kwargs: Any) -> dict[str, Any]:
    state = get_primary_memory_pin_state(kwargs["store_root"], namespace=kwargs["namespace"], memory_id=kwargs["memory_id"])
    target = _target_state(operation_kind)
    if state == target:
        current = _resolve_current(kwargs["store_root"], namespace=kwargs["namespace"], memory_id=kwargs["memory_id"], expected_revision=kwargs["expected_revision"])
        _require_active_current(current)
        return {
            "schema": PIN_PREFLIGHT_RESPONSE_SCHEMA if operation_kind == "pin" else UNPIN_PREFLIGHT_RESPONSE_SCHEMA,
            "status": "already_pinned" if operation_kind == "pin" else "already_unpinned",
            "operation_kind": operation_kind,
            "read_only": True,
            "memory_id": kwargs["memory_id"],
            "current_revision": current.current_revision,
            "current_lifecycle_state": "active",
            "current_mutation_state": "none",
            "current_pin_state": state,
            "target_pin_state": target,
            "pin_state_contract_only": False,
            "effects": _effects(operation_kind),
            "apply_token": None,
            "expires_at": None,
        }
    result = preflight_primary_memory_pin(**kwargs) if operation_kind == "pin" else preflight_primary_memory_unpin(**kwargs)
    result = dict(result)
    result["current_pin_state"] = state
    result["target_pin_state"] = target
    result["pin_state_contract_only"] = False
    return result


def _apply_operation(operation_kind: str, **kwargs: Any) -> PrimaryPinApplyResult:
    _validate_operation_kind(operation_kind)
    _validate_request(kwargs)
    root = _safe_root(kwargs["store_root"])
    namespace = kwargs["namespace"]
    memory_id = kwargs["memory_id"]
    operation_id = kwargs["operation_id"]
    reason = kwargs["reason"]
    token = kwargs["apply_token"]
    try:
        with primary_memory_mutation_lock(root, memory_id):
            existing = _lookup_receipt(root, namespace=namespace, memory_id=memory_id, operation_id=operation_id)
            if existing is not None:
                _publish_state(root, existing)
                return _result_from_receipt(existing, idempotent_replay=True)
            token_validation = _validate_token(operation_kind, **kwargs)
            current = _resolve_current(root, namespace=namespace, memory_id=memory_id, expected_revision=kwargs["expected_revision"])
            _require_active_current(current)
            _ensure_shared_fence(root, memory_id=memory_id, operation_id=operation_id)
            prior_pin_state = get_primary_memory_pin_state(root, namespace=namespace, memory_id=memory_id)
            target_pin_state = _target_state(operation_kind)
            effect_applied = prior_pin_state != target_pin_state
            status = "applied" if effect_applied else "already_pinned" if operation_kind == "pin" else "already_unpinned"
            receipt = _build_receipt(
                operation_kind=operation_kind,
                status=status,
                character_id=kwargs["character_id"],
                namespace=namespace,
                memory_id=memory_id,
                current=current,
                prior_pin_state=prior_pin_state,
                target_pin_state=target_pin_state,
                operation_id=operation_id,
                reason_digest=sha256(reason.encode("utf-8")).hexdigest(),
                token_digest=sha256(token.encode("utf-8")).hexdigest(),
                requested_at=str(token_validation["expires_at"]),
                applied_at=_iso(_utc(kwargs.get("now"))),
                effect_applied=effect_applied,
            )
            _publish_receipt(root, receipt)
            _publish_state(root, receipt)
            return _result_from_receipt(receipt, idempotent_replay=False)
    except PrimaryPinError:
        raise
    except PrimaryCurrentStateError as exc:
        raise PrimaryPinError(_contract_map_error(exc.code)) from exc
    except PrimaryMutationCoordinatorError as exc:
        raise PrimaryPinError(_contract_map_error(exc.code)) from exc


def _list_history(operation_kind: str, *, store_root: str, namespace: str, memory_id: str) -> dict[str, Any]:
    _validate_operation_kind(operation_kind)
    root = _safe_root(store_root)
    current = _resolve_current(root, namespace=namespace, memory_id=memory_id, expected_revision=None)
    if current.mutation_state == "corrupt" or not current.controls_valid or not current.page_valid:
        raise PrimaryPinError("target_corrupt")
    receipts = _read_receipts(root, namespace=namespace, memory_id=memory_id)
    if receipts.corrupt:
        raise PrimaryPinError("target_corrupt")
    items = [_public_history_item(item) for item in receipts.items if item.get("operation_kind") == operation_kind][-_MAX_HISTORY_ITEMS:]
    count_name = "pin_count" if operation_kind == "pin" else "unpin_count"
    return {
        "schema": PIN_HISTORY_SCHEMA if operation_kind == "pin" else UNPIN_HISTORY_SCHEMA,
        "source": "relaylm_runtime",
        "read_only": True,
        "memory_id": memory_id,
        "current_revision": current.current_revision,
        "current_lifecycle_state": current.lifecycle_state,
        "current_pin_state": get_primary_memory_pin_state(root, namespace=namespace, memory_id=memory_id),
        "pin_state_contract_only": False,
        count_name: len(items),
        "items": items,
    }


def _validate_token(operation_kind: str, **kwargs: Any) -> dict[str, Any]:
    return validate_primary_memory_pin_token(**kwargs) if operation_kind == "pin" else validate_primary_memory_unpin_token(**kwargs)


def _build_receipt(**kwargs: Any) -> dict[str, Any]:
    operation_kind = kwargs["operation_kind"]
    operation_id = kwargs["operation_id"]
    memory_id = kwargs["memory_id"]
    current = kwargs["current"]
    operation_key = stable_hash(("relaymem-primary-pin-operation-v0", operation_kind, operation_id))
    binding_digest = stable_hash(("relaymem-primary-pin-binding-v0", operation_kind, operation_id, memory_id, str(current.current_physical_id), str(current.current_revision), kwargs["target_pin_state"], kwargs["reason_digest"]))
    receipt_id = stable_hash(("relaymem-primary-pin-receipt-v0", operation_key, binding_digest))
    return {
        "schema_version": PIN_RECEIPT_SCHEMA,
        "runtime_private": True,
        "content_included": False,
        "operation_kind": operation_kind,
        "operation_id": operation_id,
        "operation_key": operation_key,
        "receipt_id": receipt_id,
        "binding_digest": binding_digest,
        "character_id": kwargs["character_id"],
        "namespace": kwargs["namespace"],
        "memory_id": memory_id,
        "current_physical_id": str(current.current_physical_id),
        "current_revision": int(current.current_revision),
        "current_lifecycle_state": "active",
        "current_mutation_state": "none",
        "prior_pin_state": kwargs["prior_pin_state"],
        "target_pin_state": kwargs["target_pin_state"],
        "reason_digest": kwargs["reason_digest"],
        "token_digest": kwargs["token_digest"],
        "requested_at": kwargs["requested_at"],
        "applied_at": kwargs["applied_at"],
        "status": kwargs["status"],
        "effect_applied": kwargs["effect_applied"],
        "ordinary_retrieval_excluded": False,
        "priority_hint_enabled": kwargs["target_pin_state"] == "pinned",
        "semantic_content_changed": False,
        "physical_deletion": False,
        "audit_evidence_retained": True,
    }


def _publish_receipt(root: Path, receipt: Mapping[str, Any]) -> None:
    directory = root / PIN_ROOT / str(receipt["memory_id"])
    _ensure_private_dir(root, directory)
    _atomic_write_json(directory / f"{receipt['operation_key']}.pin.json", receipt, create_only=True)


def _publish_state(root: Path, receipt: Mapping[str, Any]) -> None:
    directory = root / PIN_ROOT / str(receipt["memory_id"])
    _ensure_private_dir(root, directory)
    state = {
        "schema_version": PIN_STATE_SCHEMA,
        "runtime_private": True,
        "content_included": False,
        "namespace": receipt["namespace"],
        "memory_id": receipt["memory_id"],
        "current_pin_state": receipt["target_pin_state"],
        "current_revision": receipt["current_revision"],
        "last_operation_kind": receipt["operation_kind"],
        "last_status": receipt["status"],
        "last_receipt_id": receipt["receipt_id"],
        "updated_at": receipt["applied_at"],
        "ordinary_retrieval_excluded": False,
        "priority_hint_enabled": receipt["target_pin_state"] == "pinned",
    }
    _atomic_write_json(directory / "state.json", state, create_only=False)


@dataclass(frozen=True)
class _ReceiptReadResult:
    items: tuple[dict[str, Any], ...]
    corrupt: bool
    reason_ids: tuple[str, ...]


def _read_receipts(root: Path, *, namespace: str, memory_id: str) -> _ReceiptReadResult:
    directory = root / PIN_ROOT / memory_id
    if not directory.exists() and not directory.is_symlink():
        return _ReceiptReadResult((), False, ())
    if directory.is_symlink() or not directory.is_dir():
        return _ReceiptReadResult((), True, ("primary_pin_dir_invalid",))
    items: list[dict[str, Any]] = []
    reasons: list[str] = []
    corrupt = False
    seen: dict[str, tuple[str, str]] = {}
    for path in sorted(directory.iterdir(), key=lambda item: item.name):
        if path.name == "state.json":
            continue
        value = _read_json(path)
        if value is None or not _valid_receipt(value, namespace=namespace, memory_id=memory_id) or path.name != f"{value['operation_key']}.pin.json":
            corrupt = True
            reasons.append("primary_pin_receipt_invalid")
            continue
        meaning = (str(value["operation_kind"]), str(value["binding_digest"]))
        if str(value["operation_id"]) in seen and seen[str(value["operation_id"])] != meaning:
            corrupt = True
            reasons.append("primary_pin_operation_id_conflict")
            continue
        seen[str(value["operation_id"])] = meaning
        items.append(value)
    items.sort(key=lambda item: (str(item["applied_at"]), str(item["operation_key"])))
    return _ReceiptReadResult(tuple(items), corrupt, tuple(dict.fromkeys(reasons))[:32])


def _lookup_receipt(root: Path, *, namespace: str, memory_id: str, operation_id: str) -> dict[str, Any] | None:
    receipts = _read_receipts(root, namespace=namespace, memory_id=memory_id)
    if receipts.corrupt:
        raise PrimaryPinError("target_corrupt")
    matches = [item for item in receipts.items if item.get("operation_id") == operation_id]
    if len(matches) > 1:
        raise PrimaryPinError("operation_conflict")
    return matches[0] if matches else None


def _read_state(root: Path, *, namespace: str, memory_id: str) -> dict[str, Any] | None:
    value = _read_json(root / PIN_ROOT / memory_id / "state.json")
    return value if _valid_state(value, namespace=namespace, memory_id=memory_id) else None


def _ensure_shared_fence(root: Path, *, memory_id: str, operation_id: str) -> None:
    inspection = inspect_primary_memory_operations(root, memory_id=memory_id)
    if inspection.corrupt:
        raise PrimaryPinError("target_corrupt")
    if inspection.pending or any(item.operation_id == operation_id for item in inspection.operations):
        raise PrimaryPinError("operation_conflict")


def _result_from_receipt(receipt: Mapping[str, Any], *, idempotent_replay: bool) -> PrimaryPinApplyResult:
    return PrimaryPinApplyResult(
        status=str(receipt["status"]),
        operation_kind=str(receipt["operation_kind"]),
        memory_id=str(receipt["memory_id"]),
        current_revision=int(receipt["current_revision"]),
        current_lifecycle_state=str(receipt["current_lifecycle_state"]),
        current_mutation_state=str(receipt["current_mutation_state"]),
        prior_pin_state=str(receipt["prior_pin_state"]),
        target_pin_state=str(receipt["target_pin_state"]),
        retrieval_eligible=True,
        priority_hint_enabled=receipt["target_pin_state"] == "pinned",
        idempotent_replay=idempotent_replay,
        effect_applied=receipt.get("effect_applied") is True,
        receipt_id=str(receipt["receipt_id"]),
    )


def _public_history_item(receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "operation_kind": receipt["operation_kind"],
        "public_status": receipt["status"],
        "current_revision": receipt["current_revision"],
        "target_pin_state": receipt["target_pin_state"],
        "timestamp_class": "recorded_utc",
        "effect_flags": {
            "pin_state_changed": receipt["effect_applied"] is True,
            "priority_hint_enabled": receipt["target_pin_state"] == "pinned",
            "ordinary_retrieval_excluded": False,
            "semantic_content_changed": False,
            "physical_deletion": False,
        },
        "receipt_id": receipt["receipt_id"],
    }


def _valid_receipt(value: object, *, namespace: str, memory_id: str) -> bool:
    if not isinstance(value, dict):
        return False
    required = {"schema_version", "runtime_private", "content_included", "operation_kind", "operation_id", "operation_key", "receipt_id", "binding_digest", "character_id", "namespace", "memory_id", "current_physical_id", "current_revision", "current_lifecycle_state", "current_mutation_state", "prior_pin_state", "target_pin_state", "reason_digest", "token_digest", "requested_at", "applied_at", "status", "effect_applied", "ordinary_retrieval_excluded", "priority_hint_enabled", "semantic_content_changed", "physical_deletion", "audit_evidence_retained"}
    kind = value.get("operation_kind")
    target = value.get("target_pin_state")
    return set(value) == required and value.get("schema_version") == PIN_RECEIPT_SCHEMA and value.get("runtime_private") is True and value.get("content_included") is False and kind in {"pin", "unpin"} and value.get("namespace") == namespace and value.get("memory_id") == memory_id and value.get("current_lifecycle_state") == "active" and value.get("current_mutation_state") == "none" and value.get("prior_pin_state") in {"pinned", "unpinned"} and target == _target_state(str(kind)) and value.get("status") in {"applied", "already_pinned", "already_unpinned"} and type(value.get("current_revision")) is int and value.get("current_revision", 0) >= 1 and all(is_sha256(value.get(key)) for key in ("operation_key", "receipt_id", "binding_digest", "current_physical_id", "reason_digest", "token_digest")) and _bounded(value.get("operation_id"), 128, multiline=False) and _bounded(value.get("character_id"), 128, multiline=False) and _bounded(value.get("requested_at"), 128, multiline=False) and _bounded(value.get("applied_at"), 128, multiline=False) and value.get("effect_applied") in {True, False} and value.get("ordinary_retrieval_excluded") is False and value.get("priority_hint_enabled") is (target == "pinned") and value.get("semantic_content_changed") is False and value.get("physical_deletion") is False and value.get("audit_evidence_retained") is True


def _valid_state(value: object, *, namespace: str, memory_id: str) -> bool:
    if not isinstance(value, dict):
        return False
    required = {"schema_version", "runtime_private", "content_included", "namespace", "memory_id", "current_pin_state", "current_revision", "last_operation_kind", "last_status", "last_receipt_id", "updated_at", "ordinary_retrieval_excluded", "priority_hint_enabled"}
    state = value.get("current_pin_state")
    return set(value) == required and value.get("schema_version") == PIN_STATE_SCHEMA and value.get("runtime_private") is True and value.get("content_included") is False and value.get("namespace") == namespace and value.get("memory_id") == memory_id and state in {"pinned", "unpinned"} and type(value.get("current_revision")) is int and value.get("current_revision", 0) >= 1 and value.get("last_operation_kind") in {"pin", "unpin"} and value.get("last_status") in {"applied", "already_pinned", "already_unpinned"} and is_sha256(value.get("last_receipt_id")) and _bounded(value.get("updated_at"), 128, multiline=False) and value.get("ordinary_retrieval_excluded") is False and value.get("priority_hint_enabled") is (state == "pinned")


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode) or info.st_size <= 0 or info.st_size > _MAX_ARTIFACT_BYTES:
            return None
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return None
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return value if isinstance(value, dict) and canonical + b"\n" == raw else None


def _atomic_write_json(path: Path, value: Mapping[str, Any], *, create_only: bool) -> None:
    data = json.dumps(dict(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
    tmp = path.parent / f".{path.name}.{os.getpid()}.tmp"
    try:
        with os.fdopen(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if create_only:
            os.link(tmp, path)
            tmp.unlink()
        else:
            os.replace(tmp, path)
    except FileExistsError:
        raise PrimaryPinError("operation_conflict") from None
    except OSError as exc:
        raise PrimaryPinError("store_unavailable") from exc
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


def _ensure_private_dir(root: Path, directory: Path) -> None:
    current = root
    for part in directory.relative_to(root).parts:
        current = current / part
        if current.is_symlink() or (current.exists() and not current.is_dir()):
            raise PrimaryPinError("target_corrupt")
        current.mkdir(mode=0o700, exist_ok=True)


def _resolve_current(store_root: str | Path, *, namespace: str, memory_id: str, expected_revision: int | None):
    try:
        return resolve_primary_current_state(store_root, namespace=namespace, memory_id=memory_id, expected_revision=expected_revision)
    except PrimaryCurrentStateError as exc:
        raise PrimaryPinError(_contract_map_error(exc.code)) from exc


def _require_active_current(current: Any) -> None:
    if current.lifecycle_state != "active":
        raise PrimaryPinError("target_not_active")
    if current.mutation_state == "corrupt" or not current.controls_valid or not current.page_valid:
        raise PrimaryPinError("target_corrupt")
    if current.mutation_state == "recovery_required":
        raise PrimaryPinError("recovery_required")
    if current.mutation_state != "none":
        raise PrimaryPinError("operation_conflict")
    if not current.retrieval_eligible:
        raise PrimaryPinError("target_corrupt")


def _target_state(operation_kind: str) -> str:
    return "pinned" if operation_kind == "pin" else "unpinned"


def _effects(operation_kind: str) -> dict[str, bool]:
    value = {"ordinary_retrieval_deleted": False, "ordinary_retrieval_excluded": False, "semantic_content_changed": False, "physical_deletion": False, "audit_evidence_retained": True}
    value["future_priority_hint_contract" if operation_kind == "pin" else "future_priority_hint_removed_contract"] = True
    return value


def _validate_operation_kind(operation_kind: str) -> None:
    if operation_kind not in {"pin", "unpin"}:
        raise PrimaryPinError("invalid_request")


def _validate_request(value: Mapping[str, Any]) -> None:
    if not isinstance(value.get("store_root"), str) or not value["store_root"] or value["store_root"] != value["store_root"].strip() or "\x00" in value["store_root"]:
        raise PrimaryPinError("store_unavailable")
    _validate_namespace(value.get("namespace"))
    _validate_memory_id(value.get("memory_id"))
    if type(value.get("expected_revision")) is not int or value["expected_revision"] < 1:
        raise PrimaryPinError("invalid_request")
    for key in ("character_id", "operation_id"):
        if not _bounded(value.get(key), 128, multiline=False):
            raise PrimaryPinError("invalid_request")
    if not _bounded(value.get("reason"), 512, multiline=True):
        raise PrimaryPinError("invalid_request")
    if not isinstance(value.get("apply_token"), str) or not value["apply_token"] or len(value["apply_token"]) > 8192 or any(char in value["apply_token"] for char in "\r\n\t"):
        raise PrimaryPinError("token_invalid")


def _validate_namespace(namespace: object) -> None:
    if not _bounded(namespace, 128, multiline=False):
        raise PrimaryPinError("invalid_request")


def _validate_memory_id(memory_id: object) -> None:
    if not is_sha256(memory_id):
        raise PrimaryPinError("target_not_found")


def _safe_root(value: str | Path) -> Path:
    root = value if isinstance(value, Path) else Path(value) if isinstance(value, str) and value and value == value.strip() and "\x00" not in value else None
    if root is None or _path_has_symlink(root) or not root.exists() or not root.is_dir():
        raise PrimaryPinError("store_unavailable")
    return root


def _path_has_symlink(path: Path) -> bool:
    current = Path(path.anchor) if path.is_absolute() else Path()
    for part in path.parts[1:] if path.is_absolute() else path.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _bounded(value: object, limit: int, *, multiline: bool) -> bool:
    return isinstance(value, str) and value and value == value.strip() and len(value) <= limit and "\x00" not in value and all(ord(char) not in {0x2028, 0x2029} and not 0xD800 <= ord(char) <= 0xDFFF for char in value) and (multiline or not any(char in value for char in "\r\n\t"))


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _utc(value: datetime | None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = [
    "PIN_APPLY_RESPONSE_SCHEMA", "PIN_RECEIPT_SCHEMA", "PIN_ROOT", "PIN_STATE_SCHEMA",
    "UNPIN_APPLY_RESPONSE_SCHEMA", "PrimaryPinApplyResult", "PrimaryPinStateIndex",
    "apply_primary_memory_pin", "apply_primary_memory_unpin", "get_primary_memory_pin_state",
    "list_primary_memory_pin_history", "list_primary_memory_unpin_history",
    "load_primary_pin_state_index", "preflight_primary_memory_pin_apply",
    "preflight_primary_memory_unpin_apply",
]
