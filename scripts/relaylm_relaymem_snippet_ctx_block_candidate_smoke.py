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
    _build_ctx_block_snippet_candidate,
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
                "id": "chatcmpl-relaymem-snippet-ctx-block-smoke",
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
        "# RelayMEM\nSNIPPET_CTX_SENTINEL is diagnostics-only snippet body.\n",
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
) -> dict[str, Any]:
    store = build_relaymem_store_diagnostics(
        root_path=str(root),
        store_enabled=True,
        retrieval_dry_run_only=False,
    )
    return build_relaymem_retrieval_dry_run_artifact(
        relayscn_scene_policy_artifact=_scene_artifact(scene_type, scope),
        relayref_artifact=relayref_artifact,
        messages=[{"role": "user", "content": "RelayMEM snippet ctx block"}],
        token_budget=800,
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


def _assert_candidate_shape(artifact: dict[str, Any]) -> None:
    candidate = artifact.get("ctx_block_snippet_candidate")
    require(isinstance(candidate, dict), artifact)
    require(candidate["schema_version"] == "relaymem.ctx_block_snippet_candidate.v0", candidate)
    require(candidate["diagnostics_only"] is True, candidate)
    require(candidate["applied_to_ctx"] is False, candidate)
    require(candidate["runtime_prompt_included"] is False, candidate)
    require(candidate["source"] == "evidence_envelope", candidate)
    require(candidate["apply_decision_source"] == "snippet_apply_decision", candidate)
    require(artifact["ctx_block"] is None, artifact)
    require(artifact["apply_allowed"] is False, artifact)


def _assert_valid_dry_run_candidate(root: Path) -> None:
    artifact = _artifact_for(root)
    require(artifact["snippet_apply_decision"] == "dry_run_only", artifact)
    _assert_candidate_shape(artifact)
    candidate = artifact["ctx_block_snippet_candidate"]
    require(candidate["entries"], candidate)
    entry = candidate["entries"][0]
    require("SNIPPET_CTX_SENTINEL" in entry["snippet_text"], entry)
    require(entry["applied_to_ctx"] is False, entry)
    require(entry["runtime_prompt_included"] is False, entry)
    require(entry["included"] is True, entry)
    ctx_entry = artifact["ctx_block_candidate"]["entries"][0]
    require("snippet_text" not in ctx_entry, ctx_entry)
    print("ok dry_run_only snippet ctx block candidate carries diagnostics snippet text")


def _assert_eligible_candidate(root: Path) -> None:
    artifact = _artifact_for(
        root,
        snippet_dry_run_only=False,
        snippet_apply_enabled=True,
    )
    require(artifact["snippet_apply_decision"] == "eligible_but_not_applied", artifact)
    _assert_candidate_shape(artifact)
    require(artifact["ctx_block_snippet_candidate"]["entries"], artifact)
    print("ok eligible snippet ctx block candidate remains diagnostics-only")


def _assert_blocked_candidates(root: Path) -> None:
    for scene_type in ("recovery", "formal_document", "medical_or_safety", "unknown"):
        artifact = _artifact_for(root, scene_type=scene_type)
        _assert_candidate_shape(artifact)
        require(artifact["ctx_block_snippet_candidate"]["entries"] == [], (scene_type, artifact))
    unresolved = _artifact_for(root, relayref_artifact={"unresolved_reference_detected": True})
    require(unresolved["snippet_apply_decision"] == "blocked_unresolved_reference", unresolved)
    require(unresolved["ctx_block_snippet_candidate"]["entries"] == [], unresolved)
    disabled = _artifact_for(root, snippet_extraction_enabled=False)
    require(disabled["snippet_apply_decision"] == "blocked_no_snippet", disabled)
    require(disabled["ctx_block_snippet_candidate"]["entries"] == [], disabled)
    small_budget = _artifact_for(
        root,
        snippet_dry_run_only=False,
        snippet_apply_enabled=True,
        snippet_budget=1,
    )
    require(small_budget["snippet_apply_decision"] == "blocked_snippet_budget", small_budget)
    small_candidate = small_budget["ctx_block_snippet_candidate"]
    require(small_candidate["entries"] == [], small_budget)
    require(small_candidate["budget"]["truncated"] is True, small_candidate)
    require(
        any(item.get("reason") == "snippet_budget_exceeded" for item in small_candidate["blocked"]),
        small_candidate,
    )
    require(
        all("snippet_text" not in item for item in small_candidate["blocked"]),
        small_candidate,
    )
    require(small_budget["ctx_block"] is None, small_budget)
    require(small_budget["apply_allowed"] is False, small_budget)
    print("ok blocked snippet decisions leave snippet ctx block entries empty")


def _assert_blocked_evidence_candidate() -> None:
    candidate = _build_ctx_block_snippet_candidate(
        snippet_apply_decision="blocked_snippet_evidence",
        snippet_candidates=[],
        evidence_envelope={
            "schema_version": "relaymem.evidence_envelope.v0",
            "diagnostics_only": True,
            "applied_to_ctx": False,
            "source": "selected_mem_candidates",
            "snippets": [],
            "blocked": [
                {
                    "evidence_id": "evidence:0",
                    "path": "memory/mem/projects/malformed.md",
                    "reason": "malformed_utf8",
                }
            ],
        },
        snippet_budget=512,
    )
    require(candidate["entries"] == [], candidate)
    require(candidate["blocked"][0]["reason"] == "malformed_utf8", candidate)
    require(candidate["applied_to_ctx"] is False, candidate)
    print("ok blocked snippet evidence is preserved as candidate blocked diagnostics")


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
            "messages": [{"role": "user", "content": "RelayMEM snippet ctx block"}],
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
        require("SNIPPET_CTX_SENTINEL" not in backend_text, capture.last())
        require("snippet_text" not in backend_text, capture.last())
        record = json.loads(trace_path.read_text(encoding="utf-8").strip().splitlines()[-1])
        metadata = record.get("metadata", {})
        artifact = metadata.get("relaymem_retrieval_artifact")
        require(isinstance(artifact, dict), metadata)
        candidate = artifact.get("ctx_block_snippet_candidate")
        require(isinstance(candidate, dict) and candidate["entries"], artifact)
        require("SNIPPET_CTX_SENTINEL" in candidate["entries"][0]["snippet_text"], candidate)
        require(artifact["ctx_block"] is None, artifact)
        require(artifact["apply_allowed"] is False, artifact)
    print("ok trace carries snippet ctx block candidate and backend remains metadata-only")


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
            _assert_valid_dry_run_candidate(root)
            _assert_eligible_candidate(root)
            _assert_blocked_candidates(root)
            _assert_blocked_evidence_candidate()
            _assert_runtime_trace_and_prompt(root, capture, port)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
