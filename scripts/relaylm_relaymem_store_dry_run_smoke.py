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
from relaylm.relaymem_store import build_relaymem_store_diagnostics


class _Capture:
    def __init__(self) -> None:
        self.payloads: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def add(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self.payloads.append(payload)

    def last(self) -> dict[str, Any]:
        with self._lock:
            if not self.payloads:
                raise AssertionError("no backend payload captured")
            return self.payloads[-1]


class _BackendHandler(BaseHTTPRequestHandler):
    capture: _Capture

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/chat/completions":
            self.send_response(404)
            self.end_headers()
            return
        raw = self.rfile.read(int(self.headers.get("content-length", "0")))
        payload = json.loads(raw.decode("utf-8")) if raw else {}
        type(self).capture.add(payload)
        body = json.dumps(
            {
                "id": "chatcmpl-relaymem-store-smoke",
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


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _last_retrieval_artifact(trace_path: Path) -> dict[str, Any]:
    lines = trace_path.read_text(encoding="utf-8").strip().splitlines()
    require(bool(lines), "trace is empty")
    record = json.loads(lines[-1])
    artifact = record.get("metadata", {}).get("relaymem_retrieval_artifact")
    require(isinstance(artifact, dict), record)
    return artifact


def _write_config(path: Path, *, port: int, trace_path: Path, memory: dict[str, Any]) -> None:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    cfg["backends"]["local_backend"]["base_url"] = f"http://127.0.0.1:{port}/v1"
    cfg["trace"] = {"enabled": True, "path": str(trace_path)}
    cfg["model_routes"]["relaylm-default"]["mode"] = "pass_through"
    cfg["memory"].update(memory)
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")


def _post_design(client: TestClient) -> dict[str, Any]:
    payload = {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": "RelayMEM retrieval design"}],
        "metadata": {
            "scene_state": {
                "scene_type": "design_talk",
                "confidence": 0.95,
                "stability": 0.9,
            }
        },
        "stream": False,
    }
    resp = client.post("/v1/chat/completions", json=payload)
    require(resp.status_code == 200, resp.text)
    return payload


def _assert_no_backend_artifact(payload: dict[str, Any]) -> None:
    forbidden = {
        "relaymem_retrieval_artifact",
        "relaymem_store_diagnostics",
        "store_diagnostics",
        "ctx_block",
    }
    require(forbidden.isdisjoint(payload), payload)


def main() -> int:
    disabled = build_relaymem_store_diagnostics(
        root_path="memory_store",
        store_enabled=False,
        retrieval_dry_run_only=True,
    )
    require(disabled["store_enabled"] is False, disabled)
    require(disabled["fallback_reason"] == "memory_store_disabled", disabled)
    print("ok disabled store emits fail-soft diagnostics")

    missing = build_relaymem_store_diagnostics(
        root_path="/tmp/relaylm-missing-memory-store-for-smoke",
        store_enabled=True,
        retrieval_dry_run_only=True,
    )
    require(missing["store_enabled"] is True, missing)
    require(missing["root_present"] is False, missing)
    require(missing["fallback_reason"] == "memory_store_root_missing", missing)
    print("ok missing root emits fail-soft diagnostics")

    with tempfile.TemporaryDirectory() as store_td:
        store_root = Path(store_td)
        mem_root = store_root / "memory" / "mem"
        (mem_root / "projects").mkdir(parents=True)
        (store_root / "memory" / "raw").mkdir(parents=True)
        (mem_root / "index.md").write_text("# Index\n", encoding="utf-8")
        (mem_root / "log.md").write_text("# Log\n", encoding="utf-8")
        (mem_root / "projects" / "relaymem.md").write_text("# RelayMEM\n", encoding="utf-8")
        (mem_root / "projects" / "unsupported.txt").write_text("bad", encoding="utf-8")
        (mem_root / "projects" / "broken.md").write_bytes(b"\xff\xfe\x00")

        store = build_relaymem_store_diagnostics(
            root_path=str(store_root),
            store_enabled=True,
            retrieval_dry_run_only=True,
        )
        require(store["index_present"] is True, store)
        require(store["pages_discovered"] > 0, store)
        blocked_reasons = {item["reason"] for item in store["blocked_files"]}
        require("unsupported_file_type" in blocked_reasons, store)
        require("malformed_or_unreadable_file" in blocked_reasons, store)
        validation = store["validation"]
        require(validation["full_file_reads"] is False, store)
        require(validation["full_tree_materialized"] is False, store)
        require(validation["max_sample_bytes"] == 4096, store)
        print("ok minimal store discovers pages and blocks malformed files")

        with tempfile.TemporaryDirectory() as capped_td:
            capped_root = Path(capped_td)
            capped_mem = capped_root / "memory" / "mem" / "projects"
            capped_mem.mkdir(parents=True)
            (capped_root / "memory" / "mem" / "index.md").write_text("# Index\n", encoding="utf-8")
            (capped_root / "memory" / "mem" / "log.md").write_text("# Log\n", encoding="utf-8")
            for idx in range(150):
                (capped_mem / f"page_{idx:03d}.md").write_text("# Page\n" + ("x" * 8192), encoding="utf-8")
            capped = build_relaymem_store_diagnostics(
                root_path=str(capped_root),
                store_enabled=True,
                retrieval_dry_run_only=True,
            )
            capped_validation = capped["validation"]
            require(capped_validation["files_seen"] == capped_validation["max_files_to_scan"], capped)
            require(capped_validation["files_validated"] == capped_validation["max_files_to_validate"], capped)
            require(capped_validation["scan_truncated"] is True, capped)
            require(capped_validation["validation_truncated"] is True, capped)
            require(capped_validation["full_tree_materialized"] is False, capped)
            require(capped_validation["full_file_reads"] is False, capped)
            require(capped["fallback_reason"] == "memory_store_scan_truncated", capped)
            print("ok store validation streams walk and caps scanned files")

        capture = _Capture()
        _BackendHandler.capture = capture
        server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
        port = int(server.server_address[1])
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as disabled_td:
                trace_path = Path(disabled_td) / "trace.jsonl"
                cfg_path = Path(disabled_td) / "cfg.yaml"
                _write_config(
                    cfg_path,
                    port=port,
                    trace_path=trace_path,
                    memory={"store_enabled": False, "root_path": str(store_root)},
                )
                app = create_app(str(cfg_path))
                with TestClient(app) as client:
                    _post_design(client)
                    artifact = _last_retrieval_artifact(trace_path)
                    store_diag = artifact.get("store_diagnostics")
                    require(isinstance(store_diag, dict), artifact)
                    require(store_diag["store_enabled"] is False, store_diag)
                    require(
                        store_diag["fallback_reason"] == "memory_store_disabled",
                        store_diag,
                    )
                    print("ok runtime artifact emits disabled store diagnostics")

            with tempfile.TemporaryDirectory() as app_td:
                trace_path = Path(app_td) / "trace.jsonl"
                cfg_path = Path(app_td) / "cfg.yaml"
                _write_config(
                    cfg_path,
                    port=port,
                    trace_path=trace_path,
                    memory={
                        "store_enabled": True,
                        "retrieval_dry_run_only": True,
                        "root_path": str(store_root),
                    },
                )
                app = create_app(str(cfg_path))
                with TestClient(app) as client:
                    payload = _post_design(client)
                    artifact = _last_retrieval_artifact(trace_path)
                    store_diag = artifact.get("store_diagnostics")
                    require(isinstance(store_diag, dict), artifact)
                    require(store_diag["store_enabled"] is True, store_diag)
                    require(store_diag["index_present"] is True, store_diag)
                    require(store_diag["pages_discovered"] > 0, store_diag)
                    require(store_diag["validation"]["full_tree_materialized"] is False, store_diag)
                    require(store_diag["validation"]["full_file_reads"] is False, store_diag)
                    require(artifact["selected"] == [], artifact)
                    require(artifact["ctx_block"] is None, artifact)
                    _assert_no_backend_artifact(capture.last())
                    require(
                        capture.last().get("metadata") == payload["metadata"],
                        capture.last(),
                    )
                    print("ok runtime artifact includes store diagnostics without mutation")
        finally:
            server.shutdown()
            server.server_close()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
