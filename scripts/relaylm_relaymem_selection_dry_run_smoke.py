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
from relaylm.relaymem_retrieval import build_relaymem_retrieval_dry_run_artifact
from relaylm.relaymem_store import build_relaymem_store_diagnostics, discover_relaymem_page_candidates


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
                "id": "chatcmpl-relaymem-selection-smoke",
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
            "scene_state": {"scene_type": scene_type, "confidence": 0.95, "stability": 0.9}
        },
        "stream": False,
    }


def _scene_artifact(scene_type: str = "design_talk") -> dict[str, Any]:
    return {
        "scene_state": {"scene_type": scene_type, "confidence": 0.95, "stability": 0.9},
        "scene_policy": {"relaymem_retrieval_scope": "project_context"},
        "persistence_block": False,
        "persistence_block_reasons": [],
    }


def _last_backend_response_metadata(trace_path: Path) -> dict[str, Any]:
    lines = trace_path.read_text(encoding="utf-8").strip().splitlines()
    require(bool(lines), "trace is empty")
    for line in reversed(lines):
        record = json.loads(line)
        metadata = record.get("metadata") if isinstance(record, dict) else None
        if isinstance(metadata, dict) and metadata.get("event") == "backend_response":
            return metadata
    raise AssertionError("backend_response trace record is missing")


def _post_and_get_projection(
    client: TestClient,
    trace_path: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    resp = client.post("/v1/chat/completions", json=payload)
    require(resp.status_code == 200, resp.text)
    metadata = _last_backend_response_metadata(trace_path)
    require("relaymem_retrieval_artifact" not in metadata, "full retrieval artifact leaked")
    projection = metadata.get("relaymem_primary_recall_projection")
    require(isinstance(projection, dict), metadata)
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
        "relaymem_primary_recall_projection",
        "selected_mem_candidates",
        "ctx_block",
        "store_diagnostics",
    }
    require(forbidden.isdisjoint(payload), payload)


def _build_store(root: Path, *, count: int = 5) -> None:
    mem = root / "memory" / "mem"
    (root / "memory" / "sources" / "conversations").mkdir(parents=True)
    (mem / "primary" / "sessions").mkdir(parents=True)
    (mem / "secondary" / "projects").mkdir(parents=True)
    (mem / "secondary" / "concepts").mkdir(parents=True)
    (mem / "secondary" / "summaries").mkdir(parents=True)
    (mem / "index.md").write_text("# Index\nRelayMEM\n", encoding="utf-8")
    (mem / "log.md").write_text("# Log\n", encoding="utf-8")
    for idx in range(count):
        (mem / "secondary" / "projects" / f"relaymem_{idx}.md").write_text(
            f"# RelayMEM {idx}\nRelayMEM retrieval selection dry-run page.\n",
            encoding="utf-8",
        )
    (mem / "secondary" / "concepts" / "context.md").write_text("# Context\nRelayCTX notes.\n", encoding="utf-8")
    (mem / "secondary" / "summaries" / "overview.md").write_text("# Summary\nRelayMEM overview.\n", encoding="utf-8")
    (mem / "primary" / "sessions" / "session.md").write_text("# Session\nRelayMEM session note.\n", encoding="utf-8")


def main() -> int:
    with tempfile.TemporaryDirectory() as store_td:
        store_root = Path(store_td)
        _build_store(store_root)
        direct = discover_relaymem_page_candidates(
            root_path=str(store_root), query_terms=["relaymem"], max_candidates=2, max_read_bytes=24
        )
        require(len(direct["candidates"]) == 2, direct)
        require(all(item["estimated_chars"] <= 24 for item in direct["candidates"]), direct)
        require(direct["full_candidate_tree_materialized"] is False, direct)
        require({item["layout_profile"] for item in direct["candidates"]} == {"target_primary_secondary"}, direct)
        print("ok direct target discovery respects max candidate and read limits")

        with tempfile.TemporaryDirectory() as cap_td:
            cap_root = Path(cap_td)
            _build_store(cap_root, count=3)
            (cap_root / "memory" / "mem" / "secondary" / "projects" / "broken.md").write_bytes(b"\xff\xfe\x00")
            cap = discover_relaymem_page_candidates(
                root_path=str(cap_root), query_terms=["relaymem"], max_candidates=2, max_read_bytes=32, max_scan=10
            )
            cap_blocked = {item["path"]: item["reason"] for item in cap["blocked_files"]}
            require(len(cap["candidates"]) == 2, cap)
            require(cap["candidate_cap_reached"] is True, cap)
            require(
                cap_blocked.get("memory/mem/secondary/projects/broken.md") == "malformed_or_unreadable_file",
                cap,
            )
            print("ok candidate scan continues after candidate cap to report blocked files")

        with tempfile.TemporaryDirectory() as utf8_td:
            utf8_root = Path(utf8_td)
            _build_store(utf8_root, count=0)
            utf8_projects = utf8_root / "memory" / "mem" / "secondary" / "projects"
            (utf8_projects / "jp.md").write_text("ああ", encoding="utf-8")
            utf8 = discover_relaymem_page_candidates(
                root_path=str(utf8_root), query_terms=[], max_candidates=1, max_read_bytes=1
            )
            require(len(utf8["candidates"]) == 1, utf8)
            require(utf8["blocked_files"] == [], utf8)
            print("ok truncated UTF-8 sample does not false-block valid page")

            (utf8_projects / "incomplete.md").write_bytes(b"abc\xe3")
            incomplete = discover_relaymem_page_candidates(
                root_path=str(utf8_root), query_terms=[], max_candidates=4, max_read_bytes=16
            )
            blocked = {item["path"]: item["reason"] for item in incomplete["blocked_files"]}
            require(blocked.get("memory/mem/secondary/projects/incomplete.md") == "malformed_or_unreadable_file", incomplete)
            print("ok incomplete UTF-8 at EOF is blocked")

        with tempfile.TemporaryDirectory() as large_td:
            large_root = Path(large_td)
            _build_store(large_root, count=150)
            capped = discover_relaymem_page_candidates(
                root_path=str(large_root), query_terms=["relaymem"], max_candidates=4, max_read_bytes=32, max_scan=8
            )
            require(len(capped["candidates"]) == 4, capped)
            require(capped["candidate_scan_seen"] <= 8, capped)
            require(capped["candidate_scan_truncated"] is True, capped)
            require(capped["full_candidate_tree_materialized"] is False, capped)
            require(capped["fallback_reason"] == "memory_store_candidate_scan_truncated", capped)
            print("ok candidate discovery streams directory scan and caps work")

            truncated_store = build_relaymem_store_diagnostics(
                root_path=str(large_root), store_enabled=True, retrieval_dry_run_only=True
            )
            require(truncated_store["fallback_reason"] in {"memory_store_scan_truncated", "memory_store_validation_truncated"}, truncated_store)
            retrieval = build_relaymem_retrieval_dry_run_artifact(
                relayscn_scene_policy_artifact=_scene_artifact(),
                messages=[{"role": "user", "content": "RelayMEM Large"}],
                store_diagnostics=truncated_store,
                max_candidates=3,
            )
            require(0 < len(retrieval["selected_mem_candidates"]) <= 3, retrieval)
            require(retrieval["ctx_block"] is None, retrieval)
            require(retrieval["apply_allowed"] is False, retrieval)
            print("ok truncated store diagnostics still allow bounded selection dry-run")

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
                    cfg_path, port=port, trace_path=trace_path, store_root=store_root, store_enabled=False
                )
                app = create_app(str(cfg_path))
                with TestClient(app) as client:
                    projection = _post_and_get_projection(
                        client, trace_path, _scene_payload("design_talk", "RelayMEM retrieval")
                    )
                    require(projection["selected_count"] == 0, projection)
                    require(projection["fallback_reason"] == "memory_store_disabled", projection)
                    require(projection["injection_performed"] is False, projection)
                    print("ok disabled store emits a content-free zero-selection projection")

            with tempfile.TemporaryDirectory() as td:
                configured_root = Path(td) / "memory-root"
                scoped = resolve_relaymem_character_store_root(str(configured_root), "default")
                require(isinstance(scoped, str), scoped)
                _build_store(Path(scoped))
                trace_path = Path(td) / "trace.jsonl"
                cfg_path = Path(td) / "enabled.yaml"
                _write_config(
                    cfg_path,
                    port=port,
                    trace_path=trace_path,
                    store_root=configured_root,
                    store_enabled=True,
                    candidate_limit=2,
                )
                app = create_app(str(cfg_path))
                with TestClient(app) as client:
                    design_payload = _scene_payload("design_talk", "RelayMEM retrieval")
                    design = _post_and_get_projection(client, trace_path, design_payload)
                    require(design["selected_count"] == 0, design)
                    require(design["character_scope_resolved"] is True, design)
                    require(design["scope_matched"] is False, design)
                    require("legacy_flat_store_compatibility" not in design["blocked_reason_ids"], design)
                    backend_payload = capture.last_chat_payload()
                    _assert_no_backend_artifact(backend_payload)
                    require(backend_payload.get("metadata") == design_payload["metadata"], "backend metadata changed")
                    print("ok target runtime selection remains content-free and non-mutating")

                    recovery = _post_and_get_projection(
                        client, trace_path, _scene_payload("recovery", "何の話だったっけ")
                    )
                    require(recovery["retrieval_scope"] == "current_context_only", recovery)
                    require(recovery["selected_count"] == 0, recovery)
                    print("ok recovery scene suppresses runtime selection")

                    for scene_type in ("formal_document", "medical_or_safety"):
                        projection = _post_and_get_projection(
                            client, trace_path, _scene_payload(scene_type, "RelayMEM evidence")
                        )
                        require(projection["selected_count"] == 0, projection)
                        require(projection["persistence_block"] is True, projection)
                    print("ok formal and medical scenes suppress runtime selection")

                    latest = _post_and_get_projection(
                        client, trace_path, _scene_payload("design_talk", "RelayMEM trace check")
                    )
                    require(latest["content_free"] is True, latest)
                    require(latest["selected_layer_counts"] == {"primary": 0}, latest)
                    print("ok trace metadata exposes only the content-free selection projection")
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
