from __future__ import annotations

from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    app_path = Path("relaylm/app.py")
    app = app_path.read_text(encoding="utf-8")
    if "run_relaymem_slp_runtime_enqueue_after_response" in app:
        print("runtime wiring already applied")
        return

    app = replace_once(
        app,
        "from fastapi.responses import JSONResponse, StreamingResponse\n",
        "from fastapi.responses import JSONResponse, StreamingResponse\n"
        "from starlette.background import BackgroundTask\n",
        "background import",
    )
    app = replace_once(
        app,
        "from relaylm.config import RelayLMConfig, load_config\n",
        "from relaylm.config import RelayLMConfig, load_config\n"
        "from relaylm.relaymem_slp_primary_worker_source_registry import (\n"
        "    RelayMEMSLPPrimaryWorkerSourceRegistry,\n"
        ")\n"
        "from relaylm.relaymem_slp_runtime_finalization import (\n"
        "    RelayMEMSLPFinalizedVisibleTextCapture,\n"
        "    run_relaymem_slp_runtime_enqueue_after_response,\n"
        "    wrap_stream_with_relaymem_slp_finalized_turn_capture,\n"
        ")\n",
        "phase6 imports",
    )
    app = replace_once(
        app,
        "    app.state.relaylm_config = config\n",
        "    app.state.relaylm_config = config\n"
        "    app.state.relaymem_slp_primary_worker_source_registry = (\n"
        "        RelayMEMSLPPrimaryWorkerSourceRegistry(\n"
        "            max_entries=config.relaymem_slp_source_registry_max_entries,\n"
        "            ttl_seconds=config.relaymem_slp_source_registry_ttl_seconds,\n"
        "        )\n"
        "    )\n",
        "registry state",
    )
    app = replace_once(
        app,
        '''            stream_diagnostics = replace(
                diagnostics,
                relayrun_artifact=stream_relayrun_artifact,
            )
            trace_runtime_event(
''',
        '''            stream_diagnostics = replace(
                diagnostics,
                relayrun_artifact=stream_relayrun_artifact,
            )
            stream_background = None
            if (
                config.relaymem_slp_runtime_enqueue_enabled
                and route.mode_applied != "pass_through"
            ):
                stream_capture = RelayMEMSLPFinalizedVisibleTextCapture()
                body_iter = wrap_stream_with_relaymem_slp_finalized_turn_capture(
                    body_iter,
                    capture=stream_capture,
                )
                stream_background = BackgroundTask(
                    run_relaymem_slp_runtime_enqueue_after_response,
                    config=config,
                    diagnostics=stream_diagnostics,
                    pipeline_context=pipeline_context,
                    registry=(
                        app.state.relaymem_slp_primary_worker_source_registry
                    ),
                    status_code=status_code,
                    resolved_session_id=merged_scope.get("session_id"),
                    relayscn_scene_policy_artifact=(
                        relayscn_scene_policy_artifact
                    ),
                    relayemo_artifact=relayemo_artifact,
                    stream_capture=stream_capture,
                    message_count=len(_extract_trace_messages(forwarded_payload)),
                )
            trace_runtime_event(
''',
        "stream background",
    )
    app = replace_once(
        app,
        '''                headers=stream_diagnostics.to_headers(),
            )

        try:
''',
        '''                headers=stream_diagnostics.to_headers(),
                background=stream_background,
            )

        try:
''',
        "stream response background",
    )
    app = replace_once(
        app,
        '''        if isinstance(body, dict) or isinstance(body, list):
            trace_runtime_event(
''',
        '''        if isinstance(body, dict) or isinstance(body, list):
            assistant_visible_text = extract_response_text(body)
            response_background = None
            if (
                config.relaymem_slp_runtime_enqueue_enabled
                and route.mode_applied != "pass_through"
                and isinstance(assistant_visible_text, str)
            ):
                response_background = BackgroundTask(
                    run_relaymem_slp_runtime_enqueue_after_response,
                    config=config,
                    diagnostics=success_diagnostics,
                    pipeline_context=pipeline_context,
                    registry=(
                        app.state.relaymem_slp_primary_worker_source_registry
                    ),
                    status_code=status_code,
                    resolved_session_id=merged_scope.get("session_id"),
                    relayscn_scene_policy_artifact=(
                        relayscn_scene_policy_artifact
                    ),
                    relayemo_artifact=relayemo_artifact,
                    assistant_visible_text=assistant_visible_text,
                    message_count=len(_extract_trace_messages(forwarded_payload)),
                )
            trace_runtime_event(
''',
        "nonstream background",
    )
    app = replace_once(
        app,
        "            return JSONResponse(status_code=status_code, content=body, headers=headers)\n",
        "            return JSONResponse(\n"
        "                status_code=status_code,\n"
        "                content=body,\n"
        "                headers=headers,\n"
        "                background=response_background,\n"
        "            )\n",
        "nonstream response background",
    )
    app_path.write_text(app, encoding="utf-8")

    source_path = Path("relaylm/relaymem_slp_finalized_turn_source.py")
    source = source_path.read_text(encoding="utf-8")
    source = replace_once(
        source,
        '''FINALIZED_TURN_SOURCE_PROJECTION_SCHEMA = (
    "relaymem.slp_finalized_turn_source_projection.v0"
)
''',
        '''FINALIZED_TURN_SOURCE_PROJECTION_SCHEMA = (
    "relaymem.slp_finalized_turn_source_projection.v0"
)
# One ordinary HTTP request owns one RelayRUN run and exactly one finalized turn.
# The first bounded runtime therefore uses a run-local zero-based turn authority.
RUN_LOCAL_TURN_INDEX = 0
''',
        "turn authority constant",
    )
    source = source.replace("context.turn_index", "RUN_LOCAL_TURN_INDEX")
    if "context.turn_index" in source:
        raise SystemExit("turn authority replacement incomplete")
    source_path.write_text(source, encoding="utf-8")

    example_path = Path("config.example.yaml")
    example = example_path.read_text(encoding="utf-8")
    example = replace_once(
        example,
        '''relayctx_tts_adapter_handoff_max_segment_chars: 120
relayctx_tts_adapter_handoff_min_segment_chars: 8

''',
        '''relayctx_tts_adapter_handoff_max_segment_chars: 120
relayctx_tts_adapter_handoff_min_segment_chars: 8

# Phase 6 I1-B ordinary managed-turn deferred enqueue is default-off. Dry-run
# captures exact request-local protected source evidence after visible response
# delivery but performs no B2 queue I/O and publishes nothing to the registry.
# Apply requires enabled=true, dry_run_only=false, apply_enabled=true, and an
# absolute existing queue root. The protected source registry is process-local
# and explicitly not restart-complete; no worker is started by this boundary.
relaymem_slp_runtime_enqueue_enabled: false
relaymem_slp_runtime_enqueue_dry_run_only: true
relaymem_slp_runtime_enqueue_apply_enabled: false
relaymem_slp_queue_root:
relaymem_slp_source_registry_max_entries: 256
relaymem_slp_source_registry_ttl_seconds: 1800

''',
        "config example",
    )
    example_path.write_text(example, encoding="utf-8")


if __name__ == "__main__":
    main()
