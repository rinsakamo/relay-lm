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
from relaylm.relaymem_retrieval import (
    _attach_evidence_metadata_to_ctx_block_candidate,
    build_relaymem_retrieval_dry_run_artifact,
)
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
        raw = self.rfile.read(int(self.headers.get("content-length", "0")))
        payload = json.loads(raw.decode("utf-8")) if raw else {}
        type(self).capture.add(payload)
        body = json.dumps(
            {
                "id": "chatcmpl-relaymem-ctx-evidence-smoke",
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


def _build_store(root: Path) -> None:
    projects = root / "memory" / "mem" / "projects"
    projects.mkdir(parents=True)
    (root / "memory" / "mem" / "index.md").write_text("# Index\nRelayMEM\n", encoding="utf-8")
    (root / "memory" / "mem" / "log.md").write_text("# Log\n", encoding="utf-8")
    (projects / "relaymem.md").write_text(
        "# RelayMEM\nCTX_EVIDENCE_SENTINEL should never reach backend prompts.\n",
        encoding="utf-8",
    )


def _scene_artifact(scene_type: str = "design_talk", scope: str = "project_context") -> dict[str, Any]:
    return {
        "scene_state": {"scene_type": scene_type, "confidence": 0.95, "stability": 0.9},
        "scene_policy": {"relaymem_retrieval_scope": scope},
        "persistence_block": scene_type in {"recovery", "formal_document", "medical_or_safety"},
        "persistence_block_reasons": [],
    }


def _artifact_for(
    root: Path,
    *,
    snippet_enabled: bool,
    scene_type: str = "design_talk",
    scope: str = "project_context",
    relayref_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    store = build_relaymem_store_diagnostics(
        root_path=str(root),
        store_enabled=True,
        retrieval_dry_run_only=False,
    )
    return build_relaymem_retrieval_dry_run_artifact(
        relayscn_scene_policy_artifact=_scene_artifact(scene_type, scope),
        relayref_artifact=relayref_artifact,
        messages=[{"role": "user", "content": "RelayMEM CTX evidence metadata"}],
        token_budget=800,
        store_diagnostics=store,
        max_candidates=3,
        ctx_block_apply_enabled=True,
        snippet_extraction_enabled=snippet_enabled,
        snippet_dry_run_only=True,
        max_snippet_chars=80,
        max_snippet_candidates=3,
    )


def _assert_enabled_metadata(root: Path) -> None:
    artifact = _artifact_for(root, snippet_enabled=True)
    require(artifact["ctx_block"] is None, artifact)
    require(artifact["apply_allowed"] is False, artifact)
    entries = artifact["ctx_block_candidate"]["entries"]
    require(entries, artifact)
    entry = entries[0]
    require(entry["snippet_available"] is True, entry)
    require(entry["evidence_kind"] == "bounded_page_snippet", entry)
    require(entry["snippet_chars"] > 0, entry)
    require(entry["snippet_estimated_tokens"] > 0, entry)
    require(entry["snippet_included_in_runtime_prompt"] is False, entry)
    require(isinstance(entry["evidence_id"], str), entry)
    require("snippet_text" not in entry, entry)
    envelope_snippets = artifact["evidence_envelope"]["snippets"]
    require(envelope_snippets, artifact)
    require(envelope_snippets[0]["evidence_id"] == entry["evidence_id"], artifact)
    require(envelope_snippets[0]["content_included_in_runtime_prompt"] is False, artifact)
    print("ok ctx_block_candidate entries link to evidence envelope metadata")


def _assert_disabled_metadata(root: Path) -> None:
    artifact = _artifact_for(root, snippet_enabled=False)
    entries = artifact["ctx_block_candidate"]["entries"]
    require(entries, artifact)
    entry = entries[0]
    require(entry["snippet_available"] is False, entry)
    require(entry["evidence_kind"] == "none", entry)
    require(entry["snippet_chars"] == 0, entry)
    require(entry["snippet_estimated_tokens"] == 0, entry)
    require(entry["snippet_included_in_runtime_prompt"] is False, entry)
    require(entry["evidence_id"] is None, entry)
    print("ok snippet disabled marks ctx_block evidence metadata unavailable")


def _assert_blocked_metadata() -> None:
    candidate = {
        "schema_version": "relaymem.ctx_block_candidate.v0",
        "diagnostics_only": True,
        "applied_to_ctx": False,
        "entries": [
            {
                "path": "memory/mem/projects/malformed.md",
                "source": "mem_page",
                "reason": "keyword_match",
                "estimated_tokens": 4,
                "included": True,
                "truncated": False,
                "applied_to_ctx": False,
            }
        ],
        "blocked": [],
    }
    envelope = {
        "schema_version": "relaymem.evidence_envelope.v0",
        "diagnostics_only": True,
        "applied_to_ctx": False,
        "source": "selected_mem_candidates",
        "snippets": [],
        "blocked": [
            {
                "evidence_id": "evidence:0",
                "selected_index": 0,
                "path": "memory/mem/projects/malformed.md",
                "reason": "malformed_utf8",
            }
        ],
    }
    attached = _attach_evidence_metadata_to_ctx_block_candidate(
        ctx_block_candidate=candidate,
        evidence_envelope=envelope,
    )
    entry = attached["entries"][0]
    require(entry["snippet_available"] is False, entry)
    require(entry["evidence_id"] == "evidence:0", entry)
    require(entry["evidence_blocked_reason"] == "malformed_utf8", entry)
    require(entry["snippet_included_in_runtime_prompt"] is False, entry)
    print("ok blocked snippet evidence is referenced without snippet_text")


def _assert_scene_safety(root: Path) -> None:
    for scene_type in ("recovery", "formal_document", "medical_or_safety"):
        artifact = _artifact_for(root, snippet_enabled=True, scene_type=scene_type)
        require(artifact["ctx_block_candidate"]["entries"] == [], (scene_type, artifact))
    unresolved = _artifact_for(
        root,
        snippet_enabled=True,
        relayref_artifact={"unresolved_reference_detected": True},
    )
    require(unresolved["ctx_block_candidate"]["entries"] == [], unresolved)
    print("ok blocked scenes and unresolved references have no snippet metadata entries")


def _write_config(path: Path, *, port: int, trace_path: Path, store_root: Path) -> None:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    cfg["backends"]["local_backend"]["base_url"] = f"http://127.0.0.1:{port}/v1"
    cfg["trace"] = {"enabled": True, "path": str(trace_path)}
    cfg["model_routes"]["relaylm-default"]["mode"] = "pass_through"
    cfg["memory"].update(
        {
            "root_path": str(store_root),
            "store_enabled": True,
            "retrieval_dry_run_only": False,
            "ctx_block_apply_enabled": True,
            "snippet_extraction_enabled": True,
            "snippet_dry_run_only": True,
            "max_snippet_chars": 80,
            "max_snippet_candidates": 3,
            "candidate_limit": 3,
            "token_budget_hint": 800,
        }
    )
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")


def _assert_runtime_prompt_and_trace(root: Path, capture: _Capture, port: int) -> None:
    with tempfile.TemporaryDirectory() as td:
        trace_path = Path(td) / "trace.jsonl"
        cfg_path = Path(td) / "cfg.yaml"
        _write_config(cfg_path, port=port, trace_path=trace_path, store_root=root)
        app = create_app(str(cfg_path))
        payload = {
            "model": "relaylm-default",
            "messages": [{"role": "user", "content": "RelayMEM CTX evidence metadata"}],
            "metadata": {"scene_state": {"scene_type": "design_talk"}},
            "stream": False,
        }
        original = json.loads(json.dumps(payload))
        with TestClient(app) as client:
            resp = client.post("/v1/chat/completions", json=payload)
            require(resp.status_code == 200, resp.text)
        require(payload == original, payload)
        backend_text = json.dumps(capture.last(), ensure_ascii=False)
        require("[RelayMEM Context]" in backend_text, capture.last())
        require("CTX_EVIDENCE_SENTINEL" not in backend_text, capture.last())
        require("snippet_text" not in backend_text, capture.last())
        record = json.loads(trace_path.read_text(encoding="utf-8").strip().splitlines()[-1])
        metadata = record.get("metadata", {})
        envelope = metadata.get("evidence_envelope")
        require(isinstance(envelope, dict) and envelope.get("snippets"), metadata)
        artifact = metadata.get("relaymem_retrieval_artifact")
        require(isinstance(artifact, dict), metadata)
        entry = artifact["ctx_block_candidate"]["entries"][0]
        require(entry["snippet_available"] is True, entry)
        require("snippet_text" not in entry, entry)
        require(artifact["ctx_block"] is None, artifact)
        require(artifact["apply_allowed"] is False, artifact)
    print("ok runtime prompt stays metadata-only and trace carries evidence envelope")


def main() -> int:
    capture = _Capture()
    _BackendHandler.capture = capture
    server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
    port = int(server.server_address[1])
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _build_store(root)
            _assert_enabled_metadata(root)
            _assert_disabled_metadata(root)
            _assert_blocked_metadata()
            _assert_scene_safety(root)
            _assert_runtime_prompt_and_trace(root, capture, port)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
