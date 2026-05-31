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
from relaylm.relaymem_store import discover_relaymem_page_candidates


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
                "id": "chatcmpl-relaymem-selection-smoke",
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


def _write_config(
    path: Path,
    *,
    port: int,
    trace_path: Path,
    store_root: Path,
    store_enabled: bool,
    candidate_limit: int = 3,
) -> None:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    cfg["backends"]["local_backend"]["base_url"] = f"http://127.0.0.1:{port}/v1"
    cfg["trace"] = {"enabled": True, "path": str(trace_path)}
    cfg["model_routes"]["relaylm-default"]["mode"] = "pass_through"
    cfg["memory"].update(
        {
            "store_enabled": store_enabled,
            "retrieval_dry_run_only": True,
            "root_path": str(store_root),
            "candidate_limit": candidate_limit,
        }
    )
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")


def _scene_payload(scene_type: str, content: str) -> dict[str, Any]:
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


def _post_and_get_artifact(
    client: TestClient,
    trace_path: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    resp = client.post("/v1/chat/completions", json=payload)
    require(resp.status_code == 200, resp.text)
    lines = trace_path.read_text(encoding="utf-8").strip().splitlines()
    require(bool(lines), "trace is empty")
    record = json.loads(lines[-1])
    artifact = record.get("metadata", {}).get("relaymem_retrieval_artifact")
    require(isinstance(artifact, dict), record)
    return artifact


def _assert_no_backend_artifact(payload: dict[str, Any]) -> None:
    forbidden = {
        "relaymem_retrieval_artifact",
        "selected_mem_candidates",
        "ctx_block",
        "store_diagnostics",
    }
    require(forbidden.isdisjoint(payload), payload)


def _build_store(root: Path) -> None:
    projects = root / "memory" / "mem" / "projects"
    concepts = root / "memory" / "mem" / "concepts"
    summaries = root / "memory" / "mem" / "summaries"
    projects.mkdir(parents=True)
    concepts.mkdir(parents=True)
    summaries.mkdir(parents=True)
    (root / "memory" / "mem" / "index.md").write_text("# Index\nRelayMEM\n", encoding="utf-8")
    (root / "memory" / "mem" / "log.md").write_text("# Log\n", encoding="utf-8")
    for idx in range(5):
        (projects / f"relaymem_{idx}.md").write_text(
            f"# RelayMEM {idx}\nRelayMEM retrieval selection dry-run page.\n",
            encoding="utf-8",
        )
    (concepts / "context.md").write_text("# Context\nRelayCTX notes.\n", encoding="utf-8")
    (summaries / "overview.md").write_text("# Summary\nRelayMEM overview.\n", encoding="utf-8")
    (projects / "broken.md").write_bytes(b"\xff\xfe\x00")


def _build_large_store(root: Path) -> None:
    projects = root / "memory" / "mem" / "projects"
    projects.mkdir(parents=True)
    (root / "memory" / "mem" / "index.md").write_text("# Index\nRelayMEM\n", encoding="utf-8")
    (root / "memory" / "mem" / "log.md").write_text("# Log\n", encoding="utf-8")
    for idx in range(150):
        (projects / f"relaymem_large_{idx:03d}.md").write_text(
            f"# RelayMEM Large {idx}\n" + ("x" * 2048),
            encoding="utf-8",
        )


def main() -> int:
    with tempfile.TemporaryDirectory() as store_td:
        store_root = Path(store_td)
        _build_store(store_root)
        direct = discover_relaymem_page_candidates(
            root_path=str(store_root),
            query_terms=["relaymem"],
            max_candidates=2,
            max_read_bytes=24,
        )
        require(len(direct["candidates"]) == 2, direct)
        require(all(item["estimated_chars"] <= 24 for item in direct["candidates"]), direct)
        require(direct["full_candidate_tree_materialized"] is False, direct)
        print("ok direct discovery respects max candidate and read limits")

        with tempfile.TemporaryDirectory() as large_td:
            large_root = Path(large_td)
            _build_large_store(large_root)
            capped = discover_relaymem_page_candidates(
                root_path=str(large_root),
                query_terms=["relaymem"],
                max_candidates=4,
                max_read_bytes=32,
                max_scan=8,
            )
            require(len(capped["candidates"]) == 4, capped)
            require(capped["candidate_scan_seen"] <= 8, capped)
            require(capped["candidate_scan_truncated"] is True, capped)
            require(capped["full_candidate_tree_materialized"] is False, capped)
            require(capped["fallback_reason"] == "memory_store_candidate_scan_truncated", capped)
            print("ok candidate discovery streams directory scan and caps work")

        capture = _Capture()
        _BackendHandler.capture = capture
        server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
        port = int(server.server_address[1])
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as td:
                trace_path = Path(td) / "trace.jsonl"
                cfg_path = Path(td) / "disabled.yaml"
                _write_config(
                    cfg_path,
                    port=port,
                    trace_path=trace_path,
                    store_root=store_root,
                    store_enabled=False,
                )
                app = create_app(str(cfg_path))
                with TestClient(app) as client:
                    artifact = _post_and_get_artifact(
                        client,
                        trace_path,
                        _scene_payload("design_talk", "RelayMEM retrieval"),
                    )
                    require(artifact["selected_mem_candidates"] == [], artifact)
                    require(artifact["selected"] == [], artifact)
                    print("ok disabled store has no selected mem candidates")

            with tempfile.TemporaryDirectory() as td:
                trace_path = Path(td) / "trace.jsonl"
                cfg_path = Path(td) / "enabled.yaml"
                _write_config(
                    cfg_path,
                    port=port,
                    trace_path=trace_path,
                    store_root=store_root,
                    store_enabled=True,
                    candidate_limit=2,
                )
                app = create_app(str(cfg_path))
                with TestClient(app) as client:
                    design_payload = _scene_payload("design_talk", "RelayMEM retrieval")
                    design = _post_and_get_artifact(client, trace_path, design_payload)
                    candidates = design["selected_mem_candidates"]
                    require(0 < len(candidates) <= 2, design)
                    require(candidates[0]["source"] == "mem_page", design)
                    require(candidates[0]["applied_to_ctx"] is False, design)
                    require(design["ctx_block"] is None, design)
                    require(design["apply_allowed"] is False, design)
                    blocked_reasons = {item["reason"] for item in design["blocked"]}
                    require("malformed_or_unreadable_file" in blocked_reasons, design)
                    _assert_no_backend_artifact(capture.last())
                    require(
                        capture.last().get("metadata") == design_payload["metadata"],
                        capture.last(),
                    )
                    print("ok design scene emits selection dry-run candidates")

                    recovery = _post_and_get_artifact(
                        client,
                        trace_path,
                        _scene_payload("recovery", "何の話だったっけ"),
                    )
                    require(recovery["retrieval_scope"] == "current_context_only", recovery)
                    require(recovery["selected_mem_candidates"] == [], recovery)
                    print("ok recovery scene suppresses mem candidate selection")

                    for scene_type in ("formal_document", "medical_or_safety"):
                        artifact = _post_and_get_artifact(
                            client,
                            trace_path,
                            _scene_payload(scene_type, "RelayMEM evidence"),
                        )
                        require(artifact["selected_mem_candidates"] == [], artifact)
                    print("ok formal and medical scenes suppress mem candidate selection")

                    latest = _post_and_get_artifact(
                        client,
                        trace_path,
                        _scene_payload("design_talk", "RelayMEM trace check"),
                    )
                    require(isinstance(latest.get("selected_mem_candidates"), list), latest)
                    print("ok trace metadata includes selected_mem_candidates")
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
