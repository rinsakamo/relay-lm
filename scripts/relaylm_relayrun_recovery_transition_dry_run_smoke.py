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
from relaylm_relayrun_runtime_checkpoint_dry_run_smoke import (  # type: ignore[import-not-found]
    _BackendHandler,
    _Capture,
    _build_store,
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
    snippet_runtime_injection_enabled: bool = False,
    snippet_runtime_dry_run_only: bool = True,
) -> None:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    cfg["backends"]["local_backend"]["base_url"] = f"http://127.0.0.1:{port}/v1"
    cfg["trace"] = {"enabled": True, "path": str(trace_path)}
    cfg["model_routes"]["relaylm-default"]["mode"] = "pass_through"
    cfg["relayrun_recovery_transition_enabled"] = False
    cfg["relayrun_recovery_transition_dry_run_only"] = True
    cfg["relayrun_waiting_user_contract_enabled"] = True
    cfg["memory"].update(
        {
            "root_path": str(store_root),
            "store_enabled": True,
            "retrieval_dry_run_only": False,
            "ctx_block_apply_enabled": True,
            "snippet_extraction_enabled": True,
            "snippet_dry_run_only": False,
            "snippet_apply_enabled": True,
            "snippet_runtime_injection_enabled": snippet_runtime_injection_enabled,
            "snippet_runtime_dry_run_only": snippet_runtime_dry_run_only,
            "snippet_budget": 512,
            "max_snippet_chars": 160,
            "max_snippet_candidates": 3,
            "candidate_limit": 3,
            "token_budget_hint": 800,
            "token_budget_truncation_enabled": False,
        }
    )
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")


def _payload(content: str, scene_type: str) -> dict[str, Any]:
    return {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": content}],
        "metadata": {
            "scene_state": {
                "scene_type": scene_type,
                "confidence": 0.95,
                "stability": 0.9,
            }
        },
        "stream": False,
    }


def _post(
    *,
    port: int,
    store_root: Path,
    payload: dict[str, Any],
    capture: _Capture,
    expected_status: int = 200,
    snippet_runtime_injection_enabled: bool = False,
    snippet_runtime_dry_run_only: bool = True,
) -> tuple[dict[str, Any] | None, dict[str, Any], int]:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as td:
        trace_path = Path(td) / "trace.jsonl"
        cfg_path = Path(td) / "cfg.yaml"
        _write_config(
            cfg_path,
            port=port,
            trace_path=trace_path,
            store_root=store_root,
            snippet_runtime_injection_enabled=snippet_runtime_injection_enabled,
            snippet_runtime_dry_run_only=snippet_runtime_dry_run_only,
        )
        app = create_app(str(cfg_path))
        original = json.loads(json.dumps(payload))
        before_count = capture.count()
        with TestClient(app) as client:
            resp = client.post("/v1/chat/completions", json=payload)
            require(resp.status_code == expected_status, resp.text)
        require(payload == original, payload)
        backend_payload = None
        if capture.count() > before_count:
            backend_payload = capture.get(before_count)
        record = json.loads(trace_path.read_text(encoding="utf-8").strip().splitlines()[-1])
        metadata = record.get("metadata", {})
        require(isinstance(metadata, dict), record)
        return backend_payload, metadata, resp.status_code


def _transition(metadata: dict[str, Any]) -> dict[str, Any]:
    artifact = metadata.get("relayrun_artifact")
    require(isinstance(artifact, dict), metadata)
    transition = artifact.get("recovery_transition_artifact")
    require(isinstance(transition, dict), artifact)
    return transition


def _assert_transition_common(transition: dict[str, Any]) -> None:
    require(transition.get("schema_version") == "relayrun.recovery_transition.v0", transition)
    require(transition.get("diagnostics_only") is True, transition)
    require(transition.get("user_visible") is False, transition)
    require(transition.get("apply_allowed") is False, transition)
    require(transition.get("applied") is False, transition)
    require(transition.get("transition_created") is False, transition)
    require(transition.get("resume_mode") == "none", transition)
    blocked_reasons = transition.get("blocked_reasons")
    require(isinstance(blocked_reasons, list), transition)
    require("recovery_transition_not_implemented" in blocked_reasons, transition)
    require("recovery_transition_disabled" in blocked_reasons, transition)
    require("recovery_transition_dry_run_only" in blocked_reasons, transition)
    safety = transition.get("safety")
    require(isinstance(safety, dict), transition)
    require(safety.get("passes_through_output_pipeline") is True, transition)
    require(safety.get("direct_user_output_allowed") is False, transition)
    require(safety.get("contains_user_content") is False, transition)
    require(safety.get("contains_backend_payload") is False, transition)
    require(safety.get("contains_response_text") is False, transition)


def _assert_backend_payload_not_mutated(backend_payload: dict[str, Any] | None) -> None:
    require(isinstance(backend_payload, dict), backend_payload)
    backend_text = json.dumps(backend_payload, ensure_ascii=False)
    require("recovery_transition_artifact" not in backend_text, backend_payload)
    require("relayrun.recovery_transition.v0" not in backend_text, backend_payload)


def _assert_normal(root: Path, capture: _Capture, port: int) -> None:
    backend_payload, metadata, _ = _post(
        port=port,
        store_root=root,
        payload=_payload("Normal RelayRUN transition check", "design_talk"),
        capture=capture,
    )
    transition = _transition(metadata)
    _assert_transition_common(transition)
    if transition.get("proposed_transition_type") == "none":
        require(transition.get("source_node") is None, transition)
    else:
        require(transition.get("proposed_transition_type") == "context_repair", transition)
        require(transition.get("source_node") == "relaymem_retrieval", transition)
        require(transition.get("required_user_action") == "confirm_context_repair", transition)
    _assert_backend_payload_not_mutated(backend_payload)
    print("ok normal request emits unapplied recovery_transition_artifact")


def _assert_recovery_scene(root: Path, capture: _Capture, port: int) -> None:
    backend_payload, metadata, _ = _post(
        port=port,
        store_root=root,
        payload=_payload("Recover the current context using RelayMEM.", "recovery"),
        capture=capture,
        snippet_runtime_injection_enabled=True,
        snippet_runtime_dry_run_only=False,
    )
    transition = _transition(metadata)
    _assert_transition_common(transition)
    require(transition.get("proposed_transition_type") == "context_repair", transition)
    require(transition.get("source_node") in {"relayscn", "relaymem_retrieval", "relaymem_runtime_ctx"}, transition)
    require(transition.get("user_visible") is False, transition)
    _assert_backend_payload_not_mutated(backend_payload)
    print("ok recovery scene proposes context_repair without apply")


def _assert_unresolved_reference(root: Path, capture: _Capture, port: int) -> None:
    backend_payload, metadata, _ = _post(
        port=port,
        store_root=root,
        payload=_payload("それについて教えて", "design_talk"),
        capture=capture,
        snippet_runtime_injection_enabled=True,
        snippet_runtime_dry_run_only=False,
    )
    transition = _transition(metadata)
    _assert_transition_common(transition)
    require(transition.get("proposed_transition_type") == "ask_user_confirmation", transition)
    require(transition.get("source_node") == "relayint", transition)
    require(transition.get("source_node_alias") == "relayint_reference_intent", transition)
    require(transition.get("compatibility_source_node") == "relayint", transition)
    require(transition.get("required_user_action") == "clarify_reference", transition)
    _assert_backend_payload_not_mutated(backend_payload)
    print("ok unresolved reference proposes user confirmation without apply")


def _assert_backend_error(root: Path, capture: _Capture) -> None:
    backend_payload, metadata, status_code = _post(
        port=9,
        store_root=root,
        payload=_payload("Backend error transition check", "design_talk"),
        capture=capture,
        expected_status=502,
    )
    require(backend_payload is None, backend_payload)
    require(status_code == 502, status_code)
    transition = _transition(metadata)
    _assert_transition_common(transition)
    require(transition.get("proposed_transition_type") == "retry_safe_node", transition)
    require(transition.get("source_node") == "backend_forward", transition)
    require(transition.get("next_node") == "backend_forward", transition)
    print("ok backend error emits unapplied recovery transition and preserves error response")


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
            port = server.server_address[1]
            _assert_normal(store_root, capture, port)
            _assert_recovery_scene(store_root, capture, port)
            _assert_unresolved_reference(store_root, capture, port)
            _assert_backend_error(store_root, capture)
        finally:
            server.shutdown()
            thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
