from __future__ import annotations

import json
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

import yaml
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = Path(__file__).resolve().parent
for path in (REPO_ROOT, SCRIPTS_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from relaylm.app import create_app
from relaylm.relayint import build_relayint_quick_clarification_apply_plan
from relaylm_relayrun_runtime_checkpoint_dry_run_smoke import (  # type: ignore[import-not-found]
    _BackendHandler,
    _Capture,
    _build_store,
)

RAW_VALUES = (
    "それで",
    "some topic",
    "hidden raw referable",
    "hidden_schema_name",
    "hidden_tool_name",
    "hidden_function_name",
    "hidden memory content",
    "hidden stop sequence",
    "hidden_voice",
    "https://example.invalid/relayint-apply.png",
)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _write_config(
    path: Path,
    *,
    port: int,
    trace_path: Path,
    store_root: Path,
    apply_enabled: bool,
    apply_dry_run_only: bool,
    memory_store_enabled: bool = False,
    memory_retrieval_dry_run_only: bool = True,
    relayrun_checkpoint_write_enabled: bool = False,
    relayrun_checkpoint_dry_run_only: bool = True,
) -> None:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    cfg["backends"]["local_backend"]["base_url"] = f"http://127.0.0.1:{port}/v1"
    cfg["trace"] = {"enabled": True, "path": str(trace_path)}
    cfg["relayint_fast_path_dry_run_enabled"] = True
    cfg["relayint_quick_clarification_preflight_enabled"] = True
    cfg["relayint_quick_clarification_dry_run_only"] = True
    cfg["relayint_quick_clarification_apply_enabled"] = apply_enabled
    cfg["relayint_quick_clarification_apply_dry_run_only"] = apply_dry_run_only
    cfg["relayint_quick_clarification_response_max_chars"] = 120
    cfg["model_routes"]["relaylm-default"]["mode"] = "pass_through"
    cfg["relayrun_checkpoint_root"] = (
        store_root / "relayrun-checkpoints"
    ).relative_to(REPO_ROOT).as_posix()
    cfg["relayrun_checkpoint_write_enabled"] = relayrun_checkpoint_write_enabled
    cfg["relayrun_checkpoint_dry_run_only"] = relayrun_checkpoint_dry_run_only
    cfg["memory"].update(
        {
            "root_path": str(store_root),
            "store_enabled": memory_store_enabled,
            "retrieval_dry_run_only": memory_retrieval_dry_run_only,
            "ctx_block_apply_enabled": False,
            "snippet_extraction_enabled": False,
            "snippet_dry_run_only": True,
            "snippet_apply_enabled": False,
            "snippet_runtime_injection_enabled": False,
            "snippet_runtime_dry_run_only": True,
            "token_budget_truncation_enabled": False,
        }
    )
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")


def _payload(
    content: Any,
    *,
    ctx: dict[str, Any] | None = None,
    scene_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "scene_state": scene_state
        or {
            "scene_type": "design_talk",
            "confidence": 0.95,
            "stability": 0.9,
        }
    }
    if ctx is not None:
        metadata["ctx"] = ctx
    return {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": content}],
        "metadata": metadata,
        "stream": False,
    }


def _ambiguous_payload() -> dict[str, Any]:
    return _payload(
        [
            {"type": "text", "text": "それで"},
            {
                "type": "image_url",
                "image_url": {"url": "https://example.invalid/relayint-apply.png"},
            },
        ],
        ctx={"ctx_handoff_guess": {"summary": "hidden raw referable"}},
    )


def _post(
    *,
    port: int,
    store_root: Path,
    payload: dict[str, Any],
    capture: _Capture,
    apply_enabled: bool,
    apply_dry_run_only: bool,
    memory_store_enabled: bool = False,
    memory_retrieval_dry_run_only: bool = True,
    relayrun_checkpoint_write_enabled: bool = False,
    relayrun_checkpoint_dry_run_only: bool = True,
) -> tuple[dict[str, Any], dict[str, Any], Any]:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as td:
        trace_path = Path(td) / "trace.jsonl"
        cfg_path = Path(td) / "cfg.yaml"
        _write_config(
            cfg_path,
            port=port,
            trace_path=trace_path,
            store_root=store_root,
            apply_enabled=apply_enabled,
            apply_dry_run_only=apply_dry_run_only,
            memory_store_enabled=memory_store_enabled,
            memory_retrieval_dry_run_only=memory_retrieval_dry_run_only,
            relayrun_checkpoint_write_enabled=relayrun_checkpoint_write_enabled,
            relayrun_checkpoint_dry_run_only=relayrun_checkpoint_dry_run_only,
        )
        app = create_app(str(cfg_path))
        original = json.loads(json.dumps(payload, ensure_ascii=False))
        before_count = capture.count()
        with TestClient(app) as client:
            resp = client.post("/v1/chat/completions", json=payload)
            require(resp.status_code == 200, resp.text)
            response_body = resp.json()
        require(payload == original, payload)
        require(capture.count() == before_count + 1, capture.count())
        backend_payload = capture.get(before_count)
        require(backend_payload.get("messages") == original.get("messages"), backend_payload)
        require(backend_payload.get("metadata") == original.get("metadata"), backend_payload)
        for passthrough_key in (
            "stream",
            "response_format",
            "tools",
            "tool_choice",
            "functions",
            "function_call",
            "n",
            "max_completion_tokens",
            "max_tokens",
            "logprobs",
            "top_logprobs",
            "stop",
            "modalities",
            "audio",
        ):
            if passthrough_key in original:
                require(
                    backend_payload.get(passthrough_key) == original.get(passthrough_key),
                    backend_payload,
                )
        record = json.loads(trace_path.read_text(encoding="utf-8").strip().splitlines()[-1])
        metadata = record.get("metadata", {})
        require(isinstance(metadata, dict), record)
        relayrun = metadata.get("relayrun_artifact")
        require(isinstance(relayrun, dict), metadata)
        for phase6_key in (
            "response_source",
            "short_circuit_applied",
            "backend_forwarded",
            "relaymem_retrieval_skipped_reason",
        ):
            require(phase6_key not in relayrun, relayrun)
        _assert_backend_response(response_body)
        return backend_payload, metadata, response_body


def _response_text(response_body: Any) -> str:
    require(isinstance(response_body, dict), response_body)
    choices = response_body.get("choices")
    require(isinstance(choices, list) and choices, response_body)
    message = choices[0].get("message")
    require(isinstance(message, dict), response_body)
    content = message.get("content")
    require(isinstance(content, str), response_body)
    return content


def _assert_backend_response(response_body: Any) -> None:
    require(_response_text(response_body) == "ok", response_body)


def _assert_no_raw_content(value: Any) -> None:
    text = json.dumps(value, ensure_ascii=False)
    for raw in RAW_VALUES:
        require(raw not in text, value)


def _apply_plan(metadata: dict[str, Any]) -> dict[str, Any]:
    plan = metadata.get("relayint_quick_clarification_apply_plan")
    if isinstance(plan, dict):
        require(plan.get("schema_version") == "relayint_quick_clarification_apply_plan.v0", plan)
        require(plan.get("content_free") is True, plan)
        require(plan.get("short_circuit_applied") is False, plan)
        require(plan.get("response_short_circuit_allowed") is False, plan)
        require(plan.get("backend_payload_mutation_applied") is False, plan)
        require(plan.get("response_mutation_allowed") is False, plan)
        require(plan.get("user_visible_apply_allowed") is False, plan)
        safety = plan.get("safety_gates")
        require(isinstance(safety, dict), plan)
        require(safety.get("backend_payload_mutation_allowed") is False, plan)
        require(safety.get("response_mutation_allowed") is False, plan)
        require(safety.get("user_visible_apply_allowed") is False, plan)
        _assert_no_raw_content(plan)
        return plan

    node_results = metadata.get("pipeline_node_results")
    require(isinstance(node_results, list), metadata)
    relayint_nodes = [
        node
        for node in node_results
        if isinstance(node, dict)
        and node.get("node_name") == "relayint_quick_clarification"
    ]
    require(bool(relayint_nodes), metadata)
    node = relayint_nodes[-1]
    diagnostics = node.get("diagnostics")
    require(isinstance(diagnostics, dict), node)
    artifacts = node.get("artifacts")
    require(isinstance(artifacts, list), node)
    plan_artifacts = [
        artifact
        for artifact in artifacts
        if isinstance(artifact, dict)
        and artifact.get("artifact_name") == "relayint_quick_clarification_apply_plan"
    ]
    require(bool(plan_artifacts), node)
    artifact = plan_artifacts[-1]
    require(artifact.get("schema_version") == "relayint_quick_clarification_apply_plan.v0", artifact)
    require(artifact.get("content_free") is True, artifact)

    reasons = node.get("blocked_reasons")
    require(isinstance(reasons, list), node)
    projected_plan = {
        "schema_version": artifact.get("schema_version"),
        "content_free": artifact.get("content_free"),
        "apply_allowed": diagnostics.get("apply_allowed"),
        "apply_plan_present": diagnostics.get("apply_plan_present"),
        "apply_block_reasons": reasons,
        "short_circuit_applied": False,
        "response_short_circuit_allowed": False,
        "backend_payload_mutation_applied": False,
        "response_mutation_allowed": False,
        "user_visible_apply_allowed": False,
        "safety_gates": {
            "backend_payload_mutation_allowed": False,
            "response_mutation_allowed": False,
            "user_visible_apply_allowed": False,
        },
    }
    require(projected_plan["apply_plan_present"] is True, projected_plan)
    require(projected_plan["apply_allowed"] is False, projected_plan)
    _assert_no_raw_content(projected_plan)
    return projected_plan


def _assert_default_off(root: Path, capture: _Capture, port: int) -> None:
    payload = _ambiguous_payload()
    _backend_payload, metadata, response_body = _post(
        port=port,
        store_root=root,
        payload=payload,
        capture=capture,
        apply_enabled=False,
        apply_dry_run_only=True,
    )
    require("relayint_quick_clarification_apply_plan" not in metadata, metadata)
    _assert_backend_response(response_body)
    print("ok default-off emits no RelayINT quick clarification apply plan")


def _assert_dry_run_plan_only(root: Path, capture: _Capture, port: int) -> None:
    payload = _ambiguous_payload()
    _backend_payload, metadata, response_body = _post(
        port=port,
        store_root=root,
        payload=payload,
        capture=capture,
        apply_enabled=True,
        apply_dry_run_only=True,
    )
    plan = _apply_plan(metadata)
    reasons = plan.get("apply_block_reasons", [])
    if "dry_run_only" in plan:
        require(plan.get("dry_run_only") is True, plan)
    require(plan.get("apply_allowed") is False, plan)
    require("dry_run_only" in reasons, plan)
    require("phase4_plan_only" in reasons, plan)
    _assert_backend_response(response_body)
    print("ok dry-run-only emits diagnostics-only apply plan and forwards backend")


def _assert_plan_only_even_when_apply_flag_enabled(root: Path, capture: _Capture, port: int) -> None:
    payload = _ambiguous_payload()
    _backend_payload, metadata, response_body = _post(
        port=port,
        store_root=root,
        payload=payload,
        capture=capture,
        apply_enabled=True,
        apply_dry_run_only=False,
    )
    plan = _apply_plan(metadata)
    reasons = plan.get("apply_block_reasons", [])
    if "dry_run_only" in plan:
        require(plan.get("dry_run_only") is False, plan)
    require(plan.get("apply_allowed") is False, plan)
    require("phase4_plan_only" in reasons, plan)
    _assert_backend_response(response_body)
    print("ok apply flag remains Phase 4 plan-only without response mutation")


def _assert_plan_only_with_memory_and_relayrun_projection(
    root: Path, capture: _Capture, port: int
) -> None:
    payload = _ambiguous_payload()
    backend_payload, metadata, response_body = _post(
        port=port,
        store_root=root,
        payload=payload,
        capture=capture,
        apply_enabled=True,
        apply_dry_run_only=False,
        memory_store_enabled=True,
        memory_retrieval_dry_run_only=False,
        relayrun_checkpoint_write_enabled=True,
        relayrun_checkpoint_dry_run_only=True,
    )
    plan = _apply_plan(metadata)
    reasons = plan.get("apply_block_reasons", [])
    require(plan.get("apply_allowed") is False, plan)
    require("phase4_plan_only" in reasons, plan)
    require(backend_payload.get("messages") == payload["messages"], backend_payload)
    relayrun = metadata.get("relayrun_artifact")
    require(isinstance(relayrun, dict), metadata)
    require(relayrun.get("schema_version") == "relayrun.runtime_checkpoint.v0", relayrun)
    require(relayrun.get("content_free") is True, relayrun)
    require(relayrun.get("diagnostics_only") is True, relayrun)
    require(relayrun.get("run_status") == "diagnostics_only", relayrun)
    require(isinstance(relayrun.get("run_id"), str) and relayrun.get("run_id"), relayrun)
    _assert_backend_response(response_body)
    _assert_no_raw_content(plan)
    print("ok quick clarification remains backend-forwarded with memory and RelayRUN projection")


def _assert_gate_blocks(
    root: Path,
    capture: _Capture,
    port: int,
    *,
    mutator: Any,
    expected_reason: str,
    label: str,
) -> None:
    payload = _ambiguous_payload()
    mutator(payload)
    _backend_payload, metadata, response_body = _post(
        port=port,
        store_root=root,
        payload=payload,
        capture=capture,
        apply_enabled=True,
        apply_dry_run_only=True,
    )
    plan = _apply_plan(metadata)
    reasons = plan.get("apply_block_reasons", [])
    require(expected_reason in reasons, plan)
    _assert_no_raw_content(plan)
    _assert_backend_response(response_body)
    print(f"ok {label} compatibility gate blocks plan-only apply")


def _assert_streaming_unsupported_plan() -> None:
    preflight = {
        "schema_version": "relayint_quick_clarification_preflight.v0",
        "preflight_applicable": True,
        "clarification_type": "open_clarification",
        "scene_gate": {"quick_clarification_allowed": True, "block_reasons": []},
    }
    plan = build_relayint_quick_clarification_apply_plan(
        relayint_quick_clarification_preflight=preflight,
        enabled=True,
        dry_run_only=True,
        stream_enabled=True,
    )
    require(isinstance(plan, dict), plan)
    require(plan.get("apply_allowed") is False, plan)
    require("streaming_not_supported" in plan.get("apply_block_reasons", []), plan)
    require(plan.get("response_short_circuit_allowed") is False, plan)
    require(plan.get("response_mutation_allowed") is False, plan)
    require(plan.get("user_visible_apply_allowed") is False, plan)
    _assert_no_raw_content(plan)
    print("ok streaming is blocked in diagnostics-only apply plan")


def main() -> int:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as td:
        root = Path(td)
        store_root = root / "store"
        _build_store(store_root)
        capture = _Capture()
        _BackendHandler.capture = capture
        server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = int(server.server_address[1])
            _assert_default_off(store_root, capture, port)
            _assert_dry_run_plan_only(store_root, capture, port)
            _assert_plan_only_even_when_apply_flag_enabled(store_root, capture, port)
            _assert_plan_only_with_memory_and_relayrun_projection(store_root, capture, port)
            _assert_gate_blocks(
                store_root,
                capture,
                port,
                mutator=lambda payload: payload.update(
                    {"response_format": {"type": "json_schema", "json_schema": {"name": "hidden_schema_name"}}}
                ),
                expected_reason="response_format_requested",
                label="structured response",
            )
            _assert_gate_blocks(
                store_root,
                capture,
                port,
                mutator=lambda payload: payload.update(
                    {"tools": [{"type": "function", "function": {"name": "hidden_tool_name"}}]}
                ),
                expected_reason="tools_requested",
                label="tools",
            )
            _assert_gate_blocks(
                store_root,
                capture,
                port,
                mutator=lambda payload: payload.update(
                    {"tool_choice": {"type": "function", "function": {"name": "hidden_tool_name"}}}
                ),
                expected_reason="tool_choice_requested",
                label="tool choice",
            )
            _assert_gate_blocks(
                store_root,
                capture,
                port,
                mutator=lambda payload: payload.update(
                    {"functions": [{"name": "hidden_function_name"}]}
                ),
                expected_reason="functions_requested",
                label="legacy functions",
            )
            _assert_gate_blocks(
                store_root,
                capture,
                port,
                mutator=lambda payload: payload.update(
                    {"function_call": {"name": "hidden_function_name"}}
                ),
                expected_reason="function_call_requested",
                label="legacy function call",
            )
            _assert_gate_blocks(
                store_root,
                capture,
                port,
                mutator=lambda payload: payload.update({"n": 2}),
                expected_reason="multiple_choices_requested",
                label="multiple choices",
            )
            _assert_gate_blocks(
                store_root,
                capture,
                port,
                mutator=lambda payload: payload.update({"max_completion_tokens": 1}),
                expected_reason="max_completion_tokens_too_small",
                label="small max completion tokens",
            )
            _assert_gate_blocks(
                store_root,
                capture,
                port,
                mutator=lambda payload: payload.update({"max_tokens": 1}),
                expected_reason="max_tokens_too_small",
                label="small max tokens",
            )
            _assert_gate_blocks(
                store_root,
                capture,
                port,
                mutator=lambda payload: payload.update({"logprobs": True}),
                expected_reason="logprobs_requested",
                label="logprobs",
            )
            _assert_gate_blocks(
                store_root,
                capture,
                port,
                mutator=lambda payload: payload.update({"top_logprobs": 2}),
                expected_reason="top_logprobs_requested",
                label="top logprobs",
            )
            _assert_gate_blocks(
                store_root,
                capture,
                port,
                mutator=lambda payload: payload.update({"stop": ["hidden stop sequence"]}),
                expected_reason="stop_sequence_requested",
                label="stop sequence",
            )
            _assert_gate_blocks(
                store_root,
                capture,
                port,
                mutator=lambda payload: payload.update(
                    {"modalities": ["text", "audio"], "audio": {"voice": "hidden_voice", "format": "mp3"}}
                ),
                expected_reason="audio_modality_requested",
                label="audio modality",
            )
            _assert_streaming_unsupported_plan()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
