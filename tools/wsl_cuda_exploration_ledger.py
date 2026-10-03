"""Durable, non-refundable trial accounting for #3018's bounded WSL CUDA exploration.

This module NEVER grants execution authority. A separate, fresh, structured
owner grant and the canonical physical runner are required before any trial.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import secrets
import stat
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping

CAMPAIGN_ID = "wsl-cuda-exploration-20261003-a"
PROPOSAL_SHA256 = "a30a6a44ec0a657fa9209ec50a8daf2fdb2534c45a7ae96202180661c1457e6d"
BUDGET_COMMENT_ID = 5965167490
APPROVED_BUDGET = 8
FORMAT_VERSION = 1
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class CampaignLedgerError(RuntimeError):
    """A trial cannot be reserved or the evidence ledger is inconsistent."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()


def _require_sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
        raise CampaignLedgerError(f"{name} must be an exact lowercase SHA256")
    return value


def _safe_regular(path: Path, *, may_be_missing: bool = False) -> None:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        if may_be_missing:
            return
        raise CampaignLedgerError(f"required ledger path is absent: {path}") from None
    if not stat.S_ISREG(mode):
        raise CampaignLedgerError(f"ledger path is not a regular file: {path}")


@contextmanager
def _lock(path: Path) -> Iterator[None]:
    # Do not resolve a symlinked ledger root or permit a symlinked lock path.
    if not path.is_absolute() or path != Path(os.path.abspath(path)):
        raise CampaignLedgerError("ledger path must be an absolute lexical path")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.parent.is_symlink():
        raise CampaignLedgerError("ledger directory must not be a symlink")
    lock = path.with_name(path.name + ".lock")
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(lock, flags, 0o600)
    try:
        _safe_regular(path, may_be_missing=True)
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _read(path: Path) -> dict[str, Any]:
    _safe_regular(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CampaignLedgerError("ledger content cannot be verified") from exc
    if not isinstance(payload, dict):
        raise CampaignLedgerError("ledger root is not a JSON object")
    if (
        payload.get("format_version") != FORMAT_VERSION
        or payload.get("campaign_id") != CAMPAIGN_ID
        or payload.get("proposal_sha256") != PROPOSAL_SHA256
        or payload.get("budget_comment_id") != BUDGET_COMMENT_ID
        or payload.get("maximum_exploration_trials") != APPROVED_BUDGET
        or not isinstance(payload.get("trials"), list)
    ):
        raise CampaignLedgerError("ledger identity or schema does not match the owner budget")
    for index, trial in enumerate(payload["trials"], 1):
        if (
            not isinstance(trial, dict)
            or trial.get("trial_id") != f"exp-{index:02d}"
            or trial.get("sequence") != index
            or trial.get("status") not in ("RESERVED", "BLOCKED", "PASSED")
        ):
            raise CampaignLedgerError("ledger has a nonmonotonic or malformed trial")
    if len(payload["trials"]) > APPROVED_BUDGET:
        raise CampaignLedgerError("ledger already exceeds the approved exploration budget")
    return payload


def _commit(path: Path, data: Mapping[str, Any], *, exclusive: bool = False) -> str:
    _safe_regular(path, may_be_missing=True)
    if exclusive and path.exists():
        raise CampaignLedgerError("existing ledger cannot be recreated or reset")
    raw = _canonical(data)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    fd = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        if exclusive:
            # The campaign must never overwrite a historical ledger.
            os.link(temp, path)
            os.unlink(temp)
        else:
            os.replace(temp, path)
        dirfd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    finally:
        if temp.exists():
            temp.unlink()
    if path.read_bytes() != raw:
        raise CampaignLedgerError("durable ledger read-back mismatched the committed bytes")
    return _sha256(raw)


def initialize_ledger(path: Path, *, execution_grant_sha256: str, execution_comment_id: int) -> str:
    """Initialize only after a separately verified executable owner grant.

    This is storage, not grant verification. Callers must verify the exact
    owner grant with GitHub before calling this function.
    """
    grant = _require_sha(execution_grant_sha256, "execution grant")
    if isinstance(execution_comment_id, bool) or not isinstance(execution_comment_id, int) or execution_comment_id <= BUDGET_COMMENT_ID:
        raise CampaignLedgerError("a separate later execution comment is required")
    with _lock(path):
        return _commit(path, {
            "format_version": FORMAT_VERSION,
            "campaign_id": CAMPAIGN_ID,
            "proposal_sha256": PROPOSAL_SHA256,
            "budget_comment_id": BUDGET_COMMENT_ID,
            "maximum_exploration_trials": APPROVED_BUDGET,
            "execution_comment_id": execution_comment_id,
            "execution_grant_sha256": grant,
            "created_at": _now(),
            "trials": [],
        }, exclusive=True)


def inspect_ledger(path: Path) -> dict[str, Any]:
    with _lock(path):
        return _read(path)


def reserve_trial(
    path: Path,
    *,
    execution_comment_id: int,
    execution_grant_sha256: str,
    trial_descriptor_sha256: str,
    frozen_checkout: str,
    receipt_path: Path,
    output_root: Path,
) -> dict[str, Any]:
    """Spend a unique slot before *any* public runner invocation."""
    grant = _require_sha(execution_grant_sha256, "execution grant")
    descriptor = _require_sha(trial_descriptor_sha256, "trial descriptor")
    if not frozen_checkout or not Path(frozen_checkout).is_absolute():
        raise CampaignLedgerError("trial checkout must be an absolute frozen path")
    for label, item in (("receipt", receipt_path), ("output", output_root)):
        if not item.is_absolute() or item.exists() or item.is_symlink():
            raise CampaignLedgerError(f"trial {label} must be a distinct absent absolute path")
    with _lock(path):
        payload = _read(path)
        if payload.get("execution_comment_id") != execution_comment_id or payload.get("execution_grant_sha256") != grant:
            raise CampaignLedgerError("trial grant does not match the initialized campaign")
        trials = payload["trials"]
        if len(trials) >= APPROVED_BUDGET:
            raise CampaignLedgerError("all eight exploration slots have been consumed")
        if any(t["status"] == "PASSED" for t in trials):
            raise CampaignLedgerError("exploration must stop after the first strict PASS")
        if trials and (trials[-1]["status"] != "BLOCKED" or trials[-1].get("cleanup_verified") is not True):
            raise CampaignLedgerError("previous trial requires terminal and verified cleanup reconciliation")
        if any(
            str(receipt_path) == t["receipt_path"] or str(output_root) == t["output_root"]
            for t in trials
        ):
            raise CampaignLedgerError("trial must not reuse an earlier receipt or output")
        sequence = len(trials) + 1
        trial = {
            "trial_id": f"exp-{sequence:02d}",
            "sequence": sequence,
            "reservation_id": secrets.token_hex(16),
            "status": "RESERVED",
            "reserved_at": _now(),
            "trial_descriptor_sha256": descriptor,
            "frozen_checkout": frozen_checkout,
            "receipt_path": str(receipt_path),
            "output_root": str(output_root),
            "cleanup_verified": False,
        }
        trials.append(trial)
        sha = _commit(path, payload)
        return {**trial, "ledger_sha256": sha}


def finalize_trial(
    path: Path,
    *,
    reservation_id: str,
    status: str,
    queue_receipt_sha256: str | None,
    evidence_manifest_sha256: str,
    cleanup_verified: bool,
    zero_requests_verified: bool,
    strict_closure_verified: bool,
) -> str:
    """Persist one terminal; no retry, refund, edit or success without evidence."""
    if status not in ("BLOCKED", "PASSED"):
        raise CampaignLedgerError("terminal status must be BLOCKED or PASSED")
    evidence = _require_sha(evidence_manifest_sha256, "evidence manifest")
    receipt = _require_sha(queue_receipt_sha256, "queue receipt") if queue_receipt_sha256 is not None else None
    if any(type(x) is not bool for x in (cleanup_verified, zero_requests_verified, strict_closure_verified)):
        raise CampaignLedgerError("terminal verification flags must be exact booleans")
    if status == "PASSED" and not (receipt and cleanup_verified and zero_requests_verified and strict_closure_verified):
        raise CampaignLedgerError("exploratory PASS needs strict closure, receipt, zero requests and cleanup")
    with _lock(path):
        payload = _read(path)
        trials = payload["trials"]
        if not trials or trials[-1].get("reservation_id") != reservation_id or trials[-1]["status"] != "RESERVED":
            raise CampaignLedgerError("terminal has no unique last reserved trial or was already written")
        trials[-1].update({
            "status": status,
            "finished_at": _now(),
            "queue_receipt_sha256": receipt,
            "evidence_manifest_sha256": evidence,
            "cleanup_verified": cleanup_verified,
            "zero_requests_verified": zero_requests_verified,
            "strict_closure_verified": strict_closure_verified,
        })
        return _commit(path, payload)
