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
from relaylm.relayint import build_relayint_reference_repair_dry_run
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
) -> None:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    cfg["backends"]["local_backend"]["base_url"] = f"http://127.0.0.1:{port}/v1"
    cfg["trace"] = {"enabled": True, "path": str(trace_path)}
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


def _payload(content: Any) -> dict[str, Any]:
    return {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": content}],
        "metadata": {
            "scene_state": {
                "scene_type": "design_talk",
                "confidence": 0.95,
                "stability": 0.9,
            }
        },
        "stream": False,
    }


def _assert_wrapper_direct_call() -> None:
    artifact = build_relayint_reference_repair_dry_run(
        relayscn_artifact={
            "scene_state": {
                "scene_type": "design_talk",
                "confidence": 0.95,
                "stability": 0.9,
            },
            "scene_policy": {},
            "persistence_block": False,
            "persistence_block_reasons": [],
        },
        messages=[{"role": "user", "content": "それを直して"}],
        ctx_hints={},
    )
    require(artifact.get("schema_version") == "relayref.dry_run_artifact.v0", artifact)
    require(artifact.get("diagnostics_only") is True, artifact)
    require(artifact.get("apply_allowed") is False, artifact)
    require(artifact.get("relayint_alias") is True, artifact)
    require(artifact.get("source_compat_module") == "relayref", artifact)
    require(artifact.get("unresolved_reference_detected") is True, artifact)
    require("unresolved_reference_detected" in artifact.get("mode_reasons", []), artifact)
    print("ok RelayINT reference repair wrapper preserves relayref artifact contract")


def _assert_app_uses_wrapper(root: Path, capture: _Capture, port: int) -> None:
    payload = _payload("それを直して")

    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as td:
        trace_path = Path(td) / "trace.jsonl"
        cfg_path = Path(td) / "cfg.yaml"
        _write_config(
            cfg_path,
            port=port,
            trace_path=trace_path,
            store_root=root,
        )
        app = create_app(str(cfg_path))
        original = json.loads(json.dumps(payload, ensure_ascii=False))
        before_count = capture.count()
        with TestClient(app) as client:
            resp = client.post("/v1/chat/completions", json=payload)
            require(resp.status_code == 200, resp.text)
            response_body = resp.json()

        require(payload == original, payload)
        require(capture.count() > before_count, capture.count())
        backend_payload = capture.get(before_count)
        require(backend_payload.get("messages") == payload["messages"], backend_payload)

        choices = response_body.get("choices")
        require(isinstance(choices, list) and choices, response_body)
        message = choices[0].get("message")
        require(isinstance(message, dict), response_body)
        require(message.get("content") == "ok", response_body)

        record = json.loads(trace_path.read_text(encoding="utf-8").strip().splitlines()[-1])
        metadata = record.get("metadata", {})
        require(isinstance(metadata, dict), record)
        artifact = metadata.get("relayref")
        require(isinstance(artifact, dict), metadata)
        require(artifact.get("schema_version") == "relayref.dry_run_artifact.v0", artifact)
        require(artifact.get("relayint_alias") is True, artifact)
        require(artifact.get("source_compat_module") == "relayref", artifact)
        require(artifact.get("unresolved_reference_detected") is True, artifact)
        require(artifact.get("apply_allowed") is False, artifact)
        require(artifact.get("auto_resume_allowed") is False, artifact)

    print("ok app records reference repair artifact through RelayINT wrapper")


def main() -> None:
    _assert_wrapper_direct_call()

    capture = _Capture()
    server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
    _BackendHandler.capture = capture
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as store_dir:
            _assert_app_uses_wrapper(
                root=_build_store(Path(store_dir)),
                capture=capture,
                port=server.server_address[1],
            )
    finally:
        server.shutdown()
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
