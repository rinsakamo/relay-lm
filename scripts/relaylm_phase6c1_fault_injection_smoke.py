#!/usr/bin/env python3
"""Fault-injection smoke scaffolding for the Phase 6-C1 Primary MEM worker."""
from __future__ import annotations

import ast
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

from relaylm.relaymem_primary_index_log_apply import apply_relaymem_primary_index_log_reconciliation
from relaylm.relaymem_primary_index_log_recovery_audit import audit_relaymem_primary_index_log_reconciliation_recovery
from relaylm.relaymem_slp_queue_state import RelayMEMSLPQueueTransitionRequest, build_relaymem_slp_queue_state_node_result
from scripts._relaylm_phase6c1_fault_fixtures import (
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
    """Content-free smoke failure."""


def require(condition: bool, reason_id: str) -> None:
    if not condition:
        raise SmokeFailure(reason_id)


def queue_request(record: Mapping[str, object], kind: str, **overrides: object) -> RelayMEMSLPQueueTransitionRequest:
    values: dict[str, object] = {
        "transition_kind": kind,
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


def private_values(fixture: Phase6C1FaultFixture) -> tuple[str, ...]:
    values = [CANARY_RAW_MESSAGE, CANARY_MEMORY_SUMMARY, CANARY_MEMORY_TITLE, CANARY_NAMESPACE, CANARY_LEASE_TOKEN]
    for root in (fixture.queue_root, fixture.store_root):
        if root is not None:
            values.append(str(root))
    record = fixture.canonical_record or {}
    for key in ("job_id", "dispatch_idempotency_key", "claim_owner", "lease_token"):
        value = record.get(key)
        if isinstance(value, str) and value:
            values.append(value)
    for key in ("page_relative_path", "page_digest", "memory_write_idempotency_key"):
        value = fixture.private_artifacts.get(key)
        if isinstance(value, str) and value:
            values.append(value)
    return tuple(dict.fromkeys(values))


def require_public_safe(value: object, fixture: Phase6C1FaultFixture, reason_id: str) -> None:
    text = json.dumps(value, ensure_ascii=True, sort_keys=True, default=str)
    require(all(private not in text for private in private_values(fixture)), reason_id)
    require("Traceback" not in text and "OSError" not in text, reason_id)


def require_reason(result: object, reason: str, reason_id: str) -> None:
    require(reason in getattr(result, "blocked_reasons", ()), reason_id)


def test_claimed_record() -> None:
    root: Path | None = None
    with build_claimed_job_fixture() as fixture:
        root = fixture.queue_root
        record = read_canonical_queue_record(fixture)
        require(record["state"] == "claimed", "claimed_state")
        require(int(record["claim_generation"]) >= 1, "claimed_generation")
        require(record["attempt_count"] == record["claim_generation"], "claimed_attempt_generation")
        require(bool(record["claim_owner"]) and bool(record["lease_token"]), "claimed_fence_missing")
        require(record["terminal_reason_id"] == "" and record["retry_not_before"] is None, "claimed_terminal_fields")
        claim = fixture.private_artifacts["claim_result"]
        require_public_safe(claim.to_log_dict(), fixture, "claimed_projection_leak")
        require_public_safe(build_relaymem_slp_queue_state_node_result(claim).to_log_dict(), fixture, "claimed_node_projection_leak")
        require(CANARY_RAW_MESSAGE not in repr(fixture), "fixture_repr_leak")
    require(root is not None and not root.exists(), "claimed_temp_cleanup")


def test_expired_claim() -> None:
    with build_expired_claim_fixture() as fixture:
        root, record = fixture.queue_root, fixture.canonical_record
        require(root is not None and record is not None, "expired_fixture_missing")
        operations = (
            queue_request(record, "renew_lease", claim_owner=record["claim_owner"], lease_token=record["lease_token"], lease_duration_seconds=30),
            queue_request(record, "retry_release", claim_owner=record["claim_owner"], lease_token=record["lease_token"], retry_class="transient_lock_contention", failure_class="resource_contention"),
            queue_request(record, "commit_terminal", claim_owner=record["claim_owner"], lease_token=record["lease_token"], terminal_state="succeeded", terminal_reason_id="primary_mem_durable_state_verified"),
        )
        for operation in operations:
            result = apply_queue_transition(root, operation)
            require(result.status == "not_ready", "expired_owner_operation_status")
            require_reason(result, "active_lease_expired_stale_recovery_required", "expired_owner_operation_reason")
            require_public_safe(result.to_log_dict(), fixture, "expired_projection_leak")
        stale_owner = apply_queue_transition(root, queue_request(record, "commit_terminal", claim_owner="phase6c1-stale-owner", lease_token=record["lease_token"], terminal_state="succeeded", terminal_reason_id="primary_mem_durable_state_verified"))
        require(stale_owner.status == "conflict", "expired_stale_owner_status")
        require_reason(stale_owner, "claim_owner_mismatch", "expired_stale_owner_reason")
        require_public_safe(stale_owner.to_log_dict(), fixture, "expired_stale_owner_projection")
        recovered = apply_queue_transition(root, queue_request(record, "stale_recovery", lease_token=record["lease_token"]))
        require(recovered.status == "applied" and recovered.durable_record is not None, "expired_recovery_status")
        require(recovered.durable_record["state"] == "queued", "expired_recovery_state")
        require_public_safe(recovered.to_log_dict(), fixture, "expired_recovery_projection")


def test_stale_fences() -> None:
    with build_stale_fence_fixture() as fixture:
        root = fixture.queue_root
        requests = fixture.private_artifacts["stale_requests"]
        require(root is not None and isinstance(requests, Mapping), "stale_fixture_missing")
        expected = {
            "revision": "record_revision_mismatch",
            "generation": "claim_generation_mismatch",
            "token": "lease_token_mismatch",
            "owner_terminal": "claim_owner_mismatch",
        }
        before = read_canonical_queue_record(fixture)
        for name, reason in expected.items():
            operation = requests[name]
            require(isinstance(operation, RelayMEMSLPQueueTransitionRequest), "stale_request_type")
            result = apply_queue_transition(root, operation)
            require(result.status == "conflict", f"stale_{name}_status")
            require_reason(result, reason, f"stale_{name}_reason")
            require(read_canonical_queue_record(fixture) == before, f"stale_{name}_mutation")
            require_public_safe(result.to_log_dict(), fixture, f"stale_{name}_projection")


def test_m3e_and_duplicate() -> None:
    root: Path | None = None
    with build_m3e_published_fixture() as fixture:
        root = fixture.store_root
        require(root is not None, "m3e_store_missing")
        result = fixture.private_artifacts["m3e_result"]
        page = root / str(fixture.private_artifacts["page_relative_path"])
        require(result["status"] == "applied" and page.is_file(), "m3e_publication")
        require(CANARY_MEMORY_SUMMARY in page.read_text(encoding="utf-8"), "m3e_private_content_missing")
        require_public_safe(result["projection"], fixture, "m3e_projection_leak")
    require(root is not None and not root.exists(), "m3e_temp_cleanup")
    with build_exact_duplicate_page_fixture() as fixture:
        root = fixture.store_root
        duplicate = fixture.private_artifacts["duplicate_m3e_result"]
        require(root is not None, "duplicate_store_missing")
        require(duplicate["status"] == "already_applied", "duplicate_status")
        require(duplicate["writes_memory"] is False and duplicate["idempotent_noop"] is True, "duplicate_idempotency")
        require(len(list((root / "memory/mem/primary/projects").glob("*.md"))) == 1, "duplicate_page_count")
        require_public_safe(duplicate["projection"], fixture, "duplicate_projection_leak")


def test_m3g_lock_contention() -> None:
    root: Path | None = None
    holder: Any = None
    with build_m3g_lock_contention_fixture() as fixture:
        root = fixture.store_root
        holder = fixture.private_artifacts["lock_holder"]
        plan = fixture.private_artifacts["m3f_plan"]
        require(root is not None, "m3g_lock_store_missing")
        before = snapshot_store(root)
        started = time.monotonic()
        blocked = apply_relaymem_primary_index_log_reconciliation(plan_artifact=plan, root_path=str(root), enabled=True, dry_run_only=False, apply_enabled=True)
        require(time.monotonic() - started < 2.0, "m3g_lock_blocked_too_long")
        require(blocked["status"] == "blocked", "m3g_lock_status")
        require("primary_reconciliation_apply_lock_unavailable" in blocked["blocked_reasons"], "m3g_lock_reason")
        require(snapshot_store(root) == before, "m3g_lock_mutation")
        require_public_safe(blocked["projection"], fixture, "m3g_lock_projection")
        holder.release()
        applied = apply_relaymem_primary_index_log_reconciliation(plan_artifact=plan, root_path=str(root), enabled=True, dry_run_only=False, apply_enabled=True)
        require(applied["status"] == "applied", "m3g_after_unlock_status")
        require_public_safe(applied["projection"], fixture, "m3g_after_unlock_projection")
    require(holder is not None and holder.running is False, "m3g_lock_process_leak")
    require(root is not None and not root.exists(), "m3g_lock_temp_cleanup")


def test_m3h_lock_contention() -> None:
    root: Path | None = None
    holder: Any = None
    with build_m3h_lock_contention_fixture() as fixture:
        root = fixture.store_root
        holder = fixture.private_artifacts["lock_holder"]
        receipt = fixture.private_artifacts["m3g_result"]["receipt"]
        require(root is not None, "m3h_lock_store_missing")
        before = snapshot_store(root)
        started = time.monotonic()
        blocked = audit_relaymem_primary_index_log_reconciliation_recovery(receipt=receipt, root_path=str(root), enabled=True, dry_run_only=True)
        require(time.monotonic() - started < 2.0, "m3h_lock_blocked_too_long")
        require(blocked["status"] == "blocked", "m3h_lock_status")
        require("primary_reconciliation_recovery_lock_unavailable" in blocked["blocked_reasons"], "m3h_lock_reason")
        require(blocked["recovery_classification"] != "recovery_not_required", "m3h_lock_false_success")
        require(snapshot_store(root) == before, "m3h_lock_mutation")
        require_public_safe(blocked["projection"], fixture, "m3h_lock_projection")
        holder.release()
        complete = audit_relaymem_primary_index_log_reconciliation_recovery(receipt=receipt, root_path=str(root), enabled=True, dry_run_only=True)
        require(complete["status"] == "recovery_not_required", "m3h_after_unlock_status")
        require_public_safe(complete["projection"], fixture, "m3h_after_unlock_projection")
    require(holder is not None and holder.running is False, "m3h_lock_process_leak")
    require(root is not None and not root.exists(), "m3h_lock_temp_cleanup")


def test_recovery_states() -> None:
    with build_index_applied_log_pending_fixture() as fixture:
        audit = fixture.private_artifacts["m3h_result"]
        require(audit["store_state"] == "index_applied_log_pending", "partial_store_state")
        require(audit["recovery_classification"] == "retry_reconciliation", "partial_recovery_class")
        require_public_safe(audit["projection"], fixture, "partial_projection_leak")
    with build_fully_reconciled_fixture() as fixture:
        audit = fixture.private_artifacts["m3h_result"]
        require(audit["status"] == "recovery_not_required", "full_audit_status")
        require(audit["store_state"] == "fully_reconciled", "full_store_state")
        require(audit["recovery_classification"] == "recovery_not_required", "full_recovery_class")
        require_public_safe(audit["projection"], fixture, "full_projection_leak")


def test_diverged_controls() -> None:
    for kind in ("page_digest_mismatch", "index_symlink"):
        with build_diverged_store_fixture(kind) as fixture:
            audit = fixture.private_artifacts["diverged_audit"]
            require(audit["status"] != "recovery_not_required", "diverged_false_success")
            require(audit["recovery_classification"] != "recovery_not_required", "diverged_false_class")
            if kind == "index_symlink":
                require(audit["status"] == "blocked", "diverged_symlink_status")
                require(any("symlink" in reason for reason in audit["blocked_reasons"]), "diverged_symlink_reason")
            require_public_safe(audit["projection"], fixture, "diverged_projection_leak")


def test_crash_points() -> None:
    observed: set[str] = set()
    roots: list[Path] = []
    for name in CRASH_POINT_NAMES:
        with build_crash_point_fixture(name) as fixture:
            observed.add(str(fixture.crash_point))
            require(fixture.private_artifacts.get("next_safe_operation") is not None, "crash_next_operation")
            require(fixture.private_artifacts.get("stale_operation_rejected_by") is not None, "crash_stale_fence")
            roots.extend(root for root in (fixture.queue_root, fixture.store_root) if root is not None)
            require_public_safe({"crash_point": fixture.crash_point, "expected_state": fixture.expected_state, "next_safe_operation": fixture.private_artifacts["next_safe_operation"]}, fixture, "crash_projection_leak")
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
    stores: list[tuple[str, str, str, bytes]] = []
    store_roots: list[Path] = []
    for _ in range(2):
        with build_m3e_published_fixture() as fixture:
            root = fixture.store_root
            require(root is not None, "deterministic_store_root")
            store_roots.append(root)
            relative = str(fixture.private_artifacts["page_relative_path"])
            stores.append((relative, str(fixture.private_artifacts["page_digest"]), str(fixture.private_artifacts["memory_write_idempotency_key"]), (root / relative).read_bytes()))
    require(stores[0] == stores[1], "store_fixture_nondeterministic")
    require(all(not root.exists() for root in store_roots), "store_fixture_cleanup")
    dispatch_key = str(queue_records[0]["dispatch_idempotency_key"])
    memory_key = stores[0][2]
    require(dispatch_key.startswith("slp-dispatch-v0:"), "dispatch_key_domain")
    require(len(memory_key) == 64 and ":" not in memory_key, "memory_key_domain")
    require(dispatch_key != memory_key and memory_key not in json.dumps(queue_records[0]), "idempotency_domains_mixed")


def test_source_boundaries() -> None:
    forbidden_modules = {"relaylm.relaymem_slp_primary_worker_source", "relaylm.relaymem_slp_primary_worker_outcome"}
    for path in (REPO_ROOT / "scripts/_relaylm_phase6c1_fault_fixtures.py", Path(__file__)):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.name)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                require(node.module not in forbidden_modules, "worker_boundary_imported")
            elif isinstance(node, ast.Import):
                require(all(alias.name not in forbidden_modules for alias in node.names), "worker_boundary_imported")
            elif isinstance(node, ast.Call):
                function = node.func
                if isinstance(function, ast.Name):
                    require(function.id != "execute_relaymem_primary_pipeline", "worker_boundary_invoked")
                elif isinstance(function, ast.Attribute):
                    require(not (isinstance(function.value, ast.Name) and function.value.id == "time" and function.attr == "sleep"), "sleep_boundary_invoked")


def public_probe() -> int:
    with build_claimed_job_fixture() as fixture:
        require_public_safe(fixture.private_artifacts["claim_result"].to_log_dict(), fixture, "probe_queue_projection")
    with build_fully_reconciled_fixture() as fixture:
        require_public_safe(fixture.private_artifacts["m3h_result"]["projection"], fixture, "probe_store_projection")
    print("Phase 6-C1 fault projection probe: ok")
    return 0


def test_subprocess_content_leakage() -> None:
    completed = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--public-probe"], cwd=str(REPO_ROOT), env={**os.environ, "PYTHONPATH": str(REPO_ROOT)}, capture_output=True, text=True, timeout=60, check=False)
    require(completed.returncode == 0, "public_probe_failed")
    output = completed.stdout + completed.stderr
    require(all(canary not in output for canary in (CANARY_RAW_MESSAGE, CANARY_MEMORY_SUMMARY, CANARY_MEMORY_TITLE, CANARY_NAMESPACE, CANARY_LEASE_TOKEN)), "public_probe_canary_leak")
    for pattern in (r"/tmp/", r"slp-job-v0:", r"slp-dispatch-v0:", r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])", r"Traceback", r"OSError"):
        require(re.search(pattern, output) is None, "public_probe_private_leak")
    require(completed.stderr == "", "public_probe_stderr")


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--public-probe":
        return public_probe()
    require(len(sys.argv) == 1, "unexpected_arguments")
    for test in (
        test_claimed_record,
        test_expired_claim,
        test_stale_fences,
        test_m3e_and_duplicate,
        test_m3g_lock_contention,
        test_m3h_lock_contention,
        test_recovery_states,
        test_diverged_controls,
        test_crash_points,
        test_determinism_and_identity_domains,
        test_source_boundaries,
        test_subprocess_content_leakage,
    ):
        test()
    print("Phase 6-C1 fault injection smoke: ok")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SmokeFailure, FixtureBuildError) as exc:
        print(f"Phase 6-C1 fault injection smoke: failed:{exc}", file=sys.stderr)
        raise SystemExit(1)
    except Exception:
        print("Phase 6-C1 fault injection smoke: failed:unexpected_error", file=sys.stderr)
        raise SystemExit(1)
