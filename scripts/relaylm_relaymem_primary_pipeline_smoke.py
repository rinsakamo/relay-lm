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

from relaylm import relaymem_primary_pipeline as pipeline
from relaylm.relaymem_primary_page_candidate import (
    build_relaymem_governed_experience_summary,
    build_relaymem_primary_page_candidate_dry_run as real_m3c,
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


def claimed_record(
    *, run_id: str = "run-c1-compose", namespace: str = CANARY_NAMESPACE
) -> dict[str, object]:
    now = datetime(2026, 6, 23, tzinfo=timezone.utc)
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


def source_payload(
    record: dict[str, object], *, scene_type: str = "design_talk"
) -> dict[str, object]:
    blocked = scene_type in {"formal_document", "medical_or_safety", "recovery"}
    reasons = [f"scene_policy_blocks_persistence:{scene_type}"] if blocked else []
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
                "persistence_block_reasons": reasons,
            },
            "persistence_block": blocked,
            "persistence_block_reasons": reasons,
        },
        "relayemo_artifact": {
            "assistant_emotion_state": {"intensity": 0.67},
            "user_affect_estimate": {"confidence": 0.71, "mode": "engaged"},
        },
        "governed_messages": [
            {"role": "system", "content": "governed system context"},
            {"role": "user", "content": CANARY_SOURCE},
            {"role": "assistant", "content": "bounded project evidence"},
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
    source_enabled = enabled or (dry_run_only and not apply_enabled)
    built = build_relaymem_slp_primary_worker_source(
        source_payload(canonical, scene_type=scene_type),
        claimed_record=canonical,
        request_scope=scope,
        enabled=source_enabled,
        dry_run_only=dry_run_only,
        apply_enabled=apply_enabled,
    )
    require(built.source is not None, built.to_log_dict())
    request = RelayMEMPrimaryPipelineRequest(
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
    )
    return request, canonical


def prepare_store(root: Path) -> None:
    for relative in (
        "memory/sources/conversations",
        "memory/sources/communications",
        "memory/sources/corrections",
        "memory/mem/primary/projects",
        "memory/mem/primary/relationships",
        "memory/mem/primary/sessions",
        "memory/mem/primary/scenes",
        "memory/mem/secondary/projects",
        "memory/mem/secondary/concepts",
        "memory/mem/secondary/claims",
        "memory/mem/secondary/summaries",
        "memory/mem/secondary/relations",
    ):
        (root / relative).mkdir(parents=True, exist_ok=True)
    (root / "memory/mem/index.md").write_text("# Index\n", encoding="utf-8")
    (root / "memory/mem/log.md").write_text("# Log\n", encoding="utf-8")


def _assert_safe(value: object, root: Path, key: str = "") -> None:
    text = repr(value)
    forbidden = (
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
        str(root),
        key,
    )
    require(all(not token or token not in text for token in forbidden), "protected leak")


def _m3e_blocked(reason: str) -> dict[str, object]:
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


def _m3g(status: str, reason: str | None = None) -> dict[str, object]:
    complete = status in {"applied", "already_applied"}
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
        "log_reconciled": complete,
        "index_updated": status == "applied",
        "log_updated": status == "applied",
        "index_idempotent_noop": status == "already_applied",
        "log_idempotent_noop": status == "already_applied",
        "durability_confirmed": complete,
        "cleanup_complete": True,
        "updates_index": status == "applied",
        "updates_log": status == "applied",
        "mutates_soul": False,
        "invokes_slp": False,
        "runtime_wired": False,
        "lab_api_exposed": False,
        "visible_response_changed": False,
        "receipt": None if status == "blocked" else {"schema_version": "private"},
        "blocked_reasons": [reason] if reason else [],
        "projection": {},
    }


def _m3h(classification: str) -> dict[str, object]:
    partial = classification == "retry_reconciliation"
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
        "source_status": "index_applied_log_pending" if partial else "applied",
        "store_state": "index_applied_log_pending" if partial else "fully_reconciled",
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
        "blocked_reasons": [],
        "projection": {},
    }


def _normal_and_duplicate() -> None:
    with tempfile.TemporaryDirectory(prefix=CANARY_STORE_PATH) as temporary:
        root = Path(temporary)
        prepare_store(root)
        request, _ = create_request(root)
        seen: dict[str, object] = {}
        originals = {
            "m3d": pipeline.build_relaymem_primary_writer_handoff_preflight,
            "m3e": pipeline.apply_relaymem_primary_page_write,
            "m3f": pipeline.build_relaymem_primary_index_log_reconciliation_preflight,
            "m3g": pipeline.apply_relaymem_primary_index_log_reconciliation,
            "m3h": pipeline.audit_relaymem_primary_index_log_reconciliation_recovery,
        }

        def m3b(**kwargs):
            seen["m3a"] = kwargs["candidates"]
            return real_m3b(**kwargs)

        def m3c(**kwargs):
            seen["m3b"] = kwargs["preflight_artifact"]
            return real_m3c(**kwargs)

        def wrap(name: str, key: str):
            def call(**kwargs):
                seen[name] = kwargs[key]
                return originals[name](**kwargs)
            return call

        out, err = io.StringIO(), io.StringIO()
        with (
            redirect_stdout(out),
            redirect_stderr(err),
            patch.object(pipeline, "build_relaymem_primary_write_preflight_dry_run", side_effect=m3b),
            patch.object(pipeline, "build_relaymem_primary_page_candidate_dry_run", side_effect=m3c),
            patch.object(pipeline, "build_relaymem_primary_writer_handoff_preflight", side_effect=wrap("m3d", "page_candidate_artifact")),
            patch.object(pipeline, "apply_relaymem_primary_page_write", side_effect=wrap("m3e", "writer_handoff_artifact")),
            patch.object(pipeline, "build_relaymem_primary_index_log_reconciliation_preflight", side_effect=wrap("m3f", "receipt")),
            patch.object(pipeline, "apply_relaymem_primary_index_log_reconciliation", side_effect=wrap("m3g", "plan_artifact")),
            patch.object(pipeline, "audit_relaymem_primary_index_log_reconciliation_recovery", side_effect=wrap("m3h", "receipt")),
        ):
            result = execute_relaymem_primary_pipeline(request)
        require(result.status == "recovery_not_required", result.to_log_dict())
        require(tuple(item.stage for item in result.stage_results) == STAGES, "stage order")
        require(result.completed_stage_count == 8, result.to_log_dict())
        require(seen["m3a"] is result.m3a_result["candidates"], "m3a identity")
        require(seen["m3b"] is result.m3b_result, "m3b identity")
        require(seen["m3d"] is result.m3c_result, "m3c identity")
        require(seen["m3e"] is result.m3d_result, "m3d identity")
        require(seen["m3f"] is result.m3e_result["receipt"], "m3e identity")
        require(seen["m3g"] is result.m3f_result["plan"], "m3f identity")
        require(seen["m3h"] is result.m3g_result["receipt"], "m3g identity")
        require(out.getvalue() == "" and err.getvalue() == "", "unexpected output")
        target = next((root / "memory/mem/primary/projects").glob("*.md"))
        projection = project_relaymem_primary_pipeline(result)
        _assert_safe(result, root, target.stem)
        _assert_safe(projection.to_log_dict(), root, target.stem)
        _assert_safe(build_relaymem_primary_pipeline_node_result(result).to_log_dict(), root, target.stem)

        repeated, _ = create_request(root)
        duplicate = execute_relaymem_primary_pipeline(repeated)
        require(duplicate.status == "recovery_not_required", duplicate.to_log_dict())
        require(duplicate.m3e_result["status"] == "already_applied", duplicate.to_log_dict())
        require(duplicate.m3g_result["status"] == "already_applied", duplicate.to_log_dict())
        require(len(list((root / "memory/mem/primary/projects").glob("*.md"))) == 1, "duplicate page")
        require((root / "memory/mem/index.md").read_text().count("relaymem-primary-index-entry-v0") == 1, "duplicate index")
        require((root / "memory/mem/log.md").read_text().count("relaymem-primary-log-entry-v0") == 1, "duplicate log")


def _input_and_stop_cases() -> None:
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
        require(execute_relaymem_primary_pipeline(generic).status == "invalid_input", "dict source")

        wrong, _ = create_request(root)
        object.__setattr__(wrong.worker_source, "schema_version", "wrong.source.v0")
        require(execute_relaymem_primary_pipeline(wrong).status == "invalid_input", "wrong schema")

        correlation, _ = create_request(root)
        object.__setattr__(correlation, "claimed_record", claimed_record(run_id="other-run"))
        require(execute_relaymem_primary_pipeline(correlation).status == "invalid_input", "correlation")

        disabled, _ = create_request(root, enabled=False, dry_run_only=True, apply_enabled=False)
        with patch.object(pipeline, "build_relaymem_primary_formation_dry_run") as m3a:
            result = execute_relaymem_primary_pipeline(disabled)
        require(result.status == "disabled" and not m3a.called, result.to_log_dict())

        for scene, status in (("formal_document", "blocked"), ("system_ops", "held")):
            candidate, _ = create_request(root, scene_type=scene)
            with patch.object(pipeline, "build_relaymem_primary_write_preflight_dry_run") as m3b:
                result = execute_relaymem_primary_pipeline(candidate)
            require(result.status == status and not m3b.called, result.to_log_dict())

        m3b_request, _ = create_request(root)
        def blocked_m3b(**kwargs):
            value = real_m3b(**kwargs)
            value["operations"][0]["preflight_status"] = "blocked"
            value["operations"][0]["blocked_reasons"] = ["test_m3b_blocked"]
            return value
        with (
            patch.object(pipeline, "build_relaymem_primary_write_preflight_dry_run", side_effect=blocked_m3b),
            patch.object(pipeline, "build_relaymem_primary_page_candidate_dry_run") as m3c,
        ):
            result = execute_relaymem_primary_pipeline(m3b_request)
        require(result.status == "blocked" and not m3c.called, result.to_log_dict())

        m3c_request, _ = create_request(root)
        def invalid_m3c(**kwargs):
            value = real_m3c(**kwargs)
            value["page_candidate_count"] = 0
            value["page_candidates"] = []
            value["blocked_reasons"] = ["governed_experience_invalid"]
            return value
        with (
            patch.object(pipeline, "build_relaymem_primary_page_candidate_dry_run", side_effect=invalid_m3c),
            patch.object(pipeline, "build_relaymem_primary_writer_handoff_preflight") as m3d,
        ):
            result = execute_relaymem_primary_pipeline(m3c_request)
        require(result.status == "blocked" and not m3d.called, result.to_log_dict())


def _failure_and_recovery_cases() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        prepare_store(root)
        request, _ = create_request(root)
        with (
            patch.object(pipeline, "apply_relaymem_primary_page_write", return_value=_m3e_blocked("primary_page_writer_target_conflict")),
            patch.object(pipeline, "build_relaymem_primary_index_log_reconciliation_preflight") as m3f,
        ):
            result = execute_relaymem_primary_pipeline(request)
        require(result.status == "blocked" and not m3f.called, result.to_log_dict())

        uncertain_request, _ = create_request(root)
        uncertain = _m3e_blocked("primary_page_writer_directory_fsync_failed")
        uncertain.update(
            status="applied_durability_unconfirmed",
            writes_memory=True,
            page_applied=True,
            cleanup_complete=False,
            receipt={"schema_version": "private-uncertain-receipt"},
        )
        with patch.object(pipeline, "apply_relaymem_primary_page_write", return_value=uncertain):
            result = execute_relaymem_primary_pipeline(uncertain_request)
        require(result.status == "blocked", result.to_log_dict())

        lock_request, _ = create_request(root)
        with (
            patch.object(pipeline, "apply_relaymem_primary_index_log_reconciliation", return_value=_m3g("blocked", "primary_reconciliation_apply_lock_unavailable")),
            patch.object(pipeline, "audit_relaymem_primary_index_log_reconciliation_recovery") as m3h,
        ):
            result = execute_relaymem_primary_pipeline(lock_request)
        require(result.status == "blocked" and not m3h.called, result.to_log_dict())
        require(project_relaymem_primary_pipeline(result).retryable, result.to_log_dict())

    for classification in (
        "retry_reconciliation",
        "manual_confirmation_required",
        "journaled_recovery_candidate",
    ):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prepare_store(root)
            request, _ = create_request(root)
            with (
                patch.object(pipeline, "apply_relaymem_primary_index_log_reconciliation", return_value=_m3g("index_applied_log_pending")),
                patch.object(pipeline, "audit_relaymem_primary_index_log_reconciliation_recovery", return_value=_m3h(classification)),
            ):
                result = execute_relaymem_primary_pipeline(request)
            require(result.status == classification, result.to_log_dict())


def _dry_run() -> None:
    with tempfile.TemporaryDirectory(prefix=CANARY_STORE_PATH) as temporary:
        root = Path(temporary)
        prepare_store(root)
        before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
        request, _ = create_request(root, dry_run_only=True, apply_enabled=False)
        with (
            patch.object(pipeline, "apply_relaymem_primary_page_write") as m3e,
            patch.object(pipeline, "apply_relaymem_primary_index_log_reconciliation") as m3g,
        ):
            result = execute_relaymem_primary_pipeline(request)
        after = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
        require(result.status == "dry_run_ready", result.to_log_dict())
        require(not m3e.called and not m3g.called and before == after, "dry-run mutation")
        public = project_relaymem_primary_pipeline(result).to_log_dict()
        require(public["queue_io_performed"] is False, public)
        require(public["queue_transition_performed"] is False, public)
        require(public["mutates_soul"] is False, public)
        require(public["secondary_mem_processed"] is False, public)
        _assert_safe(public, root)


def main() -> int:
    _normal_and_duplicate()
    _input_and_stop_cases()
    _failure_and_recovery_cases()
    _dry_run()
    print("RelayMEM Primary pipeline compose smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
