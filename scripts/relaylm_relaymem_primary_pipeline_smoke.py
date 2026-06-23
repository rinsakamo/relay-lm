from __future__ import annotations

import io
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.relaymem_primary_page_candidate import (
    build_relaymem_governed_experience_summary,
)
from relaylm.relaymem_primary_pipeline import (
    REQUEST_SCHEMA,
    STAGES,
    RelayMEMPrimaryPipelineRequest,
    build_relaymem_primary_pipeline_node_result,
    execute_relaymem_primary_pipeline,
    project_relaymem_primary_pipeline,
)
from relaylm.relaymem_primary_write_preflight import (
    build_relaymem_primary_write_preflight_dry_run as real_m3b,
)
from relaylm.relaymem_primary_page_candidate import (
    build_relaymem_primary_page_candidate_dry_run as real_m3c,
)
from relaylm.relaymem_slp_primary_worker_source import (
    SOURCE_SCHEMA,
    RelayMEMSLPPrimaryWorkerSourceScope,
    build_relaymem_slp_primary_worker_source,
)
from relaylm.relaymem_slp_queue_record import (
    DISPATCH_KEY_VERSION,
    DURABLE_JOB_SCHEMA,
    derive_dispatch_key,
    derive_job_id,
    format_timestamp,
)

CANARY_SOURCE = "CANARY_PRIMARY_SOURCE_MESSAGE_DO_NOT_LEAK"
CANARY_SUMMARY = "CANARY_PRIMARY_SUMMARY_DO_NOT_LEAK"
CANARY_NAMESPACE = "CANARY_PRIMARY_NAMESPACE_DO_NOT_LEAK"
CANARY_MEMORY_KEY = "CANARY_MEMORY_WRITE_KEY_DO_NOT_LEAK"
CANARY_STORE_PATH = "CANARY_STORE_PATH_DO_NOT_LEAK"
LINEAGE = "a" * 64


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def claimed_record(*, run_id: str = "run-c1-compose", namespace: str = CANARY_NAMESPACE) -> dict[str, object]:
    now = datetime(2026, 6, 23, 0, 0, 0, tzinfo=timezone.utc)
    record: dict[str, object] = {
        "schema_version": DURABLE_JOB_SCHEMA,
        "job_id": "",
        "dispatch_idempotency_key": "",
        "dispatch_key_version": DISPATCH_KEY_VERSION,
        "candidate_schema_version": "relaymem.slp_enqueue_candidate.v0",
        "candidate_kind": "relayslp_deferred_job",
        "trigger_mode": "turn_end",
        "processing_stage": "primary_formation",
        "source_event_kind": "turn",
        "run_id": run_id,
        "turn_index": 7,
        "session_id": "session-c1-compose",
        "namespace": namespace,
        "source_count": 1,
        "source_lineage_fingerprint": LINEAGE,
        "source_admission_status": "admitted_dry_run",
        "runtime_terminal_status": "completed",
        "persistence_policy_status": "allowed",
        "state": "claimed",
        "record_revision": 1,
        "created_at": format_timestamp(now),
        "updated_at": format_timestamp(now),
        "attempt_count": 1,
        "claim_generation": 1,
        "claim_owner": "worker-c1-compose",
        "lease_token": "lease-c1-compose-secret",
        "lease_acquired_at": format_timestamp(now),
        "lease_expires_at": format_timestamp(now + timedelta(minutes=5)),
        "retry_class": "unclassified",
        "retry_not_before": None,
        "failure_class": "none",
        "terminal_reason_id": "",
    }
    record["dispatch_idempotency_key"] = derive_dispatch_key(record)
    record["job_id"] = derive_job_id(str(record["dispatch_idempotency_key"]))
    return record


def source_payload(record: dict[str, object], *, scene_type: str = "design_talk") -> dict[str, object]:
    blocked = scene_type in {"formal_document", "medical_or_safety", "recovery"}
    return {
        "schema_version": SOURCE_SCHEMA,
        "runtime_private": True,
        "content_included": True,
        "job_id": record["job_id"],
        "dispatch_idempotency_key": record["dispatch_idempotency_key"],
        "run_id": record["run_id"],
        "turn_index": record["turn_index"],
        "session_id": record["session_id"],
        "namespace": record["namespace"],
        "source_event_kind": record["source_event_kind"],
        "source_count": record["source_count"],
        "source_lineage_fingerprint": record["source_lineage_fingerprint"],
        "relayscn_scene_policy_artifact": {
            "scene_state": {
                "scene_type": scene_type,
                "confidence": 0.92,
                "stability": 0.89,
            },
            "scene_policy": {
                "relaymem_retrieval_scope": "project_context",
                "persistence_block": blocked,
                "persistence_block_reasons": [f"scene_policy_blocks_persistence:{scene_type}"] if blocked else [],
            },
            "persistence_block": blocked,
            "persistence_block_reasons": [f"scene_policy_blocks_persistence:{scene_type}"] if blocked else [],
        },
        "relayemo_artifact": {
            "assistant_emotion_state": {"intensity": 0.67},
            "user_affect_estimate": {"confidence": 0.71, "mode": "engaged"},
        },
        "governed_messages": [
            {"role": "system", "content": "governed system context"},
            {"role": "user", "content": CANARY_SOURCE},
            {"role": "assistant", "content": "I will retain the bounded project evidence."},
        ],
        "governed_experience_artifact": build_relaymem_governed_experience_summary(
            candidate_id="primary_candidate:0",
            source_event_kind="turn",
            namespace=str(record["namespace"]),
            title="Compose smoke",
            summary_text=CANARY_SUMMARY,
        ),
    }


def create_request(
    root: Path,
    *,
    scene_type: str = "design_talk",
    enabled: bool = True,
    dry_run_only: bool = False,
    apply_enabled: bool = True,
    record: dict[str, object] | None = None,
) -> tuple[RelayMEMPrimaryPipelineRequest, dict[str, object]]:
    canonical = record or claimed_record()
    scope = RelayMEMSLPPrimaryWorkerSourceScope()
    built = build_relaymem_slp_primary_worker_source(
        source_payload(canonical, scene_type=scene_type),
        claimed_record=canonical,
        request_scope=scope,
        enabled=enabled,
        dry_run_only=dry_run_only,
        apply_enabled=apply_enabled,
    )
    require(built.source is not None, built.to_log_dict())
    return RelayMEMPrimaryPipelineRequest(
        schema_version=REQUEST_SCHEMA,
        runtime_private=True,
        content_included=True,
        worker_source=built.source,
        claimed_record=canonical,
        request_scope=scope,
        store_root=str(root),
        enabled=enabled,
        dry_run_only=dry_run_only,
        apply_enabled=apply_enabled,
    ), canonical


def prepare_store(root: Path) -> None:
    for category in ("projects", "relationships", "sessions", "scenes"):
        (root / f"memory/mem/primary/{category}").mkdir(parents=True, exist_ok=True)
    (root / "memory/mem/index.md").write_text("# Index\n", encoding="utf-8")
    (root / "memory/mem/log.md").write_text("# Log\n", encoding="utf-8")


def assert_stage_order(result: object) -> None:
    stages = tuple(item.stage for item in result.stage_results)
    require(stages == STAGES, stages)
    completed_indexes = [STAGES.index(item.stage) for item in result.stage_results if item.completed]
    require(completed_indexes == sorted(completed_indexes), completed_indexes)


def assert_content_free(value: object, *, root: Path | None = None, actual_key: str | None = None) -> None:
    text = repr(value)
    forbidden = {
        CANARY_SOURCE,
        CANARY_SUMMARY,
        CANARY_NAMESPACE,
        CANARY_MEMORY_KEY,
        LINEAGE,
        "run-c1-compose",
        "session-c1-compose",
        "lease-c1-compose-secret",
        "slp-dispatch-v0:",
        "slp-job-v0:",
        "memory/mem/",
    }
    if root is not None:
        forbidden.add(str(root))
    if actual_key:
        forbidden.add(actual_key)
    for token in forbidden:
        require(token not in text, "content-free surface leaked protected data")


def fake_m3e_blocked(reason: str) -> dict[str, object]:
    return {
        "schema_version": "relaymem.primary_page_write_apply.v0",
        "helper_only": True,
        "runtime_private_receipt": True,
        "enabled": True,
        "dry_run_only": False,
        "apply_enabled": True,
        "write_apply_supported": True,
        "apply_requested": True,
        "handoff_valid": True,
        "status": "blocked",
        "writes_memory": False,
        "page_applied": False,
        "idempotent_noop": False,
        "durability_confirmed": False,
        "cleanup_complete": True,
        "updates_index": False,
        "updates_log": False,
        "mutates_soul": False,
        "invokes_slp": False,
        "lab_api_exposed": False,
        "runtime_wired": False,
        "visible_response_changed": False,
        "receipt": None,
        "blocked_reasons": [reason],
        "projection": {},
    }


def fake_m3g(*, status: str, reason: str | None = None) -> dict[str, object]:
    return {
        "schema_version": "relaymem.primary_index_log_reconciliation_apply.v0",
        "helper_only": True,
        "runtime_private_receipt": True,
        "enabled": True,
        "dry_run_only": False,
        "apply_enabled": True,
        "apply_supported": True,
        "apply_requested": True,
        "plan_valid": True,
        "page_verified": True,
        "status": status,
        "writes_memory": status != "blocked",
        "index_reconciled": status != "blocked",
        "log_reconciled": status in {"applied", "already_applied"},
        "index_updated": status == "applied",
        "log_updated": status == "applied",
        "index_idempotent_noop": status == "already_applied",
        "log_idempotent_noop": status == "already_applied",
        "durability_confirmed": status in {"applied", "already_applied"},
        "cleanup_complete": True,
        "updates_index": status == "applied",
        "updates_log": status == "applied",
        "mutates_soul": False,
        "invokes_slp": False,
        "runtime_wired": False,
        "lab_api_exposed": False,
        "visible_response_changed": False,
        "receipt": None if status == "blocked" else {"schema_version": "test-private-receipt"},
        "blocked_reasons": [reason] if reason else [],
        "projection": {},
    }


def fake_m3h(classification: str, *, reason: str | None = None) -> dict[str, object]:
    return {
        "schema_version": "relaymem.primary_index_log_reconciliation_recovery_audit_result.v0",
        "helper_only": True,
        "runtime_private_audit": True,
        "enabled": True,
        "dry_run_only": True,
        "read_only": True,
        "audit_supported": True,
        "receipt_valid": True,
        "status": classification,
        "source_status": "index_applied_log_pending" if classification == "retry_reconciliation" else "applied",
        "store_state": "index_applied_log_pending" if classification == "retry_reconciliation" else "fully_reconciled",
        "recovery_classification": classification,
        "writes_memory": False,
        "updates_index": False,
        "updates_log": False,
        "creates_journal": False,
        "mutates_soul": False,
        "invokes_slp": False,
        "runtime_wired": False,
        "lab_api_exposed": False,
        "visible_response_changed": False,
        "audit": {"runtime_private": True},
        "blocked_reasons": [reason] if reason else [],
        "projection": {},
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix=CANARY_STORE_PATH) as temporary:
        root = Path(temporary)
        prepare_store(root)
        request, _ = create_request(root)
        captured: dict[str, object] = {}

        from relaylm import relaymem_primary_pipeline as pipeline

        def m3b_capture(**kwargs):
            captured["m3a_candidates"] = kwargs["candidates"]
            return real_m3b(**kwargs)

        def m3c_capture(**kwargs):
            captured["m3b"] = kwargs["preflight_artifact"]
            captured["experience"] = kwargs["governed_experience_artifact"]
            return real_m3c(**kwargs)

        original_m3d = pipeline.build_relaymem_primary_writer_handoff_preflight
        original_m3e = pipeline.apply_relaymem_primary_page_write
        original_m3f = pipeline.build_relaymem_primary_index_log_reconciliation_preflight
        original_m3g = pipeline.apply_relaymem_primary_index_log_reconciliation
        original_m3h = pipeline.audit_relaymem_primary_index_log_reconciliation_recovery

        def m3d_capture(**kwargs):
            captured["m3c"] = kwargs["page_candidate_artifact"]
            return original_m3d(**kwargs)

        def m3e_capture(**kwargs):
            captured["m3d"] = kwargs["writer_handoff_artifact"]
            return original_m3e(**kwargs)

        def m3f_capture(**kwargs):
            captured["m3e_receipt"] = kwargs["receipt"]
            return original_m3f(**kwargs)

        def m3g_capture(**kwargs):
            captured["m3f_plan"] = kwargs["plan_artifact"]
            return original_m3g(**kwargs)

        def m3h_capture(**kwargs):
            captured["m3g_receipt"] = kwargs["receipt"]
            return original_m3h(**kwargs)

        out = io.StringIO()
        err = io.StringIO()
        with (
            redirect_stdout(out),
            redirect_stderr(err),
            patch.object(pipeline, "build_relaymem_primary_write_preflight_dry_run", side_effect=m3b_capture),
            patch.object(pipeline, "build_relaymem_primary_page_candidate_dry_run", side_effect=m3c_capture),
            patch.object(pipeline, "build_relaymem_primary_writer_handoff_preflight", side_effect=m3d_capture),
            patch.object(pipeline, "apply_relaymem_primary_page_write", side_effect=m3e_capture),
            patch.object(pipeline, "build_relaymem_primary_index_log_reconciliation_preflight", side_effect=m3f_capture),
            patch.object(pipeline, "apply_relaymem_primary_index_log_reconciliation", side_effect=m3g_capture),
            patch.object(pipeline, "audit_relaymem_primary_index_log_reconciliation_recovery", side_effect=m3h_capture),
        ):
            result = execute_relaymem_primary_pipeline(request)
        require(result.status == "recovery_not_required", result.to_log_dict())
        require(result.completed_stage_count == 8, result.to_log_dict())
        assert_stage_order(result)
        require(captured["m3a_candidates"] is result.m3a_result["candidates"], "M3a->M3b identity")
        require(captured["m3b"] is result.m3b_result, "M3b->M3c identity")
        require(captured["m3c"] is result.m3c_result, "M3c->M3d identity")
        require(captured["m3d"] is result.m3d_result, "M3d->M3e identity")
        require(captured["m3e_receipt"] is result.m3e_result["receipt"], "M3e->M3f identity")
        require(captured["m3f_plan"] is result.m3f_result["plan"], "M3f->M3g identity")
        require(captured["m3g_receipt"] is result.m3g_result["receipt"], "M3g->M3h identity")
        require(out.getvalue() == "" and err.getvalue() == "", (out.getvalue(), err.getvalue()))
        target = next((root / "memory/mem/primary/projects").glob("*.md"))
        actual_key = target.stem
        projection = project_relaymem_primary_pipeline(result)
        node = build_relaymem_primary_pipeline_node_result(result)
        assert_content_free(projection.to_log_dict(), root=root, actual_key=actual_key)
        assert_content_free(node.to_log_dict(), root=root, actual_key=actual_key)
        assert_content_free(result, root=root, actual_key=actual_key)
        assert_content_free(result.stage_results, root=root, actual_key=actual_key)
        require(projection.page_applied is True, projection)
        require(projection.index_applied is True and projection.log_applied is True, projection)

        repeated_request, _ = create_request(root)
        repeated = execute_relaymem_primary_pipeline(repeated_request)
        require(repeated.status == "recovery_not_required", repeated.to_log_dict())
        require(repeated.m3e_result["status"] == "already_applied", repeated.to_log_dict())
        require(repeated.m3g_result["status"] == "already_applied", repeated.to_log_dict())
        require(project_relaymem_primary_pipeline(repeated).page_exact_existing is True, repeated.to_log_dict())
        require(len(list((root / "memory/mem/primary/projects").glob("*.md"))) == 1, "duplicate page")
        index_text = (root / "memory/mem/index.md").read_text(encoding="utf-8")
        log_text = (root / "memory/mem/log.md").read_text(encoding="utf-8")
        require(index_text.count("relaymem-primary-index-entry-v0") == 1, index_text)
        require(log_text.count("relaymem-primary-log-entry-v0") == 1, log_text)
    print("ok exact M3a-M3h success, stage order, identity handoffs, and duplicate convergence")

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        prepare_store(root)
        request, record = create_request(root)
        generic = RelayMEMPrimaryPipelineRequest(
            schema_version=REQUEST_SCHEMA,
            runtime_private=True,
            content_included=True,
            worker_source=source_payload(record),
            claimed_record=record,
            request_scope=request.request_scope,
            store_root=str(root),
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
        with patch("relaylm.relaymem_primary_pipeline.build_relaymem_primary_formation_dry_run") as m3a:
            invalid = execute_relaymem_primary_pipeline(generic)
            require(invalid.status == "invalid_input" and not m3a.called, invalid.to_log_dict())

        wrong_request, _ = create_request(root)
        object.__setattr__(wrong_request.worker_source, "schema_version", "wrong.source.v0")
        with patch("relaylm.relaymem_primary_pipeline.build_relaymem_primary_formation_dry_run") as m3a:
            wrong = execute_relaymem_primary_pipeline(wrong_request)
            require(wrong.status == "invalid_input" and not m3a.called, wrong.to_log_dict())

        correlation_request, _ = create_request(root)
        mismatched = claimed_record(run_id="other-run")
        object.__setattr__(correlation_request, "claimed_record", mismatched)
        with patch("relaylm.relaymem_primary_pipeline.build_relaymem_primary_formation_dry_run") as m3a:
            correlation = execute_relaymem_primary_pipeline(correlation_request)
            require(correlation.status == "invalid_input" and not m3a.called, correlation.to_log_dict())

        disabled_request, _ = create_request(
            root, enabled=False, dry_run_only=True, apply_enabled=False
        )
        with patch("relaylm.relaymem_primary_pipeline.build_relaymem_primary_formation_dry_run") as m3a:
            disabled = execute_relaymem_primary_pipeline(disabled_request)
            require(disabled.status == "disabled" and not m3a.called, disabled.to_log_dict())
    print("ok generic source, wrong schema, correlation failure, and disabled mode stop before M3a")

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        prepare_store(root)
        blocked_request, _ = create_request(root, scene_type="formal_document")
        with patch("relaylm.relaymem_primary_pipeline.build_relaymem_primary_write_preflight_dry_run") as m3b:
            blocked = execute_relaymem_primary_pipeline(blocked_request)
            require(blocked.status == "blocked" and not m3b.called, blocked.to_log_dict())

        held_request, _ = create_request(root, scene_type="system_ops")
        with patch("relaylm.relaymem_primary_pipeline.build_relaymem_primary_write_preflight_dry_run") as m3b:
            held = execute_relaymem_primary_pipeline(held_request)
            require(held.status == "held" and not m3b.called, held.to_log_dict())

        m3b_request, _ = create_request(root)

        def blocked_m3b(**kwargs):
            value = real_m3b(**kwargs)
            value["operations"][0]["preflight_status"] = "blocked"
            value["operations"][0]["blocked_reasons"] = ["test_m3b_blocked"]
            return value

        with (
            patch("relaylm.relaymem_primary_pipeline.build_relaymem_primary_write_preflight_dry_run", side_effect=blocked_m3b),
            patch("relaylm.relaymem_primary_pipeline.build_relaymem_primary_page_candidate_dry_run") as m3c,
        ):
            m3b_failed = execute_relaymem_primary_pipeline(m3b_request)
            require(m3b_failed.status == "blocked" and not m3c.called, m3b_failed.to_log_dict())

        m3c_request, _ = create_request(root)

        def invalid_m3c(**kwargs):
            value = real_m3c(**kwargs)
            value["page_candidate_count"] = 0
            value["page_candidates"] = []
            value["blocked_reasons"] = ["governed_experience_invalid"]
            return value

        with (
            patch("relaylm.relaymem_primary_pipeline.build_relaymem_primary_page_candidate_dry_run", side_effect=invalid_m3c),
            patch("relaylm.relaymem_primary_pipeline.build_relaymem_primary_writer_handoff_preflight") as m3d,
        ):
            m3c_failed = execute_relaymem_primary_pipeline(m3c_request)
            require(m3c_failed.status == "blocked" and not m3d.called, m3c_failed.to_log_dict())
    print("ok M3a blocked/held, M3b failure, and M3c invalid stop downstream stages")

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        prepare_store(root)
        m3e_request, _ = create_request(root)
        with (
            patch("relaylm.relaymem_primary_pipeline.apply_relaymem_primary_page_write", return_value=fake_m3e_blocked("primary_page_writer_target_conflict")),
            patch("relaylm.relaymem_primary_pipeline.build_relaymem_primary_index_log_reconciliation_preflight") as m3f,
        ):
            m3e_failed = execute_relaymem_primary_pipeline(m3e_request)
            require(m3e_failed.status == "blocked" and not m3f.called, m3e_failed.to_log_dict())

        uncertain_request, _ = create_request(root)
        uncertain = fake_m3e_blocked("primary_page_writer_directory_fsync_failed")
        uncertain.update(
            status="applied_durability_unconfirmed",
            writes_memory=True,
            page_applied=True,
            cleanup_complete=False,
            receipt={"schema_version": "private-uncertain-receipt"},
        )
        with (
            patch("relaylm.relaymem_primary_pipeline.apply_relaymem_primary_page_write", return_value=uncertain),
            patch("relaylm.relaymem_primary_pipeline.build_relaymem_primary_index_log_reconciliation_preflight") as m3f,
        ):
            uncertain_result = execute_relaymem_primary_pipeline(uncertain_request)
            require(uncertain_result.status == "blocked" and not m3f.called, uncertain_result.to_log_dict())

        lock_request, _ = create_request(root)
        lock_result = fake_m3g(status="blocked", reason="primary_reconciliation_apply_lock_unavailable")
        with (
            patch("relaylm.relaymem_primary_pipeline.apply_relaymem_primary_index_log_reconciliation", return_value=lock_result),
            patch("relaylm.relaymem_primary_pipeline.audit_relaymem_primary_index_log_reconciliation_recovery") as m3h,
        ):
            locked = execute_relaymem_primary_pipeline(lock_request)
            require(locked.status == "blocked" and not m3h.called, locked.to_log_dict())
            require(project_relaymem_primary_pipeline(locked).retryable is True, locked.to_log_dict())
    print("ok M3e failure, durability uncertainty, and M3g lock fail closed without retry loops")

    for classification, expected_status in (
        ("retry_reconciliation", "retry_reconciliation"),
        ("manual_confirmation_required", "manual_confirmation_required"),
        ("journaled_recovery_candidate", "journaled_recovery_candidate"),
    ):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prepare_store(root)
            request, _ = create_request(root)
            with (
                patch("relaylm.relaymem_primary_pipeline.apply_relaymem_primary_index_log_reconciliation", return_value=fake_m3g(status="index_applied_log_pending")),
                patch("relaylm.relaymem_primary_pipeline.audit_relaymem_primary_index_log_recovery_audit", return_value=fake_m3h(classification)),
            ):
                classified = execute_relaymem_primary_pipeline(request)
            require(classified.status == expected_status, classified.to_log_dict())
            require(
                project_relaymem_primary_pipeline(classified).recovery_classification
                == classification,
                classified.to_log_dict(),
            )
    print("ok partial progress, manual confirmation, and journaled recovery classifications preserved")

    with tempfile.TemporaryDirectory(prefix=CANARY_STORE_PATH) as temporary:
        root = Path(temporary)
        prepare_store(root)
        before = {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*")
            if path.is_file()
        }
        request, _ = create_request(root, dry_run_only=True, apply_enabled=False)
        with (
            patch("relaylm.relaymem_primary_pipeline.apply_relaymem_primary_page_write") as m3e,
            patch("relaylm.relaymem_primary_pipeline.apply_relaymem_primary_index_log_reconciliation") as m3g,
        ):
            dry = execute_relaymem_primary_pipeline(request)
        after = {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*")
            if path.is_file()
        }
        require(dry.status == "dry_run_ready", dry.to_log_dict())
        require(not m3e.called and not m3g.called, (m3e.call_count, m3g.call_count))
        require(before == after, (before, after))
        projection = project_relaymem_primary_pipeline(dry).to_log_dict()
        require(projection["queue_io_performed"] is False, projection)
        require(projection["queue_transition_performed"] is False, projection)
        require(projection["mutates_soul"] is False, projection)
        require(projection["secondary_mem_processed"] is False, projection)
        assert_content_free(projection, root=root)
    print("ok dry-run has no M3e/M3g mutation, queue control, SOUL mutation, or Secondary MEM")

    print("RelayMEM Primary pipeline compose smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
