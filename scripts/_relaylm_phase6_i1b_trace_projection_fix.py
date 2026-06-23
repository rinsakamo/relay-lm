from __future__ import annotations

from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    audit_path = Path("relaylm/audit_projection.py")
    audit = audit_path.read_text(encoding="utf-8")
    diagnostics_anchor = '''_RELAYCTX_UNPACK_DIAGNOSTICS = _mapping(
    {
'''
    if diagnostics_anchor not in audit:
        raise SystemExit("audit diagnostics anchor missing")
    insertion_anchor = '''PIPELINE_NODE_PROJECTORS: dict[str, NodeProjector] = {
'''
    diagnostics = '''_RELAYMEM_SLP_FINALIZED_TURN_SOURCE_DIAGNOSTICS = _mapping(
    {
        "schema_version": _enum("relaymem.slp_finalized_turn_source_projection.v0"),
        "diagnostics_only": _bool,
        "content_free": _bool,
        "content_included": _bool,
        "raw_text_included": _bool,
        "raw_messages_included": _bool,
        "governed_title_included": _bool,
        "governed_summary_included": _bool,
        "identifier_values_included": _bool,
        "namespace_value_included": _bool,
        "lineage_fingerprint_included": _bool,
        "status": _enum("disabled", "invalid_input", "blocked", "ready"),
        "enabled": _bool,
        "response_finalized": _bool,
        "source_ready": _bool,
        "source_count": _non_negative_int,
        "current_user_present": _bool,
        "assistant_response_present": _bool,
        "scene_policy_present": _bool,
        "relayemo_present": _bool,
        "worker_invoked": _bool,
        "queue_io_performed": _bool,
        "writes_memory": _bool,
        "mutates_soul": _bool,
        "changes_visible_response": _bool,
        "blocked_reason_ids": _REASON_LIST,
    }
)

_RELAYMEM_SLP_RUNTIME_ENQUEUE_DIAGNOSTICS = _mapping(
    {
        "schema_version": _enum("relaymem.slp_runtime_enqueue_projection.v0"),
        "diagnostics_only": _bool,
        "content_free": _bool,
        "content_included": _bool,
        "raw_text_included": _bool,
        "raw_messages_included": _bool,
        "governed_title_included": _bool,
        "governed_summary_included": _bool,
        "namespace_value_included": _bool,
        "identifier_values_included": _bool,
        "lineage_fingerprint_included": _bool,
        "idempotency_key_included": _bool,
        "queue_path_included": _bool,
        "timestamp_values_included": _bool,
        "exception_text_included": _bool,
        "status": _enum(
            "disabled", "invalid_input", "skipped", "held", "blocked",
            "dry_run_ready", "enqueued", "duplicate_existing",
            "enqueue_failed", "source_retention_failed",
        ),
        "enabled": _bool,
        "dry_run_only": _bool,
        "apply_enabled": _bool,
        "finalized_turn_source_ready": _bool,
        "admission_eligible": _bool,
        "handoff_ready": _bool,
        "dispatch_ready": _bool,
        "source_capture_built": _bool,
        "typed_source_built": _bool,
        "source_retained": _bool,
        "worker_ready": _bool,
        "enqueue_attempted": _bool,
        "enqueue_new": _bool,
        "duplicate_existing": _bool,
        "blocked": _bool,
        "failure_stage": _enum(
            "none", "gate", "source_capture", "admission", "handoff",
            "dispatch", "enqueue", "source_retention",
        ),
        "process_local_source_retention": _bool,
        "restart_complete_source_persistence": _bool,
        "worker_invoked": _bool,
        "b3_claim_performed": _bool,
        "invokes_slp": _bool,
        "writes_memory": _bool,
        "mutates_soul": _bool,
        "changes_visible_response": _bool,
        "blocked_reason_ids": _REASON_LIST,
    }
)

'''
    audit = replace_once(
        audit,
        insertion_anchor,
        diagnostics + insertion_anchor,
        "audit diagnostics registration",
    )
    projector_anchor = '''    "relayctx_unpack": NodeProjector(
        decisions=frozenset({
            "empty_response", "blocked_update_visible_text_applied",
            "blocked_update_dry_run", "visible_text_applied",
            "structured_update_dry_run", "plain_text_no_change",
            "backend_status_not_success", "response_shape_unsupported",
            "response_copy_shape_changed",
        }),
        diagnostics=_RELAYCTX_UNPACK_DIAGNOSTICS,
        artifact_names=frozenset({"relayctx_unpack_runtime_result"}),
    ),
'''
    projector_replacement = projector_anchor + '''    "relaymem_slp_finalized_turn_source": NodeProjector(
        decisions=frozenset({"disabled", "invalid_input", "blocked", "ready"}),
        diagnostics=_RELAYMEM_SLP_FINALIZED_TURN_SOURCE_DIAGNOSTICS,
        artifact_names=frozenset({"relaymem_slp_finalized_turn_source"}),
    ),
    "relaymem_slp_runtime_enqueue": NodeProjector(
        decisions=frozenset({
            "disabled", "invalid_input", "skipped", "held", "blocked",
            "dry_run_ready", "enqueued", "duplicate_existing",
            "enqueue_failed", "source_retention_failed",
        }),
        diagnostics=_RELAYMEM_SLP_RUNTIME_ENQUEUE_DIAGNOSTICS,
        artifact_names=frozenset({"relaymem_slp_protected_source_capture"}),
    ),
'''
    audit = replace_once(
        audit,
        projector_anchor,
        projector_replacement,
        "audit node projectors",
    )
    audit = replace_once(
        audit,
        '''    "event": _enum("backend_error", "backend_response", "backend_stream_response"),
''',
        '''    "event": _enum(
        "backend_error", "backend_response", "backend_stream_response",
        "relaymem_slp_runtime_enqueue",
    ),
''',
        "audit event enum",
    )
    audit_path.write_text(audit, encoding="utf-8")

    trace_path = Path("relaylm/trace_runtime.py")
    trace = trace_path.read_text(encoding="utf-8")
    trace = replace_once(
        trace,
        '''        if resolved_pipeline_node_results is not None and not explicit_pipeline_node_results:
            trace_metadata["pipeline_node_results"] = resolved_pipeline_node_results
''',
        '''        if resolved_pipeline_node_results is not None and (
            not explicit_pipeline_node_results
            or _is_relaymem_slp_runtime_enqueue_node_results(
                resolved_pipeline_node_results
            )
        ):
            trace_metadata["pipeline_node_results"] = resolved_pipeline_node_results
''',
        "explicit Phase 6 pipeline trace",
    )
    helper_anchor = '''def _is_stream_final_tts_node_results(
    node_results: list[dict[str, Any]] | None,
) -> bool:
'''
    helper = '''def _is_relaymem_slp_runtime_enqueue_node_results(
    node_results: list[dict[str, Any]] | None,
) -> bool:
    if not node_results or len(node_results) != 2:
        return False
    return [result.get("node_name") for result in node_results] == [
        "relaymem_slp_finalized_turn_source",
        "relaymem_slp_runtime_enqueue",
    ]


'''
    trace = replace_once(
        trace,
        helper_anchor,
        helper + helper_anchor,
        "Phase 6 trace result recognizer",
    )
    trace_path.write_text(trace, encoding="utf-8")


if __name__ == "__main__":
    main()
