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
        "relaymem_primary_recall_projection",
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
        require(store["layout_compatibility"]["current_flat_present"] is True, store)
        require(store["layout_compatibility"]["migration_required"] is True, store)
        blocked_reasons = {item["reason"] for item in store["blocked_files"]}
        require("unsupported_file_type" in blocked_reasons, store)
        require("malformed_or_unreadable_file" in blocked_reasons, store)
        validation = store["validation"]
        require(validation["full_file_reads"] is False, store)
        require(validation["full_tree_materialized"] is False, store)
        require(validation["max_sample_bytes"] == 4096, store)
        print("ok minimal store discovers legacy pages and blocks malformed files")

        legacy_candidates = discover_relaymem_page_candidates(
            root_path=str(store_root),
            query_terms=["relaymem"],
        )
        require(legacy_candidates["candidates"], legacy_candidates)
        first_legacy = legacy_candidates["candidates"][0]
        require(first_legacy["layout_profile"] == "current_flat", legacy_candidates)
        require(first_legacy["memory_layer"] == "legacy_flat", legacy_candidates)
        print("ok legacy flat candidates remain read-only compatible")

        with tempfile.TemporaryDirectory() as partial_td:
            partial_root = Path(partial_td)
            partial_mem = partial_root / "memory" / "mem"
            (partial_mem / "projects").mkdir(parents=True)
            (partial_root / "memory" / "sources" / "conversations").mkdir(parents=True)
            (partial_mem / "index.md").write_text("# Index\n", encoding="utf-8")
            (partial_mem / "log.md").write_text("# Log\n", encoding="utf-8")
            partial = build_relaymem_store_diagnostics(
                root_path=str(partial_root),
                store_enabled=True,
                retrieval_dry_run_only=True,
            )
            require(partial["layout_compatibility"]["current_flat_present"] is True, partial)
            require(
                partial["layout_compatibility"]["target_primary_secondary_present"] is False,
                partial,
            )
            require(partial["layout_compatibility"]["sources_present"] is True, partial)
            require(partial["layout_compatibility"]["migration_required"] is True, partial)
            print("ok sources-only partial migration still requires MEM layout migration")

        with tempfile.TemporaryDirectory() as primary_only_td:
            primary_only_root = Path(primary_only_td)
            primary_only_mem = primary_only_root / "memory" / "mem"
            (primary_only_mem / "projects").mkdir(parents=True)
            (primary_only_mem / "primary" / "sessions").mkdir(parents=True)
            (primary_only_mem / "index.md").write_text("# Index\n", encoding="utf-8")
            (primary_only_mem / "log.md").write_text("# Log\n", encoding="utf-8")
            primary_only = build_relaymem_store_diagnostics(
                root_path=str(primary_only_root),
                store_enabled=True,
                retrieval_dry_run_only=True,
            )
            require(primary_only["layout_compatibility"]["current_flat_present"] is True, primary_only)
            require(
                primary_only["layout_compatibility"]["target_primary_secondary_present"] is False,
                primary_only,
            )
            require(primary_only["layout_compatibility"]["migration_required"] is True, primary_only)
            print("ok primary-only partial migration still requires secondary MEM layout")

        with tempfile.TemporaryDirectory() as symlink_td, tempfile.TemporaryDirectory() as outside_td:
            symlink_root = Path(symlink_td)
            outside_root = Path(outside_td)
            outside_sessions = outside_root / "sessions"
            outside_sessions.mkdir(parents=True)
            (outside_sessions / "outside.md").write_text("# Outside\nleak\n", encoding="utf-8")
            symlink_mem = symlink_root / "memory" / "mem"
            (symlink_mem / "primary").mkdir(parents=True)
            (symlink_mem / "secondary").mkdir(parents=True)
            (symlink_mem / "index.md").write_text("# Index\n", encoding="utf-8")
            (symlink_mem / "log.md").write_text("# Log\n", encoding="utf-8")
            link_path = symlink_mem / "primary" / "sessions"
            try:
                link_path.symlink_to(outside_sessions, target_is_directory=True)
            except (OSError, NotImplementedError):
                print("ok symlink candidate directory smoke skipped on unsupported platform")
            else:
                symlink_candidates = discover_relaymem_page_candidates(
                    root_path=str(symlink_root),
                    query_terms=["outside"],
                )
                require(symlink_candidates["candidates"] == [], symlink_candidates)
                require(
                    symlink_candidates["fallback_reason"]
                    == "memory_store_no_candidate_pages",
                    symlink_candidates,
                )
                print("ok symlinked target MEM candidate directory is not scanned")

        with tempfile.TemporaryDirectory() as target_td:
            target_root = Path(target_td)
            target_mem = target_root / "memory" / "mem"
            (target_root / "memory" / "sources" / "conversations").mkdir(parents=True)
            (target_mem / "primary" / "sessions").mkdir(parents=True)
            (target_mem / "secondary" / "projects").mkdir(parents=True)
            (target_mem / "secondary" / "relations").mkdir(parents=True)
            (target_mem / "index.md").write_text("# Index\n", encoding="utf-8")
            (target_mem / "log.md").write_text("# Log\n", encoding="utf-8")
            (target_root / "memory" / "sources" / "conversations" / "turn.jsonl").write_text(
                "{}\n",
                encoding="utf-8",
            )
            (target_mem / "primary" / "sessions" / "session.md").write_text(
                "# Session\nTarget primary memory\n",
                encoding="utf-8",
            )
            (target_mem / "secondary" / "projects" / "project.md").write_text(
                "# Project\nTarget secondary memory\n",
                encoding="utf-8",
            )
            (target_mem / "secondary" / "relations" / "relation.md").write_text(
                "# Relation\nTarget relation memory\n",
                encoding="utf-8",
            )
            target = build_relaymem_store_diagnostics(
                root_path=str(target_root),
                store_enabled=True,
                retrieval_dry_run_only=True,
            )
            require(target["layout_compatibility"]["current_flat_present"] is False, target)
            require(target["layout_compatibility"]["target_primary_secondary_present"] is True, target)
            require(target["layout_compatibility"]["sources_present"] is True, target)
            require(target["layout_compatibility"]["migration_required"] is False, target)
            require(target["blocked_files"] == [], target)
            require(
                "memory/mem/primary/sessions/session.md" in target["page_paths"],
                target,
            )
            require(
                "memory/mem/secondary/projects/project.md" in target["page_paths"],
                target,
            )

            target_candidates = discover_relaymem_page_candidates(
                root_path=str(target_root),
                query_terms=["target"],
                max_candidates=8,
            )
            target_paths = {item["path"] for item in target_candidates["candidates"]}
            require("memory/mem/primary/sessions/session.md" in target_paths, target_candidates)
            require("memory/mem/secondary/projects/project.md" in target_paths, target_candidates)
            require("memory/mem/secondary/relations/relation.md" in target_paths, target_candidates)
            target_layers = {item["memory_layer"] for item in target_candidates["candidates"]}
            require({"primary", "secondary"}.issubset(target_layers), target_candidates)

            snippets = build_relaymem_snippet_evidence_dry_run(
                root_path=str(target_root),
                selected_mem_candidates=target_candidates["candidates"],
                snippet_extraction_enabled=True,
                snippet_dry_run_only=True,
            )
            require(snippets["snippet_candidates"], snippets)
            snippet_layers = {item["memory_layer"] for item in snippets["snippet_candidates"]}
            require(snippet_layers.issubset({"primary", "secondary"}), snippets)
            require(snippets["evidence_envelope"]["blocked"] == [], snippets)
            print("ok target primary/secondary layout is read-only discoverable")

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
                    metadata = _last_backend_response_metadata(trace_path)
                    projection = _content_free_projection(metadata)
                    require(projection["selected_count"] == 0, projection)
                    require(
                        projection["fallback_reason"] == "memory_store_disabled",
                        projection,
                    )
                    require(projection["injection_performed"] is False, projection)
                    print("ok runtime emits content-free disabled-store projection")

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
                    metadata = _last_backend_response_metadata(trace_path)
                    projection = _content_free_projection(metadata)
                    require(projection["selected_count"] == 0, projection)
                    require(projection["memory_used"] is False, projection)
                    require(projection["injection_performed"] is False, projection)
                    backend_payload = capture.last_chat_payload()
                    _assert_no_backend_artifact(backend_payload)
                    require(
                        backend_payload.get("metadata") == payload["metadata"],
                        "backend metadata changed",
                    )
                    print("ok runtime store status is content-free and non-mutating")
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
