from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.config import load_config
from relaylm.diagnostics import RequestDiagnostics
from relaylm.trace import read_trace_records
from relaylm.trace_runtime import extract_response_text, trace_runtime_event


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    body = {
        "choices": [
            {"message": {"role": "assistant", "content": "hello from backend"}}
        ]
    }
    response_text = extract_response_text(body)
    require(response_text == "hello from backend", response_text)
    print("ok extract response text")

    with tempfile.TemporaryDirectory() as tmpdir:
        trace_path = Path(tmpdir) / "trace.jsonl"
        config = load_config(REPO_ROOT / "config.example.yaml").model_copy(deep=True)
        config.trace.enabled = True
        config.trace.path = str(trace_path)
        selection_summary = {
            "selected_count": 3,
            "selected_memory_ids": [
                "default-relaylm-project",
                "default-like-tea",
                "shared-short-replies",
            ],
            "state_counts": {
                "active": 3,
                "promoted": 0,
                "demoted": 0,
                "disabled": 0,
            },
        }
        block_assembly = {
            "included_memory_ids": [
                "default-relaylm-project",
                "default-like-tea",
                "shared-short-replies",
            ],
            "dropped_memory_ids": [],
            "character_budget": 1200,
            "rendered_characters": 300,
        }
        diagnostics = RequestDiagnostics(
            request_id="trace-success-001",
            route_model="relaylm-default",
            character_id="default",
            mode_applied="memory_light",
            compiler_used=True,
            memory_block_used=True,
            memory_source="memory_candidate_selection",
            memory_selection_summary=selection_summary,
            memory_block_assembly=block_assembly,
            relayrun_artifact={
                "schema_version": "relayrun.runtime_checkpoint.v0",
                "diagnostics_only": True,
                "applied": False,
                "run_id": "run-trace-001",
                "run_status": "diagnostics_only",
                "node_statuses": [
                    {
                        "node_name": "request_received",
                        "node_status": "completed",
                    }
                ],
                "resume_allowed": False,
                "resume_mode": "none",
                "resume_preflight": {
                "schema_version": "relayrun.resume_preflight.v0",
                "diagnostics_only": True,
                "resume_allowed": False,
                "resume_attempted": False,
                "resume_applied": False,
                "checkpoint_read_attempted": False,
                "checkpoint_read_ok": False,
                "checkpoint_schema_valid": False,
                "content_free": None,
                "source_checkpoint_path": None,
                "blocked_reasons": [
                    "resume_not_implemented",
                    "resume_disabled",
                    "resume_dry_run_only",
                ],
                "future_resume_required_gates": [
                    "explicit_config_enabled",
                    "valid_checkpoint_schema",
                    "content_free_checkpoint",
                    "safe_resume_mode",
                    "user_or_policy_confirmation",
                ],
            },
            "checkpoint_persisted": False,
                "checkpoint_write_attempted": False,
                "checkpoint_writer_failed": False,
                "persisted_path": None,
                "persisted_bytes": None,
                "content_free": True,
                "checkpoint_persistence_plan": {
                    "schema_version": "relayrun.checkpoint_persistence_plan.v0",
                    "diagnostics_only": True,
                    "write_allowed": False,
                    "checkpoint_persisted": False,
                    "target_root": ".relayrun/checkpoints",
                    "target_path_preview": ".relayrun/checkpoints/run-trace-001/trace-success-001.json",
                    "run_id": "run-trace-001",
                    "turn_id": "trace-success-001",
                    "blocked_reasons": [
                        "checkpoint_persistence_not_implemented",
                        "checkpoint_write_disabled",
                    ],
                    "resume_allowed_after_persist": False,
                },
                "checkpoint_writer_preflight": {
                    "schema_version": "relayrun.checkpoint_writer_preflight.v0",
                    "diagnostics_only": True,
                    "write_allowed": False,
                    "preflight_passed": False,
                    "checkpoint_write_attempted": False,
                    "directory_creation_attempted": False,
                    "target_root": ".relayrun/checkpoints",
                    "target_path_preview": ".relayrun/checkpoints/run-trace-001/trace-success-001.json",
                    "path_safety": {
                        "root_relative": True,
                        "path_traversal_detected": False,
                        "absolute_path_detected": False,
                    },
                    "content_policy": {
                        "content_free": True,
                        "backend_payload_included": False,
                        "response_text_included": False,
                        "raw_user_message_included": False,
                    },
                    "blocked_reasons": [
                        "checkpoint_writer_not_implemented",
                        "checkpoint_write_disabled",
                    ],
                    "future_writer_required_gates": [
                        "explicit_config_enabled",
                        "safe_target_root",
                        "content_free_payload",
                        "atomic_write",
                        "idempotent_run_turn_key",
                    ],
                },
                "recovery_transition_created": False,
                "blocked_reasons": [],
            },
            trace_enabled=True,
        )
        written = trace_runtime_event(
            config=config,
            diagnostics=diagnostics,
            messages=[{"role": "user", "content": "hello"}],
            response_text=response_text,
            metadata={"event": "backend_response", "status_code": 200},
        )
        require(written is True, written)
        records = read_trace_records(trace_path)
        require(len(records) == 1, records)
        require(records[0].trace_id == "trace-success-001", records[0])
        require(records[0].response_text == "hello from backend", records[0])
        require(records[0].metadata["event"] == "backend_response", records[0].metadata)
        require(records[0].metadata["status_code"] == 200, records[0].metadata)
        require(records[0].metadata["memory_source"] == "memory_candidate_selection", records[0].metadata)
        require(records[0].metadata["memory_selection_summary"] == selection_summary, records[0].metadata)
        require(records[0].metadata["memory_block_assembly"] == block_assembly, records[0].metadata)
        require(isinstance(records[0].metadata["relayrun_artifact"], dict), records[0].metadata)
        require(records[0].metadata["relayrun_artifact"]["run_id"] == "run-trace-001", records[0].metadata)
        resume_preflight = records[0].metadata["relayrun_artifact"].get("resume_preflight")
        require(isinstance(resume_preflight, dict), records[0].metadata)
        require(resume_preflight.get("resume_allowed") is False, records[0].metadata)
        plan = records[0].metadata["relayrun_artifact"].get("checkpoint_persistence_plan")
        require(isinstance(plan, dict), records[0].metadata)
        require(plan.get("write_allowed") is False, records[0].metadata)
        preflight = records[0].metadata["relayrun_artifact"].get("checkpoint_writer_preflight")
        require(isinstance(preflight, dict), records[0].metadata)
        require(preflight.get("write_allowed") is False, records[0].metadata)
        require(preflight.get("checkpoint_write_attempted") is False, records[0].metadata)
        require(preflight.get("directory_creation_attempted") is False, records[0].metadata)
        require(records[0].metadata["relayrun_artifact"].get("content_free") is True, records[0].metadata)
        print("ok trace backend response event")
        print("ok trace response text captured")
        print("ok trace memory source captured")
        print("ok trace memory selection summary captured")
        print("ok trace memory block assembly captured")
        print("ok trace relayrun artifact captured")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
