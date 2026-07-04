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
from relaylm.relaymem_primary_recall import resolve_relaymem_character_store_root
from relaylm.relaymem_store import (
    build_relaymem_snippet_evidence_dry_run,
    build_relaymem_store_diagnostics,
    discover_relaymem_page_candidates,
)


class _Capture:
    def __init__(self) -> None:
        self.payloads: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def add(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self.payloads.append(payload)

    def last_chat_payload(self) -> dict[str, Any]:
        with self._lock:
            for payload in reversed(self.payloads):
                if isinstance(payload.get("messages"), list):
                    return payload
        raise AssertionError("no backend chat payload captured")


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
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}}],
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
            "scene_state": {"scene_type": "design_talk", "confidence": 0.95, "stability": 0.9}
        },
        "stream": False,
    }
    resp = client.post("/v1/chat/completions", json=payload)
    require(resp.status_code == 200, resp.text)
    return payload


def _last_backend_response_metadata(trace_path: Path) -> dict[str, Any]:
    lines = trace_path.read_text(encoding="utf-8").strip().splitlines()
    require(bool(lines), "trace is empty")
    for line in reversed(lines):
        record = json.loads(line)
        metadata = record.get("metadata") if isinstance(record, dict) else None
        if isinstance(metadata, dict) and metadata.get("event") == "backend_response":
            return metadata
    raise AssertionError("backend_response trace record is missing")


def _content_free_projection(metadata: dict[str, Any]) -> dict[str, Any]:
    require("relaymem_retrieval_artifact" not in metadata, "full retrieval artifact leaked")
    projection = metadata.get("relaymem_primary_recall_projection")
    require(isinstance(projection, dict), "primary recall projection missing")
    require(projection.get("content_free") is True, projection)
    require(projection.get("content_included") is False, projection)
    require(projection.get("memory_text_included") is False, projection)
    require(projection.get("path_values_included") is False, projection)
    require(projection.get("digest_values_included") is False, projection)
    require(projection.get("lineage_values_included") is False, projection)
    require(projection.get("idempotency_values_included") is False, projection)
    return projection


def _assert_no_backend_artifact(payload: dict[str, Any]) -> None:
    forbidden = {
        "relaymem_retrieval_artifact",
        "relaymem_store_diagnostics",
        "relaymem_primary_recall_projection",
        "store_diagnostics",
        "ctx_block",
    }
    require(forbidden.isdisjoint(payload), payload)


def _write_target_store(root: Path, *, pages: int = 3) -> None:
    mem = root / "memory" / "mem"
    (root / "memory" / "sources" / "conversations").mkdir(parents=True)
    (mem / "primary" / "sessions").mkdir(parents=True)
    (mem / "secondary" / "projects").mkdir(parents=True)
    (mem / "secondary" / "relations").mkdir(parents=True)
    (mem / "index.md").write_text("# Index\n", encoding="utf-8")
    (mem / "log.md").write_text("# Log\n", encoding="utf-8")
    for idx in range(pages):
        (mem / "secondary" / "projects" / f"project_{idx}.md").write_text(
            f"# Project {idx}\nRelayMEM target secondary memory\n", encoding="utf-8"
        )
    (mem / "primary" / "sessions" / "session.md").write_text(
        "# Session\nRelayMEM target primary memory\n", encoding="utf-8"
    )
    (mem / "secondary" / "relations" / "relation.md").write_text(
        "# Relation\nRelayMEM target relation memory\n", encoding="utf-8"
    )


def main() -> int:
    disabled = build_relaymem_store_diagnostics(
        root_path="memory_store", store_enabled=False, retrieval_dry_run_only=True
    )
    require(disabled["fallback_reason"] == "memory_store_disabled", disabled)
    print("ok disabled store emits fail-soft diagnostics")

    missing = build_relaymem_store_diagnostics(
        root_path="/tmp/relaylm-missing-memory-store-for-smoke",
        store_enabled=True,
        retrieval_dry_run_only=True,
    )
    require(missing["fallback_reason"] == "memory_store_root_missing", missing)
    print("ok missing root emits fail-soft diagnostics")

    with tempfile.TemporaryDirectory() as legacy_td:
        legacy_root = Path(legacy_td)
        legacy_mem = legacy_root / "memory" / "mem"
        (legacy_mem / "projects").mkdir(parents=True)
        (legacy_mem / "index.md").write_text("# Index\n", encoding="utf-8")
        (legacy_mem / "log.md").write_text("# Log\n", encoding="utf-8")
        (legacy_mem / "projects" / "relaymem.md").write_text("# RelayMEM\n", encoding="utf-8")
        store = build_relaymem_store_diagnostics(
            root_path=str(legacy_root), store_enabled=True, retrieval_dry_run_only=True
        )
        require(store["layout_compatibility"]["flat_store_compatibility_removed"] is True, store)
        require("current_flat_present" not in store["layout_compatibility"], store)
        require("migration_required" not in store["layout_compatibility"], store)
        require(store["pages_discovered"] == 0, store)
        require(store["fallback_reason"] == "target_primary_secondary_layout_missing", store)
        candidates = discover_relaymem_page_candidates(root_path=str(legacy_root), query_terms=["relaymem"])
        require(candidates["candidates"] == [], candidates)
        require(candidates["fallback_reason"] == "target_primary_secondary_layout_missing", candidates)
        snippets = build_relaymem_snippet_evidence_dry_run(
            root_path=str(legacy_root),
            selected_mem_candidates=[{"path": "memory/mem/projects/relaymem.md", "source": "mem_page"}],
            snippet_extraction_enabled=True,
            snippet_dry_run_only=True,
        )
        require(snippets["evidence_envelope"]["blocked"][0]["reason"] == "unsupported_scope", snippets)
        print("ok legacy flat store is not runtime-readable")

    with tempfile.TemporaryDirectory() as target_td:
        target_root = Path(target_td)
        _write_target_store(target_root)
        target = build_relaymem_store_diagnostics(
            root_path=str(target_root), store_enabled=True, retrieval_dry_run_only=True
        )
        require(target["layout_compatibility"]["target_primary_secondary_present"] is True, target)
        require(target["layout_compatibility"]["sources_present"] is True, target)
        require(target["layout_compatibility"]["flat_store_compatibility_removed"] is True, target)
        require(target["blocked_files"] == [], target)
        require("memory/mem/primary/sessions/session.md" in target["page_paths"], target)
        require("memory/mem/secondary/projects/project_0.md" in target["page_paths"], target)
        target_candidates = discover_relaymem_page_candidates(
            root_path=str(target_root), query_terms=["target"], max_candidates=8
        )
        require(target_candidates["candidates"], target_candidates)
        require({item["layout_profile"] for item in target_candidates["candidates"]} == {"target_primary_secondary"}, target_candidates)
        require({item["memory_layer"] for item in target_candidates["candidates"]}.issubset({"primary", "secondary"}), target_candidates)
        snippets = build_relaymem_snippet_evidence_dry_run(
            root_path=str(target_root),
            selected_mem_candidates=target_candidates["candidates"],
            snippet_extraction_enabled=True,
            snippet_dry_run_only=True,
        )
        require(snippets["snippet_candidates"], snippets)
        require(snippets["evidence_envelope"]["blocked"] == [], snippets)
        print("ok target primary/secondary layout is read-only discoverable")

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
                memory={"store_enabled": False, "root_path": str(Path(disabled_td) / "memory-root")},
            )
            app = create_app(str(cfg_path))
            with TestClient(app) as client:
                _post_design(client)
                metadata = _last_backend_response_metadata(trace_path)
                projection = _content_free_projection(metadata)
                require(projection["selected_count"] == 0, projection)
                require(projection["fallback_reason"] == "memory_store_disabled", projection)
                require(projection["injection_performed"] is False, projection)
                print("ok runtime emits content-free disabled-store projection")

        with tempfile.TemporaryDirectory() as app_td:
            configured_root = Path(app_td) / "memory-root"
            scoped = resolve_relaymem_character_store_root(str(configured_root), "default")
            require(isinstance(scoped, str), scoped)
            _write_target_store(Path(scoped))
            trace_path = Path(app_td) / "trace.jsonl"
            cfg_path = Path(app_td) / "cfg.yaml"
            _write_config(
                cfg_path,
                port=port,
                trace_path=trace_path,
                memory={
                    "store_enabled": True,
                    "retrieval_dry_run_only": True,
                    "root_path": str(configured_root),
                },
            )
            app = create_app(str(cfg_path))
            with TestClient(app) as client:
                payload = _post_design(client)
                metadata = _last_backend_response_metadata(trace_path)
                projection = _content_free_projection(metadata)
                require(projection["selected_count"] == 0, projection)
                require(projection["character_scope_resolved"] is True, projection)
                require("legacy_flat_store_compatibility" not in projection["blocked_reason_ids"], projection)
                require(projection["memory_used"] is False, projection)
                require(projection["injection_performed"] is False, projection)
                backend_payload = capture.last_chat_payload()
                _assert_no_backend_artifact(backend_payload)
                require(backend_payload.get("metadata") == payload["metadata"], "backend metadata changed")
                print("ok runtime target store status is content-free and non-mutating")
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
