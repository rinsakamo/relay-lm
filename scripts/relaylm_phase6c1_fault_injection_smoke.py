#!/usr/bin/env python3
"""Fault-injection smoke scaffolding for the Phase 6-C1 Primary MEM worker."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.relaymem_primary_index_log_apply import (
    apply_relaymem_primary_index_log_reconciliation,
)
from relaylm.relaymem_primary_index_log_recovery_audit import (
    audit_relaymem_primary_index_log_reconciliation_recovery,
)
from relaylm.relaymem_slp_queue_state import (
    RelayMEMSLPQueueTransitionRequest,
    build_relaymem_slp_queue_state_node_result,
)
from scripts._relaylm_phase6c1_fault_fixtures import (
    CANARY_CLAIM_OWNER,
    CANARY_LEASE_TOKEN,
    CANARY_MEMORY_SUMMARY,
    CANARY_MEMORY_TITLE,
    CANARY_NAMESPACE,
    CANARY_RAW_MESSAGE,
    CRASH_POINT_NAMES,
    FixtureBuildError,
    Phase6C1FaultFixture,
    apply_queue_transition,
    build_claimed_job_fixture,
    build_crash_point_fixture,
    build_diverged_store_fixture,
    build_exact_duplicate_page_fixture,
    build_expired_claim_fixture,
    build_fully_reconciled_fixture,
    build_index_applied_log_pending_fixture,
    build_m3e_published_fixture,
    build_m3g_lock_contention_fixture,
    build_m3h_lock_contention_fixture,
    build_stale_fence_fixture,
    read_canonical_queue_record,
    snapshot_store,
)


class SmokeFailure(RuntimeError):
    pass


def require(condition: bool, reason_id: str) -> None:
    if not condition:
        raise SmokeFailure(reason_id)


def request(
    record: Mapping[str, object],
    transition_kind: str,
    **overrides: object,
) -> RelayMEMSLPQueueTransitionRequest:
    values: dict[str, object] = {
        "transition_kind": transition_kind,
        "job_id": record["job_id"],
        "dispatch_idempotency_key": record["dispatch_idempotency_key"],
        "expected_record_revision": record["record_revision"],
        "expected_state": record["state"],
        "claim_owner": "",
        "claim_generation": record["claim_generation"],
        "lease_token": "",
        "lease_duration_seconds": 0,
        "retry_class": "unclassified",
        "retry_not_before": None,
        "failure_class": "none",
        "terminal_state": "",
        "terminal_reason_id": "",
    }
    values.update(overrides)
    return RelayMEMSLPQueueTransitionRequest(**values)  # type: ignore[arg-type]


def serialized(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, default=str)


def private_values(fixture: Phase6C1FaultFixture) -> tuple[str, ...]:
    values = [
        CANARY_RAW_MESSAGE,
        CANARY_MEMORY_SUMMARY,
        CANARY_MEMORY_TITLE,
        CANARY_NAMESPACE,
        CANARY_LEASE_TOKEN,
    ]
    if fixture.queue_root is not None:
        values.append(str(fixture.queue_root))
    if fixture.store_root is not None:
        values.append(str(fixture.store_root))
    record = fixture.canonical_record or {}
    for field in ("job_id", "dispatch_idempotency_key", "claim_owner", "lease_token"):
        value = record.get(field)
        if isinstance(value, str) and value:
            values.append(value)
    for field in ("page_relative_path", "page_digest", "memory_write_idempotency_key"):
        value = fixture.private_artifacts.get(field)
        if isinstance(value, str) and value:
            values.append(value)
    return tuple(dict.fromkeys(values))


def require_public_safe(
    value: object,
    fixture: Phase6C1FaultFixture,
    reason_id: str,
) -> None:
    text = serialized(value)
    for private in private_values(fixture):
        require(private not in text, reason_id)
    require("Traceback" not in text, reason_id)
    require("OSError" not in text, reason_id)


def require_reason(result: object, reason: str, reason_id: str) -> None:
    require(reason in getattr(result, "blocked_reasons", ()), reason_id)


def test_claimed_record() -> None:
    root: Path | None = None
    with build_claimed_job_fixture() as fixture:
        root = fixture.queue_root
        record = read_canonical_queue_record(fixture)
        require(record["state"] == "claimed", "claimed_state")
        require(int(record["claim_generation"]) >= 1, "claimed_generation")
        require(
            record["attempt_count"] == record["claim_generation"],
            "claimed_attempt_generation",
        )
        require(bool(record["claim_owner"]), "claimed_owner")
        require(bool(record["lease_token"]), "claimed_token")
        require(record["terminal_reason_id"] == "", "claimed_terminal_reason")
        require(record["retry_not_before"] is None, "claimed_retry_not_before")
        claim = fixture.private_artifacts["claim_result"]
        require_public_safe(claim.to_log_dict(), fixture, "claimed_projection_leak")
        require_public_safe(
            build_relaymem_slp_queue_state_node_result(claim).to_log_dict(),
            fixture,
            "claimed_node_projection_leak",
        )
        require(CANARY_RAW_MESSAGE not in repr(fixture), "fixture_repr_leak")
    require(root is not None and not root.exists(), "claimed_temp_cleanup")


def test_expired_claim() -> None:
    with build_expired_claim_fixture() as fixture:
        root = fixture.queue_root
        record = fixture.canonical_record
        require(root is not None and record is not None, "expired_fixture_missing")
        renew = apply_queue_transition(
            root,
            request(
                record,
                "renew_lease",
                claim_owner=record["claim_owner"],
                lease_token=record["lease_token"],
                lease_duration_seconds=30,
            ),
        )
        require(renew.status == "not_ready", "expired_renew_status")
        require_reason(
            renew,
            "active_lease_expired_stale_recovery_required",
            "expired_renew_reason",
        )
        release = apply_queue_transition(
            root,
            request(
                record,
                "retry_release",
                claim_owner=record["claim_owner"],
                lease_token=record["lease_token"],
                retry_class="transient_lock_contention",
                failure_class="resource_contention",
            ),
        )
        require(release.status == "not_ready", "expired_release_status")
        terminal = apply_queue_transition(
            root,
            request(
                record,
                "commit_terminal",
                claim_owner=record["claim_owner"],
                lease_token=record["lease_token"],
                terminal_state="succeeded",
                terminal_reason_id="primary_mem_durable_state_verified",
            ),
        )
        require(terminal.status == "not_ready", "expired_terminal_status")
        wrong_owner = apply_queue_transition(
            root,
            request(
                record,
                "commit_terminal",
                claim_owner="phase6c1-stale-owner",
                lease_token=record["lease_token"],
                terminal_state="succeeded",
                terminal_reason_id="primary_mem_durable_state_verified",
            ),
        )
        require(wrong_owner.status == "conflict", "expired_wrong_owner_status")
        require_reason(wrong_owner, "claim_owner_mismatch", "expired_wrong_owner_reason")
        for result in (renew, release, terminal, wrong_owner):
            require_public_safe(result.to_log_dict(), fixture, "expired_projection_leak")
        recovery = apply_queue_transition(
            root,
            request(record, "stale_recovery", lease_token=record["lease_token"]),
        )
        require(recovery.status == "applied", "expired_recovery_status")
        require(recovery.durable_record is not None, "expired_recovery_record")
        require(recovery.durable_record["state"] == "queued", "expired_recovery_state")
        require_public_safe(
            recovery.to_log_dict(),
            fixture,
            "expired_recovery_projection_leak",
        )


def test_stale_fences() -> None:
    with build_stale_fence_fixture() as fixture:
        root = fixture.queue_root
        require(root is not None, "stale_root_missing")
        stale_requests = fixture.private_artifacts["stale_requests"]
        require(isinstance(stale_requests, Mapping), "stale_requests_missing")
        expected = {
            "revision": "record_revision_mismatch",
            "generation": "claim_generation_mismatch",
            "token": "lease_token_mismatch",
            "owner_terminal": "claim_owner_mismatch",
        }
        before = read_canonical_queue_record(fixture)
        for name, reason in expected.items():
            item = stale_requests[name]
            require(
                isinstance(item, RelayMEMSLPQueueTransitionRequest),
                "stale_request_type",
            )
            result = apply_queue_transition(root, item)
            require(result.status == "conflict", f"stale_{name}_status")
            require_reason(result, reason, f"stale_{name}_reason")
            require(
                read_canonical_queue_record(fixture) == before,
                f"stale_{name}_mutation",
            )
            require_public_safe(
                result.to_log_dict(),
                fixture,
                f"stale_{name}_projection",
            )


def test_m3e_and_duplicate() -> None:
    store_root: Path | None = None
    with build_m3e_published_fixture() as fixture:
        store_root = fixture.store_root
        require(store_root is not None, "m3e_store_missing")
        result = fixture.private_artifacts["m3e_result"]
        require(result["status"] == "applied", "m3e_status")
        page_relative = fixture.private_artifacts["page_relative_path"]
        page_path = store_root / str(page_relative)
        require(page_path.is_file(), "m3e_page_missing")
        require(
            CANARY_MEMORY_SUMMARY in page_path.read_text(encoding="utf-8"),
            "m3e_private_content_missing",
        )
        require_public_safe(result["projection"], fixture, "m3e_projection_leak")
    require(store_root is not None and not store_root.exists(), "m3e_temp_cleanup")

    with build_exact_duplicate_page_fixture() as fixture:
        store_root = fixture.store_root
        require(store_root is not None, "duplicate_store_missing")
        duplicate = fixture.private_artifacts["duplicate_m3e_result"]
        require(duplicate["status"] == "already_applied", "duplicate_status")
        require(duplicate["writes_memory"] is False, "duplicate_write")
        require(duplicate["idempotent_noop"] is True, "duplicate_idempotency")
        pages = list((store_root / "memory/mem/primary/projects").glob("*.md"))
        require(len(pages) == 1, "duplicate_page_count")
        require_public_safe(
            duplicate["projection"],
            fixture,
            "duplicate_projection_leak",
        )


def test_m3g_lock_contention() -> None:
    store_root: Path | None = None
    lock_holder: Any = None
    with build_m3g_lock_contention_fixture() as fixture:
        store_root = fixture.store_root
        require(store_root is not None, "m3g_lock_store_missing")
        plan = fixture.private_artifacts["m3f_plan"]
        lock_holder = fixture.private_artifacts["lock_holder"]
        before = snapshot_store(store_root)
        started = time.monotonic()
        blocked = apply_relaymem_primary_index_log_reconciliation(
            plan_artifact=plan,
            root_path=str(store_root),
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
        require(time.monotonic() - started < 2.0, "m3g_lock_blocked_too_long")
        require(blocked["status"] == "blocked", "m3g_lock_status")
        require(
            "primary_reconciliation_apply_lock_unavailable"
            in blocked["blocked_reasons"],
            "m3g_lock_reason",
        )
        require(snapshot_store(store_root) == before, "m3g_lock_mutation")
        require_public_safe(blocked["projection"], fixture, "m3g_lock_projection")
        lock_holder.release()
        applied = apply_relaymem_primary_index_log_reconciliation(
            plan_artifact=plan,
            root_path=str(store_root),
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
        require(applied["status"] == "applied", "m3g_after_unlock_status")
        require_public_safe(
            applied["projection"],
            fixture,
            "m3g_after_unlock_projection",
        )
    require(
        lock_holder is not None and lock_holder.running is False,
        "m3g_lock_process_leak",
    )
    require(
        store_root is not None and not store_root.exists(),
        "m3g_lock_temp_cleanup",
    )


def test_m3h_lock_contention() -> None:
    store_root: Path | None = None
    lock_holder: Any = None
    with build_m3h_lock_contention_fixture() as fixture:
        store_root = fixture.store_root
        require(store_root is not None, "m3h_lock_store_missing")
        receipt = fixture.private_artifacts["m3g_result"]["receipt"]
        lock_holder = fixture.private_artifacts["lock_holder"]
        before = snapshot_store(store_root)
        started = time.monotonic()
        blocked = audit_relaymem_primary_index_log_reconciliation_recovery(
            receipt=receipt,
            root_path=str(store_root),
            enabled=True,
            dry_run_only=True,
        )
        require(time.monotonic() - started < 2.0, "m3h_lock_blocked_too_long")
        require(blocked["status"] == "blocked", "m3h_lock_status")
        require(
            "primary_reconciliation_recovery_lock_unavailable"
            in blocked["blocked_reasons"],
            "m3h_lock_reason",
        )
        require(
            blocked["recovery_classification"] != "recovery_not_required",
            "m3h_lock_false_success",
        )
        require(snapshot_store(store_root) == before, "m3h_lock_mutation")
        require_public_safe(blocked["projection"], fixture, "m3h_lock_projection")
        lock_holder.release()
        complete = audit_relaymem_primary_index_log_reconciliation_recovery(
            receipt=receipt,
            root_path=str(store_root),
            enabled=True,
            dry_run_only=True,
        )
        require(
            complete["status"] == "recovery_not_required",
            "m3h_after_unlock_status",
        )
        require_public_safe(
            complete["projection"],
            fixture,
            "m3h_after_unlock_projection",
        )
    require(
        lock_holder is not None and lock_holder.running is False,
        "m3h_lock_process_leak",
    )
    require(
        store_root is not None and not store_root.exists(),
        "m3h_lock_temp_cleanup",
    )


def test_recovery_states() -> None:
    with build_index_applied_log_pending_fixture() as fixture:
        audit = fixture.private_artifacts["m3h_result"]
        require(
            audit["store_state"] == "index_applied_log_pending",
            "partial_store_state",
        )
        require(
            audit["recovery_classification"] == "retry_reconciliation",
            "partial_recovery_class",
        )
        require_public_safe(audit["projection"], fixture, "partial_projection_leak")

    with build_fully_reconciled_fixture() as fixture:
        audit = fixture.private_artifacts["m3h_result"]
        require(audit["status"] == "recovery_not_required", "full_audit_status")
        require(audit["store_state"] == "fully_reconciled", "full_store_state")
        require(
            audit["recovery_classification"] == "recovery_not_required",
            "full_recovery_class",
        )
        require_public_safe(audit["projection"], fixture, "full_projection_leak")


def test_diverged_controls() -> None:
    with build_diverged_store_fixture("page_digest_mismatch") as fixture:
        audit = fixture.private_artifacts["diverged_audit"]
        require(
            audit["status"] != "recovery_not_required",
            "diverged_page_false_success",
        )
        require(
            audit["recovery_classification"] != "recovery_not_required",
            "diverged_page_false_class",
        )
        require_public_safe(audit["projection"], fixture, "diverged_page_projection")

    with build_diverged_store_fixture("index_symlink") as fixture:
        audit = fixture.private_artifacts["diverged_audit"]
        require(audit["status"] == "blocked", "diverged_symlink_status")
        require(
            any("symlink" in reason for reason in audit["blocked_reasons"]),
            "diverged_symlink_reason",
        )
        require(
            audit["recovery_classification"] != "recovery_not_required",
            "diverged_symlink_false_class",
        )
        require_public_safe(audit["projection"], fixture, "diverged_symlink_projection")


def test_crash_points() -> None:
    observed: set[str] = set()
    roots: list[Path] = []
    for name in CRASH_POINT_NAMES:
        with build_crash_point_fixture(name) as fixture:
            observed.add(str(fixture.crash_point))
            require(
                fixture.private_artifacts.get("next_safe_operation") is not None,
                "crash_next_operation",
            )
            require(
                fixture.private_artifacts.get("stale_operation_rejected_by") is not None,
                "crash_stale_fence",
            )
            if fixture.queue_root is not None:
                roots.append(fixture.queue_root)
            if fixture.store_root is not None:
                roots.append(fixture.store_root)
            require_public_safe(
                {
                    "crash_point": fixture.crash_point,
                    "expected_state": fixture.expected_state,
                    "next_safe_operation": fixture.private_artifacts["next_safe_operation"],
                },
                fixture,
                "crash_projection_leak",
            )
    require(observed == set(CRASH_POINT_NAMES), "crash_point_coverage")
    require(all(not root.exists() for root in roots), "crash_temp_cleanup")


def test_determinism_and_identity_domains() -> None:
    queue_records: list[dict[str, object]] = []
    queue_roots: list[Path] = []
    for _ in range(2):
        with build_claimed_job_fixture() as fixture:
            queue_records.append(read_canonical_queue_record(fixture))
            require(fixture.queue_root is not None, "deterministic_queue_root")
            queue_roots.append(fixture.queue_root)
    require(queue_records[0] == queue_records[1], "queue_fixture_nondeterministic")
    require(all(not root.exists() for root in queue_roots), "queue_fixture_cleanup")

    store_values: list[tuple[str, str, str, bytes]] = []
    store_roots: list[Path] = []
    for _ in range(2):
        with build_m3e_published_fixture() as fixture:
            root = fixture.store_root
            require(root is not None, "deterministic_store_root")
            store_roots.append(root)
            relative = str(fixture.private_artifacts["page_relative_path"])
            store_values.append(
                (
                    relative,
                    str(fixture.private_artifacts["page_digest"]),
                    str(fixture.private_artifacts["memory_write_idempotency_key"]),
                    (root / relative).read_bytes(),
                )
            )
    require(store_values[0] == store_values[1], "store_fixture_nondeterministic")
    require(all(not root.exists() for root in store_roots), "store_fixture_cleanup")
    dispatch_key = str(queue_records[0]["dispatch_idempotency_key"])
    memory_key = store_values[0][2]
    require(dispatch_key != memory_key, "idempotency_domains_equal")
    require(dispatch_key.startswith("slp-dispatch-v0:"), "dispatch_key_domain")
    require(len(memory_key) == 64 and ":" not in memory_key, "memory_key_domain")
    require(memory_key not in serialized(queue_records[0]), "memory_key_in_queue_record")


def test_source_boundaries() -> None:
    fixture_source = (
        REPO_ROOT / "scripts/_relaylm_phase6c1_fault_fixtures.py"
    ).read_text(encoding="utf-8")
    smoke_source = Path(__file__).read_text(encoding="utf-8")
    combined = fixture_source + smoke_source
    for forbidden in (
        "from relaylm.relaymem_slp_primary_worker_source",
        "from relaylm.relaymem_slp_primary_worker_outcome",
        "execute_relaymem_primary_pipeline(",
        "time.sleep(",
    ):
        require(forbidden not in combined, "worker_boundary_imported")


def public_probe() -> int:
    with build_claimed_job_fixture() as queue_fixture:
        claim = queue_fixture.private_artifacts["claim_result"]
        require_public_safe(claim.to_log_dict(), queue_fixture, "probe_queue_projection")
    with build_fully_reconciled_fixture() as store_fixture:
        audit = store_fixture.private_artifacts["m3h_result"]
        require_public_safe(audit["projection"], store_fixture, "probe_store_projection")
    print("Phase 6-C1 fault projection probe: ok")
    return 0


def test_subprocess_content_leakage() -> None:
    completed = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--public-probe"],
        cwd=str(REPO_ROOT),
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    require(completed.returncode == 0, "public_probe_failed")
    output = completed.stdout + completed.stderr
    for canary in (
        CANARY_RAW_MESSAGE,
        CANARY_MEMORY_SUMMARY,
        CANARY_MEMORY_TITLE,
        CANARY_NAMESPACE,
        CANARY_LEASE_TOKEN,
    ):
        require(canary not in output, "public_probe_canary_leak")
    for pattern in (
        r"/tmp/",
        r"slp-job-v0:",
        r"slp-dispatch-v0:",
        r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])",
        r"Traceback",
        r"OSError",
    ):
        require(re.search(pattern, output) is None, "public_probe_private_leak")
    require(completed.stderr == "", "public_probe_stderr")


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--public-probe":
        return public_probe()
    require(len(sys.argv) == 1, "unexpected_arguments")
    test_claimed_record()
    test_expired_claim()
    test_stale_fences()
    test_m3e_and_duplicate()
    test_m3g_lock_contention()
    test_m3h_lock_contention()
    test_recovery_states()
    test_diverged_controls()
    test_crash_points()
    test_determinism_and_identity_domains()
    test_source_boundaries()
    test_subprocess_content_leakage()
    print("Phase 6-C1 fault injection smoke: ok")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SmokeFailure, FixtureBuildError) as exc:
        print(f"Phase 6-C1 fault injection smoke: failed:{exc}", file=sys.stderr)
        raise SystemExit(1)
    except Exception:
        print(
            "Phase 6-C1 fault injection smoke: failed:unexpected_error",
            file=sys.stderr,
        )
        raise SystemExit(1)
