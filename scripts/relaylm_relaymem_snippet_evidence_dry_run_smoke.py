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
from relaylm.relaymem_retrieval import build_relaymem_retrieval_dry_run_artifact
from relaylm.relaymem_store import (
    build_relaymem_snippet_evidence_dry_run,
    build_relaymem_store_diagnostics,
)


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
                "id": "chatcmpl-relaymem-snippet-evidence-smoke",
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
    concepts = root / "memory" / "mem" / "concepts"
    raw = root / "memory" / "raw"
    projects.mkdir(parents=True)
    concepts.mkdir(parents=True)
    raw.mkdir(parents=True)
    (root / "memory" / "mem" / "index.md").write_text("# Index\nRelayMEM\n", encoding="utf-8")
    (root / "memory" / "mem" / "log.md").write_text("# Log\n", encoding="utf-8")
    (projects / "relaymem.md").write_text(
        "# RelayMEM\nSNIPPET_SENTINEL should stay out of runtime prompts.\n" * 4,
        encoding="utf-8",
    )
    (concepts / "malformed.md").write_bytes(b"\xff\xfe\xff")
    (raw / "raw.md").write_text("raw body must be blocked\n", encoding="utf-8")
    (projects / "large.md").write_text("x" * 2048, encoding="utf-8")
    try:
        (projects / "linked.md").symlink_to(projects / "relaymem.md")
    except OSError:
        pass


def _scene_artifact(scene_type: str = "design_talk", scope: str = "project_context") -> dict[str, Any]:
    return {
        "scene_state": {"scene_type": scene_type, "confidence": 0.95, "stability": 0.9},
        "scene_policy": {"relaymem_retrieval_scope": scope},
        "persistence_block": scene_type in {"recovery", "formal_document", "medical_or_safety"},
        "persistence_block_reasons": [],
    }


def _retrieval(root: Path, *, scene_type: str = "design_talk", scope: str = "project_context", relayref: dict[str, Any] | None = None, token_budget: int | None = 800) -> dict[str, Any]:
    store = build_relaymem_store_diagnostics(
        root_path=str(root),
        store_enabled=True,
        retrieval_dry_run_only=False,
    )
    return build_relaymem_retrieval_dry_run_artifact(
        relayscn_scene_policy_artifact=_scene_artifact(scene_type, scope),
        relayint_intent_artifact=relayref,
        messages=[{"role": "user", "content": "RelayMEM snippet evidence"}],
        token_budget=token_budget,
        store_diagnostics=store,
        max_candidates=3,
        ctx_block_apply_enabled=True,
        snippet_extraction_enabled=True,
        snippet_dry_run_only=True,
        max_snippet_chars=48,
        max_snippet_candidates=3,
    )


def _assert_basic_snippet_artifact(root: Path) -> None:
    artifact = _retrieval(root)
    snippets = artifact.get("snippet_candidates")
    require(isinstance(snippets, list) and snippets, artifact)
    first = next(
        (item for item in snippets if item.get("path") == "memory/mem/projects/relaymem.md"),
        None,
    )
    require(isinstance(first, dict), snippets)
    require(first["evidence_kind"] == "bounded_page_snippet", first)
    require(first["snippet_chars"] <= 48, first)
    require("SNIPPET_SENTINEL" in first["snippet_text"], first)
    require(first["applied_to_ctx"] is False, first)
    require(first["safe_for_prompt_preview"] is False, first)
    envelope = artifact.get("evidence_envelope")
    require(envelope["schema_version"] == "relaymem.evidence_envelope.v0", envelope)
    require(envelope["diagnostics_only"] is True, envelope)
    require(envelope["applied_to_ctx"] is False, envelope)
    require(envelope["snippets"][0]["content_included_in_runtime_prompt"] is False, envelope)
    print("ok snippet_candidates and evidence_envelope dry-run")


def _assert_store_safety_blocks(root: Path) -> None:
    selected = [
        {"path": "../secret.md", "source": "mem_page", "reason": "test"},
        {"path": "memory/raw/raw.md", "source": "mem_page", "reason": "test"},
        {"path": "memory/mem/concepts/malformed.md", "source": "mem_page", "reason": "test"},
        {"path": "memory/mem/projects/large.md", "source": "mem_page", "reason": "test"},
        {"path": "memory/mem/projects/linked.md", "source": "mem_page", "reason": "test"},
    ]
    evidence = build_relaymem_snippet_evidence_dry_run(
        root_path=str(root),
        selected_mem_candidates=selected,
        snippet_extraction_enabled=True,
        snippet_dry_run_only=True,
        max_snippet_chars=64,
        max_snippet_candidates=5,
        max_read_bytes=1024,
    )
    blocked = evidence["evidence_envelope"]["blocked"]
    reasons = {item.get("reason") for item in blocked}
    require("path_outside_mem_scope" in reasons, blocked)
    require("unsupported_scope" in reasons, blocked)
    require("malformed_utf8" in reasons, blocked)
    require("read_limit_exceeded" in reasons, blocked)
    if (root / "memory" / "mem" / "projects" / "linked.md").is_symlink():
        require("symlink_blocked" in reasons, blocked)
    require(evidence["snippet_candidates"] == [], evidence)
    print("ok traversal raw malformed utf8 read-limit and symlink candidates blocked")


def _assert_safety_scene_skips(root: Path) -> None:
    for scene_type in ["recovery", "formal_document", "medical_or_safety", "unknown"]:
        artifact = _retrieval(root, scene_type=scene_type)
        require(artifact["snippet_candidates"] == [], (scene_type, artifact))
        require(artifact["evidence_envelope"]["snippets"] == [], (scene_type, artifact))
    current_context = _retrieval(root, scope="current_context_only")
    require(current_context["snippet_candidates"] == [], current_context)
    unresolved = _retrieval(root, relayref={"unresolved_reference_detected": True})
    require(unresolved["snippet_candidates"] == [], unresolved)
    tiny_budget = _retrieval(root, token_budget=1)
    require(tiny_budget["apply_decision"] == "blocked_token_budget", tiny_budget)
    require(tiny_budget["snippet_candidates"] == [], tiny_budget)
    print("ok scene reference and token-budget safety skip snippet extraction")


def _write_config(path: Path, *, port: int, trace_path: Path, store_root: Path) -> None:
    cfg = {
        "mode": "pass_through",
        "listen": {"host": "127.0.0.1", "port": 0},
        "trace": {"enabled": True, "path": str(trace_path)},
        "memory": {
            "root_path": str(store_root),
            "store_enabled": True,
            "retrieval_dry_run_only": False,
            "ctx_block_apply_enabled": True,
            "candidate_limit": 3,
            "token_budget_hint": 800,
            "snippet_extraction_enabled": True,
            "snippet_dry_run_only": True,
            "max_snippet_chars": 64,
            "max_snippet_candidates": 3,
        },
        "backends": {
            "local_backend": {
                "type": "openai_compatible",
                "base_url": f"http://127.0.0.1:{port}/v1",
                "api_key": "dummy",
                "default_model": "local-model",
            }
        },
        "model_routes": {
            "relaylm-default": {
                "backend": "local_backend",
                "backend_model": "local-model",
                "character_id": "default",
                "mode": "pass_through",
            }
        },
        "characters": {
            "default": {
                "soul": "examples/profiles/default/SOUL.md",
                "output_policy": "examples/profiles/default/style.md",
            }
        },
    }
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")


def _assert_runtime_trace_and_prompt(root: Path, capture: _Capture, port: int) -> None:
    with tempfile.TemporaryDirectory() as td:
        trace_path = Path(td) / "trace.jsonl"
        cfg_path = Path(td) / "cfg.yaml"
        _write_config(cfg_path, port=port, trace_path=trace_path, store_root=root)
        app = create_app(str(cfg_path))
        original_payload = {
            "model": "relaylm-default",
            "messages": [{"role": "user", "content": "RelayMEM snippet evidence"}],
            "metadata": {
                "scene_state": {
                    "scene_type": "design_talk",
                    "confidence": 0.95,
                    "stability": 0.9,
                }
            },
            "stream": False,
        }
        payload_before = json.loads(json.dumps(original_payload))
        with TestClient(app) as client:
            resp = client.post("/v1/chat/completions", json=original_payload)
            require(resp.status_code == 200, resp.text)
        require(original_payload == payload_before, original_payload)
        backend_payload = capture.last()
        backend_text = json.dumps(backend_payload, ensure_ascii=False)
        require("[RelayMEM Context]" in backend_text, backend_payload)
        require("memory/mem/projects/relaymem.md" in backend_text, backend_payload)
        require("SNIPPET_SENTINEL" not in backend_text, backend_payload)
        require("snippet_text" not in backend_text, backend_payload)
        record = json.loads(trace_path.read_text(encoding="utf-8").strip().splitlines()[-1])
        metadata = record.get("metadata", {})
        envelope = metadata.get("evidence_envelope")
        require(isinstance(envelope, dict), metadata)
        require(envelope["snippets"], envelope)
        artifact = metadata.get("relaymem_retrieval_artifact")
        require(isinstance(artifact, dict), metadata)
        snippet_candidates = artifact.get("snippet_candidates")
        require(isinstance(snippet_candidates, list) and snippet_candidates, artifact)
        require(
            any("SNIPPET_SENTINEL" in item.get("snippet_text", "") for item in snippet_candidates),
            artifact,
        )
        result = metadata.get("runtime_ctx_injection_result")
        require(result["applied"] is True, result)
    print("ok trace includes evidence envelope and runtime prompt stays metadata-only")


def main() -> int:
    capture = _Capture()
    _BackendHandler.capture = capture
    server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
    port = int(server.server_address[1])
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory() as store_td:
            root = Path(store_td)
            _build_store(root)
            _assert_basic_snippet_artifact(root)
            _assert_store_safety_blocks(root)
            _assert_safety_scene_skips(root)
            _assert_runtime_trace_and_prompt(root, capture, port)
    finally:
        server.shutdown()
        thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
