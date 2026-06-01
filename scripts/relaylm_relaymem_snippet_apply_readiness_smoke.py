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
    _build_snippet_apply_readiness,
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
                "id": "chatcmpl-relaymem-snippet-apply-readiness-smoke",
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
        "# RelayMEM\nSNIPPET_APPLY_SENTINEL must remain diagnostics-only.\n",
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
    scene_type: str = "design_talk",
    scope: str = "project_context",
    relayref_artifact: dict[str, Any] | None = None,
    snippet_extraction_enabled: bool = True,
    snippet_dry_run_only: bool = True,
    snippet_apply_enabled: bool = False,
    snippet_budget: int = 512,
    token_budget: int | None = 800,
) -> dict[str, Any]:
    store = build_relaymem_store_diagnostics(
        root_path=str(root),
        store_enabled=True,
        retrieval_dry_run_only=False,
    )
    return build_relaymem_retrieval_dry_run_artifact(
        relayscn_scene_policy_artifact=_scene_artifact(scene_type, scope),
        relayref_artifact=relayref_artifact,
        messages=[{"role": "user", "content": "RelayMEM snippet apply readiness"}],
        token_budget=token_budget,
        store_diagnostics=store,
        max_candidates=3,
        ctx_block_apply_enabled=True,
        snippet_extraction_enabled=snippet_extraction_enabled,
        snippet_dry_run_only=snippet_dry_run_only,
        snippet_apply_enabled=snippet_apply_enabled,
        snippet_budget=snippet_budget,
        max_snippet_chars=120,
        max_snippet_candidates=3,
    )


def _assert_default_valid_snippet(root: Path) -> None:
    artifact = _artifact_for(root)
    require(artifact["snippet_apply_decision"] == "dry_run_only", artifact)
    preconditions = artifact["snippet_apply_preconditions"]
    require(preconditions["included_snippet_entries_present"] is True, preconditions)
    require(preconditions["snippet_dry_run_only"] is True, preconditions)
    require(preconditions["snippet_apply_enabled"] is False, preconditions)
    entry = artifact["ctx_block_candidate"]["entries"][0]
    require(entry["snippet_included_in_runtime_prompt"] is False, entry)
    require("snippet_text" not in entry, entry)
    require(artifact["ctx_block"] is None, artifact)
    require(artifact["apply_allowed"] is False, artifact)
    print("ok valid snippet stays dry_run_only with snippet preconditions")


def _assert_eligible_not_applied(root: Path) -> None:
    artifact = _artifact_for(
        root,
        snippet_dry_run_only=False,
        snippet_apply_enabled=True,
    )
    require(artifact["snippet_apply_decision"] == "eligible_but_not_applied", artifact)
    require("runtime_snippet_injection_not_implemented" in artifact["snippet_apply_blocked_reasons"], artifact)
    require(artifact["ctx_block"] is None, artifact)
    require(artifact["apply_allowed"] is False, artifact)
    print("ok snippet apply gates can become eligible_but_not_applied without prompt apply")


def _assert_snippet_disabled(root: Path) -> None:
    artifact = _artifact_for(root, snippet_extraction_enabled=False)
    require(artifact["snippet_apply_decision"] == "blocked_no_snippet", artifact)
    require(artifact["snippet_apply_preconditions"]["snippet_candidates_present"] is False, artifact)
    require(artifact["ctx_block_candidate"]["entries"][0]["snippet_available"] is False, artifact)
    print("ok snippet disabled blocks snippet apply readiness as no snippet")


def _assert_blocked_evidence() -> None:
    readiness = _build_snippet_apply_readiness(
        malformed=False,
        scene_type="design_talk",
        retrieval_scope="project_context",
        relayref_unresolved=False,
        ctx_block_candidate={
            "entries": [
                {
                    "path": "memory/mem/projects/malformed.md",
                    "included": True,
                    "snippet_available": False,
                    "snippet_estimated_tokens": 0,
                }
            ]
        },
        evidence_envelope={
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
        },
        snippet_candidates=[],
        snippet_dry_run_only=False,
        snippet_apply_enabled=True,
        snippet_budget=512,
    )
    require(readiness["snippet_apply_decision"] == "blocked_snippet_evidence", readiness)
    require("snippet_evidence_blocked" in readiness["snippet_apply_blocked_reasons"], readiness)
    print("ok blocked evidence produces blocked_snippet_evidence")


def _assert_small_budget(root: Path) -> None:
    artifact = _artifact_for(
        root,
        snippet_dry_run_only=False,
        snippet_apply_enabled=True,
        snippet_budget=1,
    )
    require(artifact["snippet_apply_decision"] == "blocked_snippet_budget", artifact)
    require(
        artifact["snippet_apply_preconditions"]["snippet_budget_allows_candidate"] is False,
        artifact,
    )
    require("snippet_budget_exceeded" in artifact["snippet_apply_blocked_reasons"], artifact)
    print("ok small snippet budget blocks snippet apply readiness")


def _assert_scene_and_ref_blocks(root: Path) -> None:
    for scene_type in ("recovery", "formal_document", "medical_or_safety", "unknown"):
        artifact = _artifact_for(root, scene_type=scene_type)
        require(
            artifact["snippet_apply_decision"] == "blocked_scene_policy",
            (scene_type, artifact),
        )
    current_context = _artifact_for(root, scope="current_context_only")
    require(current_context["snippet_apply_decision"] == "blocked_scene_policy", current_context)
    unresolved = _artifact_for(
        root,
        relayref_artifact={"unresolved_reference_detected": True},
    )
    require(unresolved["snippet_apply_decision"] == "blocked_unresolved_reference", unresolved)
    print("ok scene and unresolved reference block snippet apply readiness")


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
            "snippet_dry_run_only": False,
            "snippet_apply_enabled": True,
            "snippet_budget": 512,
            "max_snippet_chars": 120,
            "max_snippet_candidates": 3,
            "candidate_limit": 3,
            "token_budget_hint": 800,
        }
    )
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")


def _assert_runtime_trace_and_prompt(root: Path, capture: _Capture, port: int) -> None:
    with tempfile.TemporaryDirectory() as td:
        trace_path = Path(td) / "trace.jsonl"
        cfg_path = Path(td) / "cfg.yaml"
        _write_config(cfg_path, port=port, trace_path=trace_path, store_root=root)
        app = create_app(str(cfg_path))
        payload = {
            "model": "relaylm-default",
            "messages": [{"role": "user", "content": "RelayMEM snippet apply readiness"}],
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
        require("SNIPPET_APPLY_SENTINEL" not in backend_text, capture.last())
        require("snippet_text" not in backend_text, capture.last())
        record = json.loads(trace_path.read_text(encoding="utf-8").strip().splitlines()[-1])
        metadata = record.get("metadata", {})
        require(isinstance(metadata.get("evidence_envelope"), dict), metadata)
        artifact = metadata.get("relaymem_retrieval_artifact")
        require(isinstance(artifact, dict), metadata)
        require(
            artifact["snippet_apply_decision"] == "eligible_but_not_applied",
            artifact,
        )
        require(artifact["ctx_block"] is None, artifact)
        require(artifact["apply_allowed"] is False, artifact)
    print("ok runtime trace has snippet apply decision and prompt remains metadata-only")


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
            _assert_default_valid_snippet(root)
            _assert_eligible_not_applied(root)
            _assert_snippet_disabled(root)
            _assert_blocked_evidence()
            _assert_small_budget(root)
            _assert_scene_and_ref_blocks(root)
            _assert_runtime_trace_and_prompt(root, capture, port)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
