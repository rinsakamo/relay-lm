"""Exact M3g receipt validation for RelayMEM M3h recovery audit."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import PurePosixPath
from typing import Any

from ._relaymem_primary_page_writer_common import TARGET_DIR, bad_text, is_sha256

RECEIPT_SCHEMA = "relaymem.primary_index_log_reconciliation_receipt.v0"
RECEIPT_FIELDS = {
    "schema_version", "runtime_private", "content_included", "reconciliation_state",
    "page_relative_path", "page_digest", "idempotency_key", "index_entry_identity",
    "log_entry_identity", "index_expected_digest", "index_proposed_digest",
    "log_expected_digest", "log_proposed_digest", "status", "writes_memory",
    "index_reconciled", "log_reconciled", "index_updated", "log_updated",
    "index_idempotent_noop", "log_idempotent_noop", "durability_confirmed",
    "cleanup_complete", "operation_count", "updates_index", "updates_log",
}
OPERATION_COUNTS = {
    "index_and_log_update_required": 2,
    "index_update_required": 1,
    "log_update_required": 1,
    "already_reconciled": 0,
}
PLAN_NOOPS = {
    "index_and_log_update_required": (False, False),
    "index_update_required": (False, True),
    "log_update_required": (True, False),
    "already_reconciled": (True, True),
}
STATUSES = {
    "blocked", "dry_run_ready", "resume_ready", "already_applied", "applied",
    "index_applied_log_pending", "applied_durability_unconfirmed",
    "applied_cleanup_incomplete", "applied_state_uncertain",
}
BOOL_FIELDS = (
    "writes_memory", "index_reconciled", "log_reconciled", "index_updated",
    "log_updated", "index_idempotent_noop", "log_idempotent_noop",
    "durability_confirmed", "cleanup_complete", "updates_index", "updates_log",
)
DIGEST_FIELDS = (
    "page_digest", "idempotency_key", "index_entry_identity",
    "log_entry_identity", "index_expected_digest", "index_proposed_digest",
    "log_expected_digest", "log_proposed_digest",
)


def parse_m3g_reconciliation_receipt(
    value: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return invalid("primary_reconciliation_recovery_receipt_missing")
    reasons: list[str] = []

    if set(value) != RECEIPT_FIELDS:
        reasons.append("primary_reconciliation_recovery_receipt_fields_mismatch")
    if value.get("schema_version") != RECEIPT_SCHEMA:
        reasons.append("primary_reconciliation_recovery_receipt_schema_invalid")
    _expect(value, reasons, "runtime_private", True)
    _expect(value, reasons, "content_included", False)

    state = value.get("reconciliation_state")
    if not isinstance(state, str) or state not in OPERATION_COUNTS:
        reasons.append("primary_reconciliation_recovery_receipt_state_invalid")
        state = ""
    status = value.get("status")
    if not isinstance(status, str) or status not in STATUSES:
        reasons.append("primary_reconciliation_recovery_receipt_status_invalid")
        status = ""

    for field in DIGEST_FIELDS:
        if not is_sha256(value.get(field)):
            reasons.append(f"primary_reconciliation_recovery_receipt_{field}_invalid")
    if not _exact_primary_page_path(
        value.get("page_relative_path"), value.get("idempotency_key")
    ):
        reasons.append("primary_reconciliation_recovery_receipt_page_path_invalid")
    for field in BOOL_FIELDS:
        if type(value.get(field)) is not bool:
            reasons.append(f"primary_reconciliation_recovery_receipt_{field}_invalid")

    count = value.get("operation_count")
    if type(count) is not int or not 0 <= count <= 2:
        reasons.append("primary_reconciliation_recovery_receipt_operation_count_invalid")
    elif state and count != OPERATION_COUNTS[state]:
        reasons.append("primary_reconciliation_recovery_receipt_operation_count_mismatch")

    for role in ("index", "log"):
        if (
            type(value.get(f"updates_{role}")) is bool
            and type(value.get(f"{role}_updated")) is bool
            and value[f"updates_{role}"] is not value[f"{role}_updated"]
        ):
            reasons.append(
                f"primary_reconciliation_recovery_receipt_{role}_update_alias_mismatch"
            )
        if value.get(f"{role}_updated") is True and value.get(
            f"{role}_idempotent_noop"
        ) is True:
            reasons.append(
                f"primary_reconciliation_recovery_receipt_{role}_outcome_mismatch"
            )
        if value.get(f"{role}_idempotent_noop") is True and value.get(
            f"{role}_reconciled"
        ) is not True:
            reasons.append(f"primary_reconciliation_recovery_receipt_{role}_noop_mismatch")

    if type(value.get("writes_memory")) is bool:
        wrote = value.get("index_updated") is True or value.get("log_updated") is True
        if value["writes_memory"] is not wrote:
            reasons.append("primary_reconciliation_recovery_receipt_write_state_mismatch")
    if value.get("durability_confirmed") is True and not _all_reconciled(value):
        reasons.append("primary_reconciliation_recovery_receipt_durability_claim_invalid")
    elif value.get("durability_confirmed") is True and value.get(
        "cleanup_complete"
    ) is not True:
        reasons.append("primary_reconciliation_recovery_receipt_durability_claim_invalid")

    if state:
        for role, plan_noop in zip(("index", "log"), PLAN_NOOPS[state]):
            expected = value.get(f"{role}_expected_digest")
            proposed = value.get(f"{role}_proposed_digest")
            if is_sha256(expected) and is_sha256(proposed):
                if (expected == proposed) is not plan_noop:
                    reasons.append(
                        f"primary_reconciliation_recovery_receipt_{role}_digest_transition_mismatch"
                    )
            if plan_noop:
                if value.get(f"{role}_updated") is not False:
                    reasons.append(
                        f"primary_reconciliation_recovery_receipt_{role}_update_not_planned"
                    )
                if (
                    value.get(f"{role}_idempotent_noop") is not True
                    or value.get(f"{role}_reconciled") is not True
                ):
                    reasons.append(
                        f"primary_reconciliation_recovery_receipt_{role}_plan_noop_state_mismatch"
                    )
            elif value.get(f"{role}_reconciled") is True and not (
                value.get(f"{role}_updated") is True
                or value.get(f"{role}_idempotent_noop") is True
            ):
                reasons.append(
                    f"primary_reconciliation_recovery_receipt_{role}_reconciled_outcome_missing"
                )

    reasons.extend(_status_reasons(value, status))
    return invalid(*reasons) if reasons else {
        "valid": True, "receipt": dict(value), "blocked_reasons": []
    }


def _status_reasons(value: Mapping[str, Any], status: str) -> list[str]:
    checks: dict[str, tuple[tuple[str, bool], ...]] = {
        "dry_run_ready": (
            ("writes_memory", False), ("index_updated", False),
            ("log_updated", False), ("durability_confirmed", False),
            ("cleanup_complete", True),
        ),
        "resume_ready": (
            ("writes_memory", False), ("index_reconciled", True),
            ("log_reconciled", False), ("index_updated", False),
            ("log_updated", False), ("index_idempotent_noop", True),
            ("durability_confirmed", False), ("cleanup_complete", True),
        ),
        "already_applied": (
            ("writes_memory", False), ("index_reconciled", True),
            ("log_reconciled", True), ("index_updated", False),
            ("log_updated", False), ("index_idempotent_noop", True),
            ("log_idempotent_noop", True), ("cleanup_complete", True),
        ),
        "applied": (
            ("writes_memory", True), ("index_reconciled", True),
            ("log_reconciled", True), ("durability_confirmed", True),
            ("cleanup_complete", True),
        ),
        "index_applied_log_pending": (
            ("index_reconciled", True), ("log_reconciled", False),
            ("log_updated", False), ("log_idempotent_noop", False),
            ("durability_confirmed", False),
        ),
        "applied_cleanup_incomplete": (("cleanup_complete", False),),
    }
    reasons: list[str] = []
    if not status:
        return reasons
    if status == "blocked":
        if value.get("durability_confirmed") is not False:
            reasons.append("primary_reconciliation_recovery_receipt_blocked_state_mismatch")
        return reasons
    suffix = {
        "dry_run_ready": "dry_run_state_mismatch",
        "resume_ready": "resume_state_mismatch",
        "already_applied": "already_applied_state_mismatch",
        "applied": "applied_state_mismatch",
        "index_applied_log_pending": "partial_state_mismatch",
        "applied_cleanup_incomplete": "cleanup_state_mismatch",
    }.get(status)
    if status == "applied_durability_unconfirmed":
        partial_index = (
            value.get("log_reconciled") is False
            and value.get("index_updated") is True
            and value.get("log_updated") is False
            and value.get("writes_memory") is True
        )
        if (
            value.get("index_reconciled") is not True
            or value.get("durability_confirmed") is not False
            or not (value.get("log_reconciled") is True or partial_index)
        ):
            reasons.append(
                "primary_reconciliation_recovery_receipt_"
                "durability_state_mismatch"
            )
    elif suffix and any(
        value.get(field) is not expected
        for field, expected in checks[status]
    ):
        reasons.append(f"primary_reconciliation_recovery_receipt_{suffix}")
    if status == "dry_run_ready" and value.get("index_reconciled") is True:
        reasons.append("primary_reconciliation_recovery_receipt_dry_run_state_mismatch")
    return reasons


def _expect(
    value: Mapping[str, Any], reasons: list[str], field: str, expected: bool
) -> None:
    if type(value.get(field)) is not bool or value.get(field) is not expected:
        reasons.append(f"primary_reconciliation_recovery_receipt_{field}_invalid")


def _all_reconciled(value: Mapping[str, Any]) -> bool:
    return (
        value.get("index_reconciled") is True
        and value.get("log_reconciled") is True
    )


def _exact_primary_page_path(value: object, key: object) -> bool:
    if (
        not isinstance(value, str) or not isinstance(key, str) or not value
        or value.startswith("/") or "\\" in value or bad_text(value)
    ):
        return False
    path = PurePosixPath(value)
    if path.as_posix() != value or any(part in {"", ".", ".."} for part in path.parts):
        return False
    prefixes = tuple(f"{directory}/" for directory in TARGET_DIR.values())
    return value.startswith(prefixes) and value.endswith(f"/{key}.md")


def invalid(*reasons: str) -> dict[str, Any]:
    return {"valid": False, "blocked_reasons": dedupe(reasons)}


def dedupe(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


__all__ = ["parse_m3g_reconciliation_receipt"]
