"""Reusable Phase 6-C1 fault fixtures built only from canonical helpers.

The module is test-only. It does not implement or import a worker, scheduler,
request-runtime wiring, protected-source production schema, or outcome mapper.
"""
from __future__ import annotations

import json
import os
import select
import subprocess
import sys
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Literal

import relaylm.relaymem_slp_durable_enqueue as durable_enqueue_module
import relaylm.relaymem_slp_queue_state as queue_state_module
from relaylm import _relaymem_primary_index_log_apply_io as apply_io
from relaylm.relaymem_primary_formation import build_relaymem_primary_formation_dry_run
from relaylm.relaymem_primary_index_log_apply import (
    apply_relaymem_primary_index_log_reconciliation,
)
from relaylm.relaymem_primary_index_log_reconciliation import (
    build_relaymem_primary_index_log_reconciliation_preflight,
)
from relaylm.relaymem_primary_index_log_recovery_audit import (
    audit_relaymem_primary_index_log_reconciliation_recovery,
)
from relaylm.relaymem_primary_page_candidate import (
    build_relaymem_governed_experience_summary,
    build_relaymem_primary_page_candidate_dry_run,
)
from relaylm.relaymem_primary_page_writer import apply_relaymem_primary_page_write
from relaylm.relaymem_primary_write_preflight import (
    build_relaymem_primary_source_lineage,
    build_relaymem_primary_write_preflight_dry_run,
)
from relaylm.relaymem_primary_writer_handoff import (
    build_relaymem_primary_writer_handoff_preflight,
)
from relaylm.relaymem_slp_dispatch_preflight import build_relaymem_slp_dispatch_preflight
from relaylm.relaymem_slp_durable_enqueue import enqueue_relaymem_slp_durable_job
from relaylm.relaymem_slp_job_admission import build_relaymem_slp_job_admission_preflight
from relaylm.relaymem_slp_queue_record import (
    parse_timestamp,
    record_filename,
    validate_record_mapping,
)
from relaylm.relaymem_slp_queue_state import (
    RelayMEMSLPQueueStateTransitionResult,
    RelayMEMSLPQueueTransitionRequest,
    transition_relaymem_slp_queue_state,
)
from relaylm.relaymem_slp_response_handoff import (
    build_relaymem_slp_response_finalization_handoff,
)

CANARY_RAW_MESSAGE = "CANARY_RAW_MESSAGE_DO_NOT_LEAK"
CANARY_MEMORY_SUMMARY = "CANARY_MEMORY_SUMMARY_DO_NOT_LEAK"
CANARY_MEMORY_TITLE = "CANARY_MEMORY_TITLE_DO_NOT_LEAK"
CANARY_NAMESPACE = "CANARY_NAMESPACE_DO_NOT_LEAK"
CANARY_LEASE_TOKEN = "CANARY_LEASE_TOKEN_DO_NOT_LEAK"
SECOND_LEASE_TOKEN = "phase6c1-lease-token-generation-2"
CANARY_CLAIM_OWNER = "phase6c1-worker-a"
SECOND_CLAIM_OWNER = "phase6c1-worker-b"
FIXED_CREATED_AT = "2026-06-23T00:00:00.000000Z"
FIXED_BASE_NOW = datetime(2026, 6, 23, 0, 0, tzinfo=timezone.utc)

CrashPointName = Literal[
    "after_claim_before_source",
    "after_m3e_before_m3f",
    "after_m3g_index_before_log",
    "after_reconciliation_before_terminal_commit",
    "during_lease_expiry_and_stale_recovery",
]

CRASH_POINT_NAMES: tuple[CrashPointName, ...] = (
    "after_claim_before_source",
    "after_m3e_before_m3f",
    "after_m3g_index_before_log",
    "after_reconciliation_before_terminal_commit",
    "during_lease_expiry_and_stale_recovery",
)


class FixtureBuildError(RuntimeError):
    """A content-free fixture construction failure."""


@dataclass(frozen=True, repr=False)
class Phase6C1FaultFixture:
    queue_root: Path | None = field(default=None, repr=False)
    store_root: Path | None = field(default=None, repr=False)
    canonical_record: dict[str, object] | None = field(default=None, repr=False)
    private_artifacts: Mapping[str, object] = field(default_factory=dict, repr=False)
    expected_state: str = "not_evaluated"
    crash_point: str | None = None

    def __repr__(self) -> str:
        return (
            "Phase6C1FaultFixture("
            f"expected_state={self.expected_state!r}, crash_point={self.crash_point!r})"
        )


class _ExclusiveMemLockHolder:
    """Separate-process holder for the production memory/mem directory flock."""

    _CHILD = r"""
import fcntl
import os
import sys
fd = os.open(sys.argv[1], os.O_RDONLY | os.O_DIRECTORY)
try:
    fcntl.flock(fd, fcntl.LOCK_EX)
    sys.stdout.write("ready\n")
    sys.stdout.flush()
    sys.stdin.buffer.read(1)
finally:
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)
"""

    def __init__(self, mem_root: Path) -> None:
        self._mem_root = mem_root
        self._process: subprocess.Popen[bytes] | None = None

    @property
    def running(self) -> bool:
        process = self._process
        return process is not None and process.poll() is None

    def start(self) -> None:
        if os.name != "posix":
            raise FixtureBuildError("phase6c1_lock_platform_unsupported")
        if self._process is not None:
            raise FixtureBuildError("phase6c1_lock_holder_already_started")
        process = subprocess.Popen(
            [sys.executable, "-c", self._CHILD, str(self._mem_root)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self._process = process
        stdout = process.stdout
        if stdout is None:
            self.release()
            raise FixtureBuildError("phase6c1_lock_holder_stdout_missing")
        ready, _, _ = select.select([stdout], [], [], 3.0)
        if not ready or stdout.readline() != b"ready\n":
            self.release()
            raise FixtureBuildError("phase6c1_lock_holder_not_ready")

    def release(self) -> None:
        process = self._process
        if process is None:
            return
        self._process = None
        try:
            if process.poll() is None and process.stdin is not None:
                try:
                    process.stdin.write(b"x")
                    process.stdin.flush()
                    process.stdin.close()
                except (BrokenPipeError, OSError):
                    pass
            try:
                process.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3.0)
        finally:
            if process.stdout is not None:
                process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()


@contextmanager
def _fixed_queue_runtime(now: datetime = FIXED_BASE_NOW) -> Iterator[None]:
    original_enqueue_now = durable_enqueue_module._utc_now
    original_queue_now = queue_state_module._now_utc
    original_token = queue_state_module._new_lease_token
    durable_enqueue_module._utc_now = lambda: FIXED_CREATED_AT
    queue_state_module._now_utc = lambda: now
    queue_state_module._new_lease_token = lambda: CANARY_LEASE_TOKEN
    try:
        yield
    finally:
        durable_enqueue_module._utc_now = original_enqueue_now
        queue_state_module._now_utc = original_queue_now
        queue_state_module._new_lease_token = original_token


def _require(condition: bool, reason_id: str) -> None:
    if not condition:
        raise FixtureBuildError(reason_id)


def _queue_request(
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


def apply_queue_transition(
    queue_root: Path,
    request: RelayMEMSLPQueueTransitionRequest,
) -> RelayMEMSLPQueueStateTransitionResult:
    return transition_relaymem_slp_queue_state(
        request,
        queue_root=str(queue_root),
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )


def read_canonical_queue_record(fixture: Phase6C1FaultFixture) -> dict[str, object]:
    queue_root = fixture.queue_root
    canonical = fixture.canonical_record
    if queue_root is None or canonical is None:
        raise FixtureBuildError("phase6c1_queue_fixture_missing")
    path = queue_root / record_filename(str(canonical["dispatch_idempotency_key"]))
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise FixtureBuildError("phase6c1_queue_record_unreadable") from None
    _require(isinstance(value, dict), "phase6c1_queue_record_shape_invalid")
    _require(not validate_record_mapping(value), "phase6c1_queue_record_invalid")
    return value


def snapshot_store(root: Path) -> dict[str, bytes]:
    snapshot: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            snapshot[path.relative_to(root).as_posix()] = path.read_bytes()
        elif path.is_symlink():
            snapshot[path.relative_to(root).as_posix()] = b"<symlink>"
        elif path != root and not path.is_dir():
            snapshot[path.relative_to(root).as_posix()] = b"<unsafe-type>"
    return snapshot


def _build_dispatch_preflight() -> object:
    lineage = build_relaymem_primary_source_lineage(
        source_event_kind="turn",
        run_id="phase6c1-run",
        turn_index=1,
        session_id="phase6c1-session",
        namespace=CANARY_NAMESPACE,
    )
    _require(lineage.get("valid") is True, "phase6c1_queue_lineage_invalid")
    admission = build_relaymem_slp_job_admission_preflight(
        enabled=True,
        dry_run_only=True,
        enqueue_enabled=False,
        trigger_mode="turn_end",
        processing_stage="primary_formation",
        run_id="phase6c1-run",
        turn_index=1,
        session_id="phase6c1-session",
        namespace=CANARY_NAMESPACE,
        source_event_kind="turn",
        source_lineage_artifact=lineage,
        source_count=1,
        visible_response_finalized=True,
        runtime_terminal_status="completed",
        persistence_policy_status="allowed",
    )
    handoff = build_relaymem_slp_response_finalization_handoff(
        admission,
        enabled=True,
        dry_run_only=True,
        response_finalized=True,
    )
    preflight = build_relaymem_slp_dispatch_preflight(
        handoff,
        enabled=True,
        dry_run_only=True,
    )
    _require(
        getattr(preflight, "status", None) == "dry_run_ready",
        "phase6c1_b1_preflight_not_ready",
    )
    return preflight


def _prepare_claimed_record(
    queue_root: Path,
    *,
    lease_seconds: int = 30,
    claim_owner: str = CANARY_CLAIM_OWNER,
) -> tuple[dict[str, object], Mapping[str, object]]:
    enqueue = enqueue_relaymem_slp_durable_job(
        _build_dispatch_preflight(),
        queue_root=str(queue_root),
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )
    _require(enqueue.status == "enqueued_new", "phase6c1_enqueue_failed")
    queued = enqueue.durable_record
    _require(isinstance(queued, dict), "phase6c1_enqueued_record_missing")
    claim = apply_queue_transition(
        queue_root,
        _queue_request(
            queued,
            "claim",
            claim_owner=claim_owner,
            lease_duration_seconds=lease_seconds,
        ),
    )
    _require(claim.status == "applied", "phase6c1_claim_failed")
    claimed = claim.durable_record
    _require(isinstance(claimed, dict), "phase6c1_claimed_record_missing")
    _require(not validate_record_mapping(claimed), "phase6c1_claimed_record_invalid")
    _require(claimed["state"] == "claimed", "phase6c1_claimed_state_invalid")
    _require(int(claimed["claim_generation"]) >= 1, "phase6c1_claim_generation_invalid")
    _require(
        claimed["attempt_count"] == claimed["claim_generation"],
        "phase6c1_attempt_generation_mismatch",
    )
    _require(bool(claimed["claim_owner"]), "phase6c1_claim_owner_missing")
    _require(bool(claimed["lease_token"]), "phase6c1_lease_token_missing")
    acquired = parse_timestamp(claimed["lease_acquired_at"])
    expires = parse_timestamp(claimed["lease_expires_at"])
    _require(
        acquired is not None and expires is not None and acquired < expires,
        "phase6c1_lease_interval_invalid",
    )
    _require(claimed["terminal_reason_id"] == "", "phase6c1_terminal_reason_nonempty")
    _require(claimed["retry_not_before"] is None, "phase6c1_retry_not_before_nonnull")
    return claimed, {"enqueue_result": enqueue, "claim_result": claim}


@contextmanager
def build_claimed_job_fixture() -> Iterator[Phase6C1FaultFixture]:
    with TemporaryDirectory(prefix="relaylm-phase6c1-queue-") as temporary:
        queue_root = Path(temporary).resolve()
        with _fixed_queue_runtime():
            claimed, artifacts = _prepare_claimed_record(queue_root)
            queue_state_module._now_utc = lambda: FIXED_BASE_NOW + timedelta(seconds=1)
            yield Phase6C1FaultFixture(
                queue_root=queue_root,
                canonical_record=claimed,
                private_artifacts=artifacts,
                expected_state="claimed_active",
            )


@contextmanager
def build_expired_claim_fixture() -> Iterator[Phase6C1FaultFixture]:
    with TemporaryDirectory(prefix="relaylm-phase6c1-expired-") as temporary:
        queue_root = Path(temporary).resolve()
        with _fixed_queue_runtime():
            claimed, artifacts = _prepare_claimed_record(queue_root, lease_seconds=5)
            expiry = parse_timestamp(claimed["lease_expires_at"])
            _require(expiry is not None, "phase6c1_expiry_missing")
            queue_state_module._now_utc = lambda: expiry
            yield Phase6C1FaultFixture(
                queue_root=queue_root,
                canonical_record=claimed,
                private_artifacts={**artifacts, "expired_at": expiry},
                expected_state="claimed_lease_expired",
            )


@contextmanager
def build_stale_fence_fixture() -> Iterator[Phase6C1FaultFixture]:
    with TemporaryDirectory(prefix="relaylm-phase6c1-stale-") as temporary:
        queue_root = Path(temporary).resolve()
        with _fixed_queue_runtime():
            first, artifacts = _prepare_claimed_record(queue_root, lease_seconds=5)
            first_revision = int(first["record_revision"])
            first_generation = int(first["claim_generation"])
            first_token = str(first["lease_token"])
            expiry = parse_timestamp(first["lease_expires_at"])
            _require(expiry is not None, "phase6c1_stale_expiry_missing")
            queue_state_module._now_utc = lambda: expiry
            recovery = apply_queue_transition(
                queue_root,
                _queue_request(first, "stale_recovery", lease_token=first_token),
            )
            _require(recovery.status == "applied", "phase6c1_stale_recovery_failed")
            recovered = recovery.durable_record
            _require(isinstance(recovered, dict), "phase6c1_recovered_record_missing")
            queue_state_module._now_utc = lambda: expiry + timedelta(seconds=1)
            queue_state_module._new_lease_token = lambda: SECOND_LEASE_TOKEN
            second_claim = apply_queue_transition(
                queue_root,
                _queue_request(
                    recovered,
                    "claim",
                    claim_owner=SECOND_CLAIM_OWNER,
                    lease_duration_seconds=30,
                ),
            )
            _require(second_claim.status == "applied", "phase6c1_reclaim_failed")
            current = second_claim.durable_record
            _require(isinstance(current, dict), "phase6c1_reclaimed_record_missing")
            stale_requests = {
                "revision": _queue_request(
                    first,
                    "renew_lease",
                    claim_owner=CANARY_CLAIM_OWNER,
                    lease_token=first_token,
                    lease_duration_seconds=30,
                ),
                "generation": _queue_request(
                    current,
                    "renew_lease",
                    claim_owner=SECOND_CLAIM_OWNER,
                    claim_generation=first_generation,
                    lease_token=current["lease_token"],
                    lease_duration_seconds=30,
                ),
                "token": _queue_request(
                    current,
                    "renew_lease",
                    claim_owner=SECOND_CLAIM_OWNER,
                    lease_token=first_token,
                    lease_duration_seconds=30,
                ),
                "owner_terminal": _queue_request(
                    current,
                    "commit_terminal",
                    claim_owner=CANARY_CLAIM_OWNER,
                    lease_token=current["lease_token"],
                    terminal_state="succeeded",
                    terminal_reason_id="primary_mem_durable_state_verified",
                ),
            }
            _require(
                first_revision < int(current["record_revision"]),
                "phase6c1_revision_not_advanced",
            )
            _require(
                first_generation < int(current["claim_generation"]),
                "phase6c1_generation_not_advanced",
            )
            _require(first_token != current["lease_token"], "phase6c1_token_not_rotated")
            yield Phase6C1FaultFixture(
                queue_root=queue_root,
                canonical_record=current,
                private_artifacts={
                    **artifacts,
                    "stale_recovery_result": recovery,
                    "second_claim_result": second_claim,
                    "stale_requests": stale_requests,
                    "stale_record": first,
                },
                expected_state="reclaimed_with_stale_fences",
            )


def _prepare_store_layout(store_root: Path) -> None:
    (store_root / "memory/mem/primary/projects").mkdir(parents=True, exist_ok=True)
    mem_root = store_root / "memory/mem"
    (mem_root / "index.md").write_text("# Index\n", encoding="utf-8")
    (mem_root / "log.md").write_text("# Log\n", encoding="utf-8")


def _prepare_m3e_publication(store_root: Path) -> Mapping[str, object]:
    _prepare_store_layout(store_root)
    scene = {
        "scene_state": {
            "scene_type": "design_talk",
            "confidence": 0.92,
            "stability": 0.88,
        },
        "scene_policy": {
            "relaymem_retrieval_scope": "project_context",
            "persistence_block": False,
            "persistence_block_reasons": [],
        },
        "persistence_block": False,
        "persistence_block_reasons": [],
    }
    formation = build_relaymem_primary_formation_dry_run(
        relayscn_scene_policy_artifact=scene,
        relayemo_artifact={"assistant_emotion_state": {"intensity": 0.81}},
        messages=[
            {"role": "assistant", "content": "bounded prior response"},
            {"role": "user", "content": CANARY_RAW_MESSAGE},
        ],
        enabled=True,
    )
    _require(formation.get("candidate_count") == 1, "phase6c1_m3a_candidate_missing")
    candidate = formation["candidates"][0]
    lineage = build_relaymem_primary_source_lineage(
        source_event_kind="turn",
        run_id="phase6c1-memory-run",
        turn_index=1,
        session_id="phase6c1-memory-session",
        namespace=CANARY_NAMESPACE,
    )
    _require(lineage.get("valid") is True, "phase6c1_m3b_lineage_invalid")
    write_preflight = build_relaymem_primary_write_preflight_dry_run(
        candidates=[candidate],
        source_lineage_artifact=lineage,
        enabled=True,
    )
    _require(
        write_preflight.get("operation_count") == 1,
        "phase6c1_m3b_operation_missing",
    )
    governed = build_relaymem_governed_experience_summary(
        candidate_id=candidate["candidate_id"],
        source_event_kind=candidate["source_event_kind"],
        namespace=CANARY_NAMESPACE,
        title=CANARY_MEMORY_TITLE,
        summary_text=CANARY_MEMORY_SUMMARY,
    )
    _require(governed.get("valid") is True, "phase6c1_governed_experience_invalid")
    page_candidate = build_relaymem_primary_page_candidate_dry_run(
        preflight_artifact=write_preflight,
        source_lineage_artifact=lineage,
        governed_experience_artifact=governed,
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )
    _require(
        page_candidate.get("page_candidate_count") == 1,
        "phase6c1_m3c_page_missing",
    )
    writer_handoff = build_relaymem_primary_writer_handoff_preflight(
        page_candidate_artifact=page_candidate,
        root_path=str(store_root),
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )
    _require(writer_handoff.get("handoff_count") == 1, "phase6c1_m3d_handoff_missing")
    m3e_result = apply_relaymem_primary_page_write(
        writer_handoff_artifact=writer_handoff,
        root_path=str(store_root),
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )
    _require(m3e_result.get("status") == "applied", "phase6c1_m3e_apply_failed")
    handoff = writer_handoff["handoffs"][0]
    page_path = store_root / handoff["target_relative_path"]
    _require(page_path.is_file(), "phase6c1_m3e_page_missing")
    return {
        "formation": formation,
        "lineage": lineage,
        "write_preflight": write_preflight,
        "governed_experience": governed,
        "page_candidate": page_candidate,
        "writer_handoff": writer_handoff,
        "m3e_result": m3e_result,
        "page_relative_path": handoff["target_relative_path"],
        "page_digest": handoff["page_digest"],
        "memory_write_idempotency_key": handoff["idempotency_key"],
    }


@contextmanager
def build_m3e_published_fixture() -> Iterator[Phase6C1FaultFixture]:
    with TemporaryDirectory(prefix="relaylm-phase6c1-store-") as temporary:
        store_root = Path(temporary).resolve()
        artifacts = _prepare_m3e_publication(store_root)
        yield Phase6C1FaultFixture(
            store_root=store_root,
            private_artifacts=artifacts,
            expected_state="page_published_control_pending",
        )


@contextmanager
def build_exact_duplicate_page_fixture() -> Iterator[Phase6C1FaultFixture]:
    with build_m3e_published_fixture() as published:
        store_root = published.store_root
        _require(store_root is not None, "phase6c1_duplicate_store_missing")
        duplicate = apply_relaymem_primary_page_write(
            writer_handoff_artifact=published.private_artifacts["writer_handoff"],
            root_path=str(store_root),
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
        _require(
            duplicate.get("status") == "already_applied",
            "phase6c1_duplicate_not_idempotent",
        )
        yield replace(
            published,
            private_artifacts={
                **published.private_artifacts,
                "duplicate_m3e_result": duplicate,
            },
            expected_state="exact_duplicate_page",
        )


def _build_m3f_plan(
    store_root: Path,
    m3e_result: Mapping[str, object],
) -> tuple[Mapping[str, object], Mapping[str, object]]:
    receipt = m3e_result.get("receipt")
    _require(isinstance(receipt, Mapping), "phase6c1_m3e_receipt_missing")
    m3f = build_relaymem_primary_index_log_reconciliation_preflight(
        receipt=receipt,
        root_path=str(store_root),
        enabled=True,
        dry_run_only=True,
    )
    plan = m3f.get("plan")
    _require(isinstance(plan, Mapping), "phase6c1_m3f_plan_missing")
    return m3f, plan


def _apply_m3g(
    store_root: Path,
    plan: Mapping[str, object],
) -> Mapping[str, object]:
    return apply_relaymem_primary_index_log_reconciliation(
        plan_artifact=plan,
        root_path=str(store_root),
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )


def _audit_m3h(
    store_root: Path,
    receipt: Mapping[str, object],
) -> Mapping[str, object]:
    return audit_relaymem_primary_index_log_reconciliation_recovery(
        receipt=receipt,
        root_path=str(store_root),
        enabled=True,
        dry_run_only=True,
    )


@contextmanager
def build_m3g_lock_contention_fixture() -> Iterator[Phase6C1FaultFixture]:
    with build_m3e_published_fixture() as published:
        store_root = published.store_root
        _require(store_root is not None, "phase6c1_m3g_lock_store_missing")
        m3f, plan = _build_m3f_plan(
            store_root,
            published.private_artifacts["m3e_result"],
        )
        lock_holder = _ExclusiveMemLockHolder(store_root / "memory/mem")
        lock_holder.start()
        try:
            yield replace(
                published,
                private_artifacts={
                    **published.private_artifacts,
                    "m3f_result": m3f,
                    "m3f_plan": plan,
                    "lock_holder": lock_holder,
                },
                expected_state="m3g_exclusive_lock_contended",
            )
        finally:
            lock_holder.release()


@contextmanager
def build_index_applied_log_pending_fixture() -> Iterator[Phase6C1FaultFixture]:
    with build_m3e_published_fixture() as published:
        store_root = published.store_root
        _require(store_root is not None, "phase6c1_partial_store_missing")
        m3f, plan = _build_m3f_plan(
            store_root,
            published.private_artifacts["m3e_result"],
        )
        original_replace = apply_io.os.replace
        calls = 0

        def fail_second_replace(*args: object, **kwargs: object) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("phase6c1_injected_log_replace_failure")
            original_replace(*args, **kwargs)

        apply_io.os.replace = fail_second_replace
        try:
            partial = _apply_m3g(store_root, plan)
        finally:
            apply_io.os.replace = original_replace
        _require(
            partial.get("status") == "index_applied_log_pending",
            "phase6c1_partial_state_not_created",
        )
        receipt = partial.get("receipt")
        _require(isinstance(receipt, Mapping), "phase6c1_partial_receipt_missing")
        audit = _audit_m3h(store_root, receipt)
        _require(
            audit.get("store_state") == "index_applied_log_pending",
            "phase6c1_partial_store_state_invalid",
        )
        _require(
            audit.get("recovery_classification") == "retry_reconciliation",
            "phase6c1_partial_recovery_class_invalid",
        )
        yield replace(
            published,
            private_artifacts={
                **published.private_artifacts,
                "m3f_result": m3f,
                "m3f_plan": plan,
                "m3g_result": partial,
                "m3h_result": audit,
            },
            expected_state="index_applied_log_pending",
        )


@contextmanager
def build_fully_reconciled_fixture() -> Iterator[Phase6C1FaultFixture]:
    with build_m3e_published_fixture() as published:
        store_root = published.store_root
        _require(store_root is not None, "phase6c1_full_store_missing")
        m3f, plan = _build_m3f_plan(
            store_root,
            published.private_artifacts["m3e_result"],
        )
        applied = _apply_m3g(store_root, plan)
        _require(applied.get("status") == "applied", "phase6c1_m3g_apply_failed")
        receipt = applied.get("receipt")
        _require(isinstance(receipt, Mapping), "phase6c1_m3g_receipt_missing")
        audit = _audit_m3h(store_root, receipt)
        _require(
            audit.get("status") == "recovery_not_required",
            "phase6c1_full_audit_status_invalid",
        )
        _require(
            audit.get("recovery_classification") == "recovery_not_required",
            "phase6c1_full_recovery_class_invalid",
        )
        yield replace(
            published,
            private_artifacts={
                **published.private_artifacts,
                "m3f_result": m3f,
                "m3f_plan": plan,
                "m3g_result": applied,
                "m3h_result": audit,
            },
            expected_state="fully_reconciled",
        )


@contextmanager
def build_m3h_lock_contention_fixture() -> Iterator[Phase6C1FaultFixture]:
    with build_fully_reconciled_fixture() as reconciled:
        store_root = reconciled.store_root
        _require(store_root is not None, "phase6c1_m3h_lock_store_missing")
        lock_holder = _ExclusiveMemLockHolder(store_root / "memory/mem")
        lock_holder.start()
        try:
            yield replace(
                reconciled,
                private_artifacts={
                    **reconciled.private_artifacts,
                    "lock_holder": lock_holder,
                },
                expected_state="m3h_shared_lock_contended",
            )
        finally:
            lock_holder.release()


@contextmanager
def build_diverged_store_fixture(
    kind: Literal["page_digest_mismatch", "index_symlink"] = "page_digest_mismatch",
) -> Iterator[Phase6C1FaultFixture]:
    with build_fully_reconciled_fixture() as reconciled:
        store_root = reconciled.store_root
        _require(store_root is not None, "phase6c1_diverged_store_missing")
        if kind == "page_digest_mismatch":
            page_relative = str(reconciled.private_artifacts["page_relative_path"])
            (store_root / page_relative).write_text("diverged", encoding="utf-8")
        elif kind == "index_symlink":
            index_path = store_root / "memory/mem/index.md"
            outside = store_root / "outside-index.md"
            outside.write_text("# Index\n", encoding="utf-8")
            index_path.unlink()
            index_path.symlink_to(outside)
        else:  # pragma: no cover - Literal callers
            raise FixtureBuildError("phase6c1_diverged_kind_invalid")
        receipt = reconciled.private_artifacts["m3g_result"].get("receipt")
        _require(isinstance(receipt, Mapping), "phase6c1_diverged_receipt_missing")
        audit = _audit_m3h(store_root, receipt)
        yield replace(
            reconciled,
            private_artifacts={
                **reconciled.private_artifacts,
                "diverged_kind": kind,
                "diverged_audit": audit,
            },
            expected_state=f"diverged:{kind}",
        )


@contextmanager
def build_crash_point_fixture(name: CrashPointName) -> Iterator[Phase6C1FaultFixture]:
    _require(name in CRASH_POINT_NAMES, "phase6c1_crash_point_invalid")
    if name == "after_claim_before_source":
        with build_claimed_job_fixture() as claimed:
            yield replace(
                claimed,
                crash_point=name,
                private_artifacts={
                    **claimed.private_artifacts,
                    "next_safe_operation": "validate_exact_protected_source",
                    "stale_operation_rejected_by": (
                        "record_revision",
                        "claim_generation",
                        "lease_token",
                    ),
                },
            )
        return
    if name == "after_m3e_before_m3f":
        with build_claimed_job_fixture() as claimed, build_m3e_published_fixture() as published:
            yield Phase6C1FaultFixture(
                queue_root=claimed.queue_root,
                store_root=published.store_root,
                canonical_record=claimed.canonical_record,
                private_artifacts={
                    **claimed.private_artifacts,
                    **published.private_artifacts,
                    "next_safe_operation": "rerun_m3f_from_exact_m3e_receipt",
                    "stale_operation_rejected_by": (
                        "record_revision",
                        "claim_generation",
                        "lease_token",
                    ),
                },
                expected_state="page_published_control_pending",
                crash_point=name,
            )
        return
    if name == "after_m3g_index_before_log":
        with build_claimed_job_fixture() as claimed, build_index_applied_log_pending_fixture() as partial:
            yield Phase6C1FaultFixture(
                queue_root=claimed.queue_root,
                store_root=partial.store_root,
                canonical_record=claimed.canonical_record,
                private_artifacts={
                    **claimed.private_artifacts,
                    **partial.private_artifacts,
                    "next_safe_operation": "retry_reconciliation",
                    "stale_operation_rejected_by": (
                        "record_revision",
                        "claim_generation",
                        "lease_token",
                    ),
                },
                expected_state="index_applied_log_pending",
                crash_point=name,
            )
        return
    if name == "after_reconciliation_before_terminal_commit":
        with build_claimed_job_fixture() as claimed, build_fully_reconciled_fixture() as reconciled:
            yield Phase6C1FaultFixture(
                queue_root=claimed.queue_root,
                store_root=reconciled.store_root,
                canonical_record=claimed.canonical_record,
                private_artifacts={
                    **claimed.private_artifacts,
                    **reconciled.private_artifacts,
                    "next_safe_operation": "revalidate_lease_then_terminal_commit",
                    "stale_operation_rejected_by": (
                        "record_revision",
                        "claim_generation",
                        "lease_token",
                        "lease_expiry",
                    ),
                },
                expected_state="fully_reconciled_claimed",
                crash_point=name,
            )
        return
    with build_expired_claim_fixture() as expired:
        yield replace(
            expired,
            crash_point=name,
            private_artifacts={
                **expired.private_artifacts,
                "next_safe_operation": "stale_recovery",
                "stale_operation_rejected_by": (
                    "lease_expiry",
                    "record_revision",
                    "claim_generation",
                    "lease_token",
                ),
            },
        )


__all__ = [
    "CANARY_CLAIM_OWNER",
    "CANARY_LEASE_TOKEN",
    "SECOND_LEASE_TOKEN",
    "CANARY_MEMORY_SUMMARY",
    "CANARY_MEMORY_TITLE",
    "CANARY_NAMESPACE",
    "CANARY_RAW_MESSAGE",
    "CRASH_POINT_NAMES",
    "FixtureBuildError",
    "Phase6C1FaultFixture",
    "apply_queue_transition",
    "build_claimed_job_fixture",
    "build_crash_point_fixture",
    "build_diverged_store_fixture",
    "build_exact_duplicate_page_fixture",
    "build_expired_claim_fixture",
    "build_fully_reconciled_fixture",
    "build_index_applied_log_pending_fixture",
    "build_m3e_published_fixture",
    "build_m3g_lock_contention_fixture",
    "build_m3h_lock_contention_fixture",
    "build_stale_fence_fixture",
    "read_canonical_queue_record",
    "snapshot_store",
]
