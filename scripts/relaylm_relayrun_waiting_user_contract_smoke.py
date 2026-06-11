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
    cfg["relayrun_waiting_user_contract_enabled"] = False
    cfg["relayrun_waiting_user_contract_dry_run_only"] = True
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


def _relayrun(metadata: dict[str, Any]) -> dict[str, Any]:
    artifact = metadata.get("relayrun_artifact")
    require(isinstance(artifact, dict), metadata)
    return artifact


def _contract(metadata: dict[str, Any]) -> dict[str, Any]:
    artifact = _relayrun(metadata)
    contract = artifact.get("waiting_user_contract")
    require(isinstance(contract, dict), artifact)
    require(metadata.get("relayrun_artifact", {}).get("waiting_user_contract") == contract, metadata)
    return contract


def _assert_contract_common(contract: dict[str, Any]) -> None:
    require(contract.get("schema_version") == "relayrun.waiting_user_contract.v0", contract)
    require(contract.get("diagnostics_only") is True, contract)
    require(contract.get("user_visible") is False, contract)
    require(contract.get("apply_allowed") is False, contract)
    require(contract.get("applied") is False, contract)
    source_artifacts = contract.get("source_artifacts")
    require(isinstance(source_artifacts, dict), contract)
    require(isinstance(source_artifacts.get("resume_preflight"), dict), contract)
    require(isinstance(source_artifacts.get("recovery_transition_artifact"), dict), contract)
    blocked_reasons = contract.get("blocked_reasons")
    require(isinstance(blocked_reasons, list), contract)
    require("waiting_user_contract_disabled" in blocked_reasons, contract)
    require("waiting_user_contract_dry_run_only" in blocked_reasons, contract)
    safety = contract.get("safety")
    require(isinstance(safety, dict), contract)
    require(safety.get("direct_user_output_allowed") is False, contract)
    require(safety.get("passes_through_output_pipeline_required") is True, contract)
    require(safety.get("contains_user_content") is False, contract)
    require(safety.get("contains_backend_payload") is False, contract)
    require(safety.get("contains_response_text") is False, contract)


def _assert_backend_payload_not_mutated(backend_payload: dict[str, Any] | None) -> None:
    require(isinstance(backend_payload, dict), backend_payload)
    backend_text = json.dumps(backend_payload, ensure_ascii=False)
    require("waiting_user_contract" not in backend_text, backend_payload)
    require("relayrun.waiting_user_contract.v0" not in backend_text, backend_payload)
    require("recovery_transition_artifact" not in backend_text, backend_payload)


def _assert_no_raw_content(contract: dict[str, Any]) -> None:
    text = json.dumps(contract, ensure_ascii=False)
    require("Recover the current context" not in text, contract)
    require("それについて教えて" not in text, contract)
    require("Backend error waiting-user contract check" not in text, contract)


def _assert_normal(root: Path, capture: _Capture, port: int) -> None:
    backend_payload, metadata, _ = _post(
        port=port,
        store_root=root,
        payload=_payload("Normal waiting-user contract check", "design_talk"),
        capture=capture,
    )
    contract = _contract(metadata)
    _assert_contract_common(contract)
    require(contract.get("waiting_user_required") is False, contract)
    require(contract.get("waiting_user_reason") is None, contract)
    require(contract.get("source_node") is None, contract)
    require(contract.get("allowed_user_actions") == [], contract)
    _assert_backend_payload_not_mutated(backend_payload)
    _assert_no_raw_content(contract)
    print("ok normal request emits waiting_user_contract without waiting requirement")
    print("ok trace metadata includes waiting_user_contract")


def _assert_recovery_scene(root: Path, capture: _Capture, port: int) -> None:
    backend_payload, metadata, _ = _post(
        port=port,
        store_root=root,
        payload=_payload("Recover the current context using RelayMEM.", "recovery"),
        capture=capture,
        snippet_runtime_injection_enabled=True,
        snippet_runtime_dry_run_only=False,
    )
    contract = _contract(metadata)
    _assert_contract_common(contract)
    require(contract.get("waiting_user_required") is True, contract)
    require(contract.get("waiting_user_reason") == "recovery_context_repair", contract)
    require(contract.get("source_node") in {"relayscn", "relaymem_runtime_ctx"}, contract)
    actions = contract.get("allowed_user_actions")
    require(isinstance(actions, list), contract)
    require("confirm_context" in actions, contract)
    require("provide_clarification" in actions, contract)
    require("waiting_user_apply_not_implemented" in contract.get("blocked_reasons", []), contract)
    _assert_backend_payload_not_mutated(backend_payload)
    _assert_no_raw_content(contract)
    print("ok recovery scene sets waiting_user_required for context repair")


def _assert_unresolved_reference(root: Path, capture: _Capture, port: int) -> None:
    backend_payload, metadata, _ = _post(
        port=port,
        store_root=root,
        payload=_payload("それについて教えて", "design_talk"),
        capture=capture,
        snippet_runtime_injection_enabled=True,
        snippet_runtime_dry_run_only=False,
    )
    contract = _contract(metadata)
    _assert_contract_common(contract)
    require(contract.get("waiting_user_required") is True, contract)
    require(contract.get("waiting_user_reason") == "unresolved_reference", contract)
    require(contract.get("source_node") == "relayref", contract)
    require(contract.get("source_node_alias") == "relayint_reference_repair", contract)
    require(contract.get("compatibility_source_node") == "relayref", contract)
    actions = contract.get("allowed_user_actions")
    require(isinstance(actions, list), contract)
    require("provide_clarification" in actions, contract)
    _assert_backend_payload_not_mutated(backend_payload)
    _assert_no_raw_content(contract)
    print("ok unresolved reference sets waiting_user_required for clarification")


def _assert_backend_error(root: Path, capture: _Capture) -> None:
    backend_payload, metadata, status_code = _post(
        port=9,
        store_root=root,
        payload=_payload("Backend error waiting-user contract check", "design_talk"),
        capture=capture,
        expected_status=502,
    )
    require(backend_payload is None, backend_payload)
    require(status_code == 502, status_code)
    contract = _contract(metadata)
    _assert_contract_common(contract)
    require(contract.get("waiting_user_required") is True, contract)
    require(contract.get("waiting_user_reason") == "backend_error_recovery_confirmation", contract)
    require(contract.get("source_node") == "backend_forward", contract)
    actions = contract.get("allowed_user_actions")
    require(isinstance(actions, list), contract)
    require("confirm_retry" in actions, contract)
    require("cancel_recovery" in actions, contract)
    _assert_no_raw_content(contract)
    print("ok backend error emits waiting_user_contract and preserves error response")


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
            _assert_normal(store_root, capture, port)
            _assert_recovery_scene(store_root, capture, port)
            _assert_unresolved_reference(store_root, capture, port)
            _assert_backend_error(store_root, capture)
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
