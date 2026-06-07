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

FIXED_REFERENCE_CLARIFICATION = "どの話のことか、もう少しだけ教えて。"
RAW_VALUES = (
    "それで",
    "some topic",
    "hidden raw referable",
    "hidden_schema_name",
    "hidden_tool_name",
    "hidden_function_name",
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
    cfg["memory"].update(
        {
            "root_path": str(store_root),
            "store_enabled": False,
            "retrieval_dry_run_only": True,
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
            {"type": "image_url", "image_url": {"url": "https://example.invalid/relayint-apply.png"}},
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
    expect_backend_called: bool,
) -> tuple[dict[str, Any] | None, dict[str, Any], Any]:
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
        )
        app = create_app(str(cfg_path))
        original = json.loads(json.dumps(payload, ensure_ascii=False))
        before_count = capture.count()
        with TestClient(app) as client:
            resp = client.post("/v1/chat/completions", json=payload)
            require(resp.status_code == 200, resp.text)
            response_body = resp.json()
        require(payload == original, payload)
        if expect_backend_called:
            require(capture.count() > before_count, capture.count())
            backend_payload: dict[str, Any] | None = capture.get(before_count)
        else:
            require(capture.count() == before_count, capture.count())
            backend_payload = None
        record = json.loads(trace_path.read_text(encoding="utf-8").strip().splitlines()[-1])
        metadata = record.get("metadata", {})
        require(isinstance(metadata, dict), record)
        return backend_payload, metadata, response_body


def _apply_plan(metadata: dict[str, Any]) -> dict[str, Any]:
    plan = metadata.get("relayint_quick_clarification_apply_plan")
    require(isinstance(plan, dict), metadata)
    require(plan.get("schema_version") == "relayint_quick_clarification_apply_plan.v0", plan)
    require(plan.get("enabled") is True, plan)
    require(plan.get("content_free") is True, plan)
    require(plan.get("content_free_template") is True, plan)
    safety = plan.get("safety_gates")
    require(isinstance(safety, dict), plan)
    require(safety.get("content_free") is True, plan)
    require(safety.get("llm_call_allowed") is False, plan)
    require(safety.get("mem_lookup_allowed") is False, plan)
    require(safety.get("backend_payload_mutation_allowed") is False, plan)
    require(plan.get("llm_called") is False, plan)
    require(plan.get("mem_lookup_executed") is False, plan)
    require(plan.get("backend_payload_mutation_allowed") is False, plan)
    require(plan.get("backend_payload_mutation_applied") is False, plan)
    compatibility_gate = plan.get("request_compatibility_gate")
    require(isinstance(compatibility_gate, dict), plan)
    _assert_no_raw_content(plan)
    return plan


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


def _assert_default_false(root: Path, capture: _Capture, port: int) -> None:
    payload = _ambiguous_payload()
    backend_payload, metadata, response_body = _post(
        port=port,
        store_root=root,
        payload=payload,
        capture=capture,
        apply_enabled=False,
        apply_dry_run_only=True,
        expect_backend_called=True,
    )
    require(backend_payload is not None and backend_payload.get("messages") == payload["messages"], backend_payload)
    require("relayint_quick_clarification_apply_plan" not in metadata, metadata)
    _assert_backend_response(response_body)
    print("ok default-off RelayINT quick clarification apply does not short-circuit")


def _assert_dry_run_only(root: Path, capture: _Capture, port: int) -> None:
    payload = _ambiguous_payload()
    backend_payload, metadata, response_body = _post(
        port=port,
        store_root=root,
        payload=payload,
        capture=capture,
        apply_enabled=True,
        apply_dry_run_only=True,
        expect_backend_called=True,
    )
    require(backend_payload is not None and backend_payload.get("messages") == payload["messages"], backend_payload)
    plan = _apply_plan(metadata)
    require(plan.get("dry_run_only") is True, plan)
    require(plan.get("apply_allowed") is False, plan)
    require("dry_run_only" in plan.get("apply_block_reasons", []), plan)
    require(plan.get("response_short_circuit_allowed") is False, plan)
    require(plan.get("short_circuit_applied") is False, plan)
    _assert_backend_response(response_body)
    print("ok dry-run-only RelayINT quick clarification apply is blocked")


def _assert_actual_apply(root: Path, capture: _Capture, port: int) -> None:
    payload = _ambiguous_payload()
    backend_payload, metadata, response_body = _post(
        port=port,
        store_root=root,
        payload=payload,
        capture=capture,
        apply_enabled=True,
        apply_dry_run_only=False,
        expect_backend_called=False,
    )
    require(backend_payload is None, backend_payload)
    plan = _apply_plan(metadata)
    require(plan.get("apply_allowed") is True, plan)
    require(plan.get("response_short_circuit_allowed") is True, plan)
    require(plan.get("short_circuit_applied") is True, plan)
    require(plan.get("response_template_id") == "generic_reference_clarification.ja.v0", plan)
    response_text = _response_text(response_body)
    require(response_text == FIXED_REFERENCE_CLARIFICATION, response_body)
    _assert_no_raw_content(response_body)
    print("ok RelayINT quick clarification apply short-circuits with fixed response")


def _assert_resolved_reference_falls_through(root: Path, capture: _Capture, port: int) -> None:
    payload = _payload("それで", ctx={"current_topic": "some topic"})
    backend_payload, metadata, response_body = _post(
        port=port,
        store_root=root,
        payload=payload,
        capture=capture,
        apply_enabled=True,
        apply_dry_run_only=False,
        expect_backend_called=True,
    )
    require(backend_payload is not None and backend_payload.get("messages") == payload["messages"], backend_payload)
    preflight = metadata.get("relayint_quick_clarification_preflight")
    require(isinstance(preflight, dict), metadata)
    require(preflight.get("preflight_applicable") is False, preflight)
    plan = _apply_plan(metadata)
    require(plan.get("apply_allowed") is False, plan)
    require("preflight_not_applicable" in plan.get("apply_block_reasons", []), plan)
    _assert_backend_response(response_body)
    print("ok resolved RelayINT reference falls through to backend")


def _assert_scene_gate_blocks(root: Path, capture: _Capture, port: int) -> None:
    payload = _payload(
        "それで",
        scene_state={
            "scene_type": "recovery",
            "confidence": 0.95,
            "stability": 0.9,
            "recovery_mode": True,
            "user_confirmation_required": True,
        },
    )
    backend_payload, metadata, response_body = _post(
        port=port,
        store_root=root,
        payload=payload,
        capture=capture,
        apply_enabled=True,
        apply_dry_run_only=False,
        expect_backend_called=True,
    )
    require(backend_payload is not None and backend_payload.get("messages") == payload["messages"], backend_payload)
    preflight = metadata.get("relayint_quick_clarification_preflight")
    require(isinstance(preflight, dict), metadata)
    require(preflight.get("preflight_applicable") is False, preflight)
    plan = _apply_plan(metadata)
    reasons = plan.get("apply_block_reasons", [])
    require(plan.get("apply_allowed") is False, plan)
    require("scene_gate_blocked" in reasons, plan)
    require("scene_type_is_recovery" in reasons, plan)
    require("user_confirmation_required" in reasons, plan)
    _assert_backend_response(response_body)
    print("ok RelayINT quick clarification apply respects scene gate blocks")



def _assert_response_format_blocks_apply(root: Path, capture: _Capture, port: int) -> None:
    payload = _ambiguous_payload()
    payload["response_format"] = {
        "type": "json_schema",
        "json_schema": {"name": "hidden_schema_name", "schema": {"type": "object"}},
    }
    backend_payload, metadata, response_body = _post(
        port=port,
        store_root=root,
        payload=payload,
        capture=capture,
        apply_enabled=True,
        apply_dry_run_only=False,
        expect_backend_called=True,
    )
    require(backend_payload is not None and backend_payload.get("messages") == payload["messages"], backend_payload)
    plan = _apply_plan(metadata)
    reasons = plan.get("apply_block_reasons", [])
    require(plan.get("apply_allowed") is False, plan)
    require(plan.get("response_short_circuit_allowed") is False, plan)
    require("response_format_requested" in reasons, plan)
    gate = plan.get("request_compatibility_gate")
    require(isinstance(gate, dict), plan)
    require(gate.get("compatible") is False, plan)
    require(gate.get("response_format_present") is True, plan)
    require(gate.get("tools_count") == 0, plan)
    _assert_backend_response(response_body)
    require(_response_text(response_body) != FIXED_REFERENCE_CLARIFICATION, response_body)
    print("ok response_format blocks RelayINT quick clarification apply")


def _assert_tools_block_apply(root: Path, capture: _Capture, port: int) -> None:
    payload = _ambiguous_payload()
    payload["tools"] = [
        {
            "type": "function",
            "function": {
                "name": "hidden_tool_name",
                "parameters": {"type": "object"},
            },
        }
    ]
    payload["tool_choice"] = "auto"
    backend_payload, metadata, response_body = _post(
        port=port,
        store_root=root,
        payload=payload,
        capture=capture,
        apply_enabled=True,
        apply_dry_run_only=False,
        expect_backend_called=True,
    )
    require(backend_payload is not None and backend_payload.get("messages") == payload["messages"], backend_payload)
    plan = _apply_plan(metadata)
    reasons = plan.get("apply_block_reasons", [])
    require(plan.get("apply_allowed") is False, plan)
    require("tools_requested" in reasons, plan)
    require("tool_choice_requested" in reasons, plan)
    gate = plan.get("request_compatibility_gate")
    require(isinstance(gate, dict), plan)
    require(gate.get("compatible") is False, plan)
    require(gate.get("tools_count") == 1, plan)
    require(gate.get("tool_choice_present") is True, plan)
    _assert_backend_response(response_body)
    require(_response_text(response_body) != FIXED_REFERENCE_CLARIFICATION, response_body)
    print("ok tools/tool_choice block RelayINT quick clarification apply")


def _assert_functions_block_apply(root: Path, capture: _Capture, port: int) -> None:
    payload = _ambiguous_payload()
    payload["functions"] = [
        {
            "name": "hidden_function_name",
            "parameters": {"type": "object"},
        }
    ]
    payload["function_call"] = {"name": "hidden_function_name"}
    backend_payload, metadata, response_body = _post(
        port=port,
        store_root=root,
        payload=payload,
        capture=capture,
        apply_enabled=True,
        apply_dry_run_only=False,
        expect_backend_called=True,
    )
    require(backend_payload is not None and backend_payload.get("messages") == payload["messages"], backend_payload)
    plan = _apply_plan(metadata)
    reasons = plan.get("apply_block_reasons", [])
    require(plan.get("apply_allowed") is False, plan)
    require("functions_requested" in reasons, plan)
    require("function_call_requested" in reasons, plan)
    gate = plan.get("request_compatibility_gate")
    require(isinstance(gate, dict), plan)
    require(gate.get("compatible") is False, plan)
    require(gate.get("functions_count") == 1, plan)
    require(gate.get("function_call_present") is True, plan)
    _assert_backend_response(response_body)
    require(_response_text(response_body) != FIXED_REFERENCE_CLARIFICATION, response_body)
    print("ok legacy functions/function_call block RelayINT quick clarification apply")

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
        dry_run_only=False,
        stream_enabled=True,
    )
    require(isinstance(plan, dict), plan)
    require(plan.get("apply_allowed") is False, plan)
    require("streaming_not_supported" in plan.get("apply_block_reasons", []), plan)
    require(plan.get("response_short_circuit_allowed") is False, plan)
    print("ok RelayINT quick clarification apply blocks streaming plans")


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
            _assert_default_false(store_root, capture, port)
            _assert_dry_run_only(store_root, capture, port)
            _assert_actual_apply(store_root, capture, port)
            _assert_resolved_reference_falls_through(store_root, capture, port)
            _assert_scene_gate_blocks(store_root, capture, port)
            _assert_response_format_blocks_apply(store_root, capture, port)
            _assert_tools_block_apply(store_root, capture, port)
            _assert_functions_block_apply(store_root, capture, port)
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
