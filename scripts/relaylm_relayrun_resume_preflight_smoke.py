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
from relaylm.relayrun import (
    build_relayrun_node,
    build_relayrun_resume_preflight,
    build_runtime_checkpoint_dry_run_artifact,
    write_relayrun_checkpoint_if_enabled,
)
from relaylm_relayrun_runtime_checkpoint_dry_run_smoke import (  # type: ignore[import-not-found]
    _BackendHandler,
    _Capture,
    _build_store,
)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _write_config(path: Path, *, port: int, trace_path: Path, store_root: Path) -> None:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    cfg["backends"]["local_backend"]["base_url"] = f"http://127.0.0.1:{port}/v1"
    cfg["trace"] = {"enabled": True, "path": str(trace_path)}
    cfg["model_routes"]["relaylm-default"]["mode"] = "pass_through"
    cfg["relayrun_resume_preflight_enabled"] = False
    cfg["relayrun_resume_dry_run_only"] = True
    cfg["memory"].update(
        {
            "root_path": str(store_root),
            "store_enabled": True,
            "retrieval_dry_run_only": False,
            "ctx_block_apply_enabled": True,
            "candidate_limit": 3,
            "token_budget_hint": 800,
            "token_budget_truncation_enabled": False,
        }
    )
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")


def _payload() -> dict[str, Any]:
    return {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": "resume preflight request"}],
        "metadata": {
            "scene_state": {
                "scene_type": "design_talk",
                "confidence": 0.95,
                "stability": 0.9,
            }
        },
        "stream": False,
    }


def _post_request(root: Path, capture: _Capture, port: int) -> tuple[dict[str, Any], dict[str, Any]]:
    trace_path = root / "trace.jsonl"
    cfg_path = root / "cfg.yaml"
    _write_config(cfg_path, port=port, trace_path=trace_path, store_root=root / "store")
    app = create_app(str(cfg_path))
    payload = _payload()
    original = json.loads(json.dumps(payload))
    before_count = capture.count()
    with TestClient(app) as client:
        resp = client.post("/v1/chat/completions", json=payload)
        require(resp.status_code == 200, resp.text)
    require(payload == original, payload)
    require(capture.count() == before_count + 1, capture.count())
    record = json.loads(trace_path.read_text(encoding="utf-8").strip().splitlines()[-1])
    metadata = record.get("metadata", {})
    require(isinstance(metadata, dict), record)
    return capture.get(before_count), metadata


def _assert_backend_payload_not_mutated(backend_payload: dict[str, Any]) -> None:
    backend_text = json.dumps(backend_payload, ensure_ascii=False)
    require("relayrun_artifact" not in backend_text, backend_payload)
    require("resume_preflight" not in backend_text, backend_payload)
    require("relayrun.resume_preflight.v0" not in backend_text, backend_payload)


def _assert_default_request(root: Path, capture: _Capture, port: int) -> None:
    backend_payload, metadata = _post_request(root, capture, port)
    artifact = metadata.get("relayrun_artifact")
    require(isinstance(artifact, dict), metadata)
    resume_preflight = artifact.get("resume_preflight")
    require(isinstance(resume_preflight, dict), artifact)
    require(resume_preflight.get("schema_version") == "relayrun.resume_preflight.v0", resume_preflight)
    require(resume_preflight.get("diagnostics_only") is True, resume_preflight)
    require(resume_preflight.get("resume_allowed") is False, resume_preflight)
    require(resume_preflight.get("resume_attempted") is False, resume_preflight)
    require(resume_preflight.get("resume_applied") is False, resume_preflight)
    require(resume_preflight.get("checkpoint_read_attempted") is False, resume_preflight)
    blocked_reasons = resume_preflight.get("blocked_reasons")
    require(isinstance(blocked_reasons, list), resume_preflight)
    require("resume_not_implemented" in blocked_reasons, resume_preflight)
    require("resume_disabled" in blocked_reasons, resume_preflight)
    require("resume_dry_run_only" in blocked_reasons, resume_preflight)
    _assert_backend_payload_not_mutated(backend_payload)
    require(metadata.get("relayrun_artifact", {}).get("resume_preflight") == resume_preflight, metadata)
    print("ok default request emits resume_preflight")
    print("ok backend payload not polluted by resume preflight")
    print("ok trace metadata includes resume_preflight")


def _valid_envelope(path: Path) -> dict[str, Any]:
    envelope = {
        "schema_version": "relayrun.checkpoint_envelope.v0",
        "diagnostics_only": True,
        "content_free": True,
        "run_id": "run-resume-valid",
        "request_id": "request-resume-valid",
        "turn_id": "request-resume-valid",
        "route_model": "relaylm-default",
        "node_statuses": [],
        "blocked_reasons": [],
        "checkpoint_persistence_plan": {"checkpoint_persisted": True, "write_allowed": True},
        "checkpoint_writer_preflight": {"preflight_passed": True, "write_allowed": True},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(envelope, ensure_ascii=False), encoding="utf-8")
    return envelope


def _preflight_for(path: Path, root: Path) -> dict[str, Any]:
    return build_relayrun_resume_preflight(
        resume_preflight_enabled=True,
        resume_dry_run_only=True,
        checkpoint_path=path.relative_to(REPO_ROOT).as_posix(),
        checkpoint_root=root.relative_to(REPO_ROOT).as_posix(),
    )


def _assert_valid_checkpoint_read(root: Path) -> None:
    checkpoint_root = root / "resume-valid"
    checkpoint = checkpoint_root / "run" / "turn.json"
    _valid_envelope(checkpoint)
    preflight = _preflight_for(checkpoint, checkpoint_root)
    require(preflight.get("checkpoint_read_attempted") is True, preflight)
    require(preflight.get("checkpoint_read_ok") is True, preflight)
    require(preflight.get("checkpoint_schema_valid") is True, preflight)
    require(preflight.get("content_free") is True, preflight)
    require(preflight.get("resume_allowed") is False, preflight)
    blocked_reasons = preflight.get("blocked_reasons")
    require("resume_not_implemented" in blocked_reasons, preflight)
    require("resume_dry_run_only" in blocked_reasons, preflight)
    print("ok valid content-free checkpoint read preflight")


def _assert_malformed_json(root: Path) -> None:
    checkpoint_root = root / "resume-malformed"
    checkpoint = checkpoint_root / "bad.json"
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    checkpoint.write_text("{bad json", encoding="utf-8")
    preflight = _preflight_for(checkpoint, checkpoint_root)
    require("resume_checkpoint_malformed_json" in preflight.get("blocked_reasons", []), preflight)
    require(preflight.get("checkpoint_read_ok") is False, preflight)
    print("ok malformed checkpoint json blocked")


def _assert_wrong_schema(root: Path) -> None:
    checkpoint_root = root / "resume-wrong-schema"
    checkpoint = checkpoint_root / "wrong.json"
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    checkpoint.write_text(json.dumps({"schema_version": "wrong", "content_free": True}), encoding="utf-8")
    preflight = _preflight_for(checkpoint, checkpoint_root)
    require(preflight.get("checkpoint_read_ok") is True, preflight)
    require(preflight.get("checkpoint_schema_valid") is False, preflight)
    require("resume_checkpoint_schema_invalid" in preflight.get("blocked_reasons", []), preflight)
    print("ok wrong checkpoint schema blocked")


def _assert_content_free_false(root: Path) -> None:
    checkpoint_root = root / "resume-content-false"
    checkpoint = checkpoint_root / "content-false.json"
    envelope = _valid_envelope(checkpoint)
    envelope["content_free"] = False
    checkpoint.write_text(json.dumps(envelope), encoding="utf-8")
    preflight = _preflight_for(checkpoint, checkpoint_root)
    require(preflight.get("checkpoint_schema_valid") is True, preflight)
    require(preflight.get("content_free") is False, preflight)
    require("resume_checkpoint_content_policy_failed" in preflight.get("blocked_reasons", []), preflight)
    print("ok content_free false checkpoint blocked")


def _assert_missing_file(root: Path) -> None:
    checkpoint_root = root / "resume-missing"
    checkpoint = checkpoint_root / "missing.json"
    preflight = _preflight_for(checkpoint, checkpoint_root)
    require(preflight.get("checkpoint_read_attempted") is True, preflight)
    require("resume_checkpoint_missing" in preflight.get("blocked_reasons", []), preflight)
    print("ok missing checkpoint blocked")


def _assert_traversal_blocked(root: Path) -> None:
    preflight = build_relayrun_resume_preflight(
        resume_preflight_enabled=True,
        resume_dry_run_only=True,
        checkpoint_path="../outside.json",
        checkpoint_root=(root / "resume-traversal").relative_to(REPO_ROOT).as_posix(),
    )
    require(preflight.get("checkpoint_read_attempted") is False, preflight)
    require("resume_checkpoint_path_traversal_detected" in preflight.get("blocked_reasons", []), preflight)
    print("ok traversal checkpoint path blocked")


def _assert_raw_content_key_blocked(root: Path) -> None:
    checkpoint_root = root / "resume-raw-key"
    checkpoint = checkpoint_root / "raw-key.json"
    envelope = _valid_envelope(checkpoint)
    envelope["raw_user_message"] = "must not resume from raw content"
    checkpoint.write_text(json.dumps(envelope), encoding="utf-8")
    preflight = _preflight_for(checkpoint, checkpoint_root)
    require(preflight.get("checkpoint_schema_valid") is True, preflight)
    require(preflight.get("content_free") is False, preflight)
    require("resume_checkpoint_content_policy_failed" in preflight.get("blocked_reasons", []), preflight)
    print("ok raw content checkpoint key blocked")


def _assert_writer_envelope_read(root: Path) -> None:
    checkpoint_root = root / "resume-writer-envelope"
    artifact = build_runtime_checkpoint_dry_run_artifact(
        request_id="request-writer-resume",
        run_id="run-writer-resume",
        route_model="relaylm-default",
        node_statuses=[build_relayrun_node(node_name="request_received", node_status="completed")],
        checkpoint_target_root=checkpoint_root.relative_to(REPO_ROOT).as_posix(),
    )
    result = write_relayrun_checkpoint_if_enabled(
        artifact,
        write_enabled=True,
        dry_run_only=False,
    )
    persisted_path = result.get("persisted_path")
    require(isinstance(persisted_path, str), result)
    preflight = build_relayrun_resume_preflight(
        resume_preflight_enabled=True,
        resume_dry_run_only=True,
        checkpoint_path=persisted_path,
        checkpoint_root=checkpoint_root.relative_to(REPO_ROOT).as_posix(),
    )
    require(preflight.get("checkpoint_read_ok") is True, preflight)
    require(preflight.get("checkpoint_schema_valid") is True, preflight)
    require(preflight.get("content_free") is True, preflight)
    print("ok writer checkpoint envelope can be read by resume preflight")


def main() -> int:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as td:
        root = Path(td)
        _build_store(root / "store")
        capture = _Capture()
        _BackendHandler.capture = capture
        server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_address[1]
            _assert_default_request(root, capture, port)
            _assert_valid_checkpoint_read(root)
            _assert_malformed_json(root)
            _assert_wrong_schema(root)
            _assert_content_free_false(root)
            _assert_missing_file(root)
            _assert_traversal_blocked(root)
            _assert_raw_content_key_blocked(root)
            _assert_writer_envelope_read(root)
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
