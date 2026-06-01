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
    _build_snippet_runtime_injection_plan,
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
                "id": "chatcmpl-relaymem-snippet-runtime-plan-smoke",
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
        "# RelayMEM\nSNIPPET_RUNTIME_PLAN_SENTINEL is diagnostics-only snippet body.\n",
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
        relayscn_scene_policy_artifact=_scene_artifact(scene_type),
        relayref_artifact=relayref_artifact,
        messages=[{"role": "user", "content": "RelayMEM snippet runtime plan"}],
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


def _assert_plan_shape(artifact: dict[str, Any]) -> dict[str, Any]:
    plan = artifact.get("snippet_runtime_injection_plan")
    require(isinstance(plan, dict), artifact)
    require(plan["schema_version"] == "relaymem.snippet_runtime_injection_plan.v0", plan)
    require(plan["diagnostics_only"] is True, plan)
    require(plan["applied"] is False, plan)
    require(plan["payload_mutation_allowed"] is False, plan)
    require(plan["target"] == "backend_messages", plan)
    require(plan["insertion_point"] == "before_latest_user", plan)
    require(plan["source"] == "ctx_block_snippet_candidate", plan)
    require(plan["apply_decision_source"] == "snippet_apply_decision", plan)
    require(artifact["ctx_block"] is None, artifact)
    require(artifact["apply_allowed"] is False, artifact)
    return plan


def _assert_valid_dry_run_plan(root: Path) -> None:
    artifact = _artifact_for(root)
    require(artifact["snippet_apply_decision"] == "dry_run_only", artifact)
    plan = _assert_plan_shape(artifact)
    require(isinstance(plan["preview_text"], str) and plan["preview_text"], plan)
    require("[RelayMEM Snippet Context Candidate]" in plan["preview_text"], plan)
    require("SNIPPET_RUNTIME_PLAN_SENTINEL" in plan["preview_text"], plan)
    require(plan["source_entries"], plan)
    require(plan["estimated_tokens"] > 0, plan)
    require("runtime_snippet_injection_not_implemented" in plan["blocked_reasons"], plan)
    print("ok dry_run_only snippet runtime injection plan previews diagnostics text")


def _assert_eligible_plan(root: Path) -> None:
    artifact = _artifact_for(
        root,
        snippet_dry_run_only=False,
        snippet_apply_enabled=True,
    )
    require(artifact["snippet_apply_decision"] == "eligible_but_not_applied", artifact)
    plan = _assert_plan_shape(artifact)
    require(isinstance(plan["preview_text"], str) and plan["preview_text"], plan)
    require(plan["applied"] is False, plan)
    require(plan["payload_mutation_allowed"] is False, plan)
    print("ok eligible snippet runtime injection plan remains diagnostics-only")


def _assert_blocked_plans(root: Path) -> None:
    blocked_cases = [
        _artifact_for(root, scene_type="recovery"),
        _artifact_for(root, scene_type="formal_document"),
        _artifact_for(root, scene_type="medical_or_safety"),
        _artifact_for(root, scene_type="unknown"),
        _artifact_for(root, relayref_artifact={"unresolved_reference_detected": True}),
        _artifact_for(root, snippet_extraction_enabled=False),
        _artifact_for(
            root,
            snippet_dry_run_only=False,
            snippet_apply_enabled=True,
            snippet_budget=1,
        ),
    ]
    for artifact in blocked_cases:
        plan = _assert_plan_shape(artifact)
        require(plan["preview_text"] is None, artifact)
        require(artifact["snippet_apply_decision"] in plan["blocked_reasons"], plan)
        require("ctx_block_snippet_candidate_empty" in plan["blocked_reasons"], plan)
    print("ok blocked snippet runtime injection plans do not preview snippet text")


def _assert_empty_candidate_plan() -> None:
    plan = _build_snippet_runtime_injection_plan(
        snippet_apply_decision="dry_run_only",
        ctx_block_snippet_candidate={
            "schema_version": "relaymem.ctx_block_snippet_candidate.v0",
            "diagnostics_only": True,
            "entries": [],
            "blocked": [],
        },
    )
    require(plan["preview_text"] is None, plan)
    require(plan["source_entries"] == [], plan)
    require("ctx_block_snippet_candidate_empty" in plan["blocked_reasons"], plan)
    print("ok empty snippet ctx block candidate produces no preview")


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
            "messages": [{"role": "user", "content": "RelayMEM snippet runtime plan"}],
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
        require("SNIPPET_RUNTIME_PLAN_SENTINEL" not in backend_text, capture.last())
        require("snippet_text" not in backend_text, capture.last())
        require("[RelayMEM Snippet Context Candidate]" not in backend_text, capture.last())
        record = json.loads(trace_path.read_text(encoding="utf-8").strip().splitlines()[-1])
        metadata = record.get("metadata", {})
        artifact = metadata.get("relaymem_retrieval_artifact")
        require(isinstance(artifact, dict), metadata)
        plan = artifact.get("snippet_runtime_injection_plan")
        require(isinstance(plan, dict), artifact)
        require("SNIPPET_RUNTIME_PLAN_SENTINEL" in plan.get("preview_text", ""), plan)
        require(plan["applied"] is False, plan)
        require(plan["payload_mutation_allowed"] is False, plan)
        require(artifact["ctx_block"] is None, artifact)
        require(artifact["apply_allowed"] is False, artifact)
    print("ok trace carries snippet runtime plan and backend remains metadata-only")


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
            _assert_valid_dry_run_plan(root)
            _assert_eligible_plan(root)
            _assert_blocked_plans(root)
            _assert_empty_candidate_plan()
            _assert_runtime_trace_and_prompt(root, capture, port)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
