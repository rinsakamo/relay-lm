from __future__ import annotations

import json
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import yaml
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.app import create_app
from relaylm.relayrun import (
    build_relayrun_checkpoint_index_diagnostics,
    build_relayrun_node,
    build_runtime_checkpoint_dry_run_artifact,
    write_relayrun_checkpoint_if_enabled,
)


class _Capture:
    def __init__(self) -> None:
        self.payloads: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def add(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self.payloads.append(payload)

    def count(self) -> int:
        with self._lock:
            return len(self.payloads)

    def get(self, index: int) -> dict[str, Any]:
        with self._lock:
            return self.payloads[index]


class _BackendHandler(BaseHTTPRequestHandler):
    capture: _Capture

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return

    def do_POST(self) -> None:  # noqa: N802
        raw = self.rfile.read(int(self.headers.get("content-length", "0")))
        payload = json.loads(raw.decode("utf-8")) if raw else {}
        type(self).capture.add(payload)
        body = json.dumps(
            {
                "id": "chatcmpl-relayrun-checkpoint-index-smoke",
                "object": "chat.completion",
                "choices": [
                    {"index": 0, "message": {"role": "assistant", "content": "ok"}}
                ],
            }
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _write_config(path: Path, *, port: int, trace_path: Path, checkpoint_root: str) -> None:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    cfg["backends"]["local_backend"]["base_url"] = f"http://127.0.0.1:{port}/v1"
    cfg["trace"] = {"enabled": True, "path": str(trace_path)}
    cfg["relayrun_checkpoint_root"] = checkpoint_root
    path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")


def _payload(content: str = "RAW_USER_SHOULD_NOT_INDEX") -> dict[str, Any]:
    return {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": content}],
        "stream": False,
    }


def _assert_backend_payload_not_mutated(backend_payload: dict[str, Any]) -> None:
    backend_text = json.dumps(backend_payload, ensure_ascii=False)
    require("relayrun_artifact" not in backend_text, backend_payload)
    require("checkpoint_index" not in backend_text, backend_payload)
    require("relayrun.checkpoint_index.v0" not in backend_text, backend_payload)


def _assert_no_forbidden_index_content(index: dict[str, Any]) -> None:
    forbidden = {
        "backend_payload",
        "messages",
        "raw_messages",
        "raw_user_message",
        "response_text",
        "prompt",
        "prompt_text",
        "snippet_text",
        "page_body",
    }

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                require(str(key) not in forbidden, index)
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, str):
            require("RAW_USER_SHOULD_NOT_INDEX" not in value, index)
            require("BACKEND_PAYLOAD_SHOULD_NOT_INDEX" not in value, index)
            require("RESPONSE_SHOULD_NOT_INDEX" not in value, index)
            require("SNIPPET_SHOULD_NOT_INDEX" not in value, index)

    walk(index)


def _base_artifact(*, root: str, run_id: str, turn_id: str) -> dict[str, Any]:
    return build_runtime_checkpoint_dry_run_artifact(
        request_id=f"request-{turn_id}",
        run_id=run_id,
        turn_id=turn_id,
        route_model="relaylm-default",
        backend_name="local_backend",
        character_id="default",
        stream_enabled=False,
        node_statuses=[
            build_relayrun_node(node_name="request_received", node_status="completed"),
            build_relayrun_node(node_name="backend_forward", node_status="completed"),
        ],
        blocked_reasons=[],
        stream_started=False,
        first_token_sent=False,
        checkpoint_target_root=root,
        checkpoint_index_enabled=False,
        checkpoint_index_dry_run_only=True,
    )


def _persist_valid_checkpoint(root: str, *, run_id: str, turn_id: str) -> Path:
    artifact = _base_artifact(root=root, run_id=run_id, turn_id=turn_id)
    updated = write_relayrun_checkpoint_if_enabled(
        artifact,
        write_enabled=True,
        dry_run_only=False,
    )
    require(updated.get("checkpoint_persisted") is True, updated)
    path = Path(str(updated.get("persisted_path")))
    require(path.exists(), updated)
    return path


def _blocked_by_reason(index: dict[str, Any], reason: str) -> bool:
    for item in index.get("blocked_files", []):
        if reason in item.get("blocked_reasons", []):
            return True
    return False


def _assert_default_request(capture: _Capture, port: int) -> None:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as td:
        trace_path = Path(td) / "trace.jsonl"
        cfg_path = Path(td) / "cfg.yaml"
        checkpoint_root = (Path(td) / "checkpoints").relative_to(REPO_ROOT).as_posix()
        _write_config(cfg_path, port=port, trace_path=trace_path, checkpoint_root=checkpoint_root)
        app = create_app(str(cfg_path))
        payload = _payload()
        original = json.loads(json.dumps(payload))
        before_count = capture.count()
        with TestClient(app) as client:
            resp = client.post("/v1/chat/completions", json=payload)
            require(resp.status_code == 200, resp.text)
        require(payload == original, payload)
        backend_payload = capture.get(before_count)
        _assert_backend_payload_not_mutated(backend_payload)
        record = json.loads(trace_path.read_text(encoding="utf-8").strip().splitlines()[-1])
        metadata = record.get("metadata", {})
        artifact = metadata.get("relayrun_artifact")
        require(isinstance(artifact, dict), metadata)
        index = artifact.get("checkpoint_index")
        require(isinstance(index, dict), artifact)
        require(index.get("schema_version") == "relayrun.checkpoint_index.v0", index)
        require(index.get("diagnostics_only") is True, index)
        require(index.get("index_enabled") is False, index)
        require(index.get("dry_run_only") is True, index)
        require(index.get("scan_attempted") is False, index)
        require("checkpoint_index_disabled" in index.get("blocked_reasons", []), index)
        require("checkpoint_index_dry_run_only" in index.get("blocked_reasons", []), index)
        require(metadata.get("relayrun_artifact", {}).get("checkpoint_index") == index, metadata)
        _assert_no_forbidden_index_content(index)
        print("ok default request emits checkpoint_index without scan")
        print("ok backend payload excludes checkpoint_index")
        print("ok trace metadata includes checkpoint_index")


def _assert_scan_cases() -> None:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as td:
        root = Path(td) / "checkpoints"
        root.mkdir()
        root_rel = root.relative_to(REPO_ROOT).as_posix()
        valid_path = _persist_valid_checkpoint(root_rel, run_id="run-index-valid", turn_id="turn-valid")
        (root / "malformed.json").write_text("{not json", encoding="utf-8")
        (root / "wrong_schema.json").write_text(json.dumps({"schema_version": "wrong"}), encoding="utf-8")
        bad_content = json.loads(valid_path.read_text(encoding="utf-8"))
        bad_content["content_free"] = False
        (root / "content_free_false.json").write_text(json.dumps(bad_content), encoding="utf-8")
        forbidden = json.loads(valid_path.read_text(encoding="utf-8"))
        forbidden["raw_user_message"] = "RAW_USER_SHOULD_NOT_INDEX"
        (root / "forbidden_key.json").write_text(json.dumps(forbidden), encoding="utf-8")
        outside = Path(td) / "outside.json"
        outside.write_text(valid_path.read_text(encoding="utf-8"), encoding="utf-8")
        try:
            (root / "outside_link.json").symlink_to(outside)
        except (OSError, NotImplementedError):
            pass

        index = build_relayrun_checkpoint_index_diagnostics(
            checkpoint_root=root_rel,
            index_enabled=True,
            dry_run_only=False,
            max_files=100,
        )
        require(index.get("scan_attempted") is True, index)
        require(index.get("blocked_reasons") == [], index)
        require(index.get("scanned_files") >= 5, index)
        summaries = index.get("indexed_checkpoints")
        require(isinstance(summaries, list), index)
        valid_summary = next(
            (item for item in summaries if item.get("run_id") == "run-index-valid"),
            None,
        )
        require(isinstance(valid_summary, dict), index)
        require(valid_summary.get("checkpoint_path") == Path(valid_path).relative_to(root_rel).as_posix(), valid_summary)
        require(valid_summary.get("turn_id") == "turn-valid", valid_summary)
        require(valid_summary.get("route_model") == "relaylm-default", valid_summary)
        require(valid_summary.get("backend_name") == "local_backend", valid_summary)
        require(valid_summary.get("run_status") == "diagnostics_only", valid_summary)
        require(valid_summary.get("checkpoint_persisted") is True, valid_summary)
        require(valid_summary.get("node_count") == 2, valid_summary)
        require(valid_summary.get("blocked_reason_count") == 0, valid_summary)
        require(valid_summary.get("content_free") is True, valid_summary)
        require(_blocked_by_reason(index, "checkpoint_index_malformed_json"), index)
        require(_blocked_by_reason(index, "checkpoint_index_schema_invalid"), index)
        require(_blocked_by_reason(index, "checkpoint_index_content_policy_failed"), index)
        require(
            _blocked_by_reason(index, "checkpoint_index_symlink_blocked")
            or not (root / "outside_link.json").exists(),
            index,
        )
        _assert_no_forbidden_index_content(index)
        print("ok enabled scan indexes valid envelopes and blocks unsafe files")
        print("ok writer checkpoint envelope can be indexed")
        print("ok indexed summaries exclude forbidden raw fields")


def _assert_truncation() -> None:
    max_files = 2
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as td:
        root = Path(td) / "checkpoints"
        root.mkdir()
        root_rel = root.relative_to(REPO_ROOT).as_posix()
        _persist_valid_checkpoint(root_rel, run_id="run-index-cap-1", turn_id="turn-1")
        _persist_valid_checkpoint(root_rel, run_id="run-index-cap-2", turn_id="turn-2")
        _persist_valid_checkpoint(root_rel, run_id="run-index-cap-3", turn_id="turn-3")
        (root / "malformed-cap.json").write_text("{not json", encoding="utf-8")
        index = build_relayrun_checkpoint_index_diagnostics(
            checkpoint_root=root_rel,
            index_enabled=True,
            dry_run_only=False,
            max_files=max_files,
        )
        require(index.get("scan_attempted") is True, index)
        require(index.get("truncated") is True, index)
        require(index.get("scanned_files") <= max_files, index)
        indexed_count = len(index.get("indexed_checkpoints", []))
        blocked_count = len(index.get("blocked_files", []))
        require(indexed_count + blocked_count <= max_files, index)
        require("checkpoint_index_truncated" in index.get("blocked_reasons", []), index)
        print("ok max_files truncation bounds traversal and results")


def main() -> int:
    capture = _Capture()
    _BackendHandler.capture = capture
    server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
    port = int(server.server_address[1])
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        _assert_default_request(capture, port)
        _assert_scan_cases()
        _assert_truncation()
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
