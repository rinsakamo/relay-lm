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
                "id": "chatcmpl-relaymem-ctx-block-candidate-smoke",
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
        "# RelayMEM\nRelayMEM selected memory candidate for dry-run ctx block packing.\n",
        encoding="utf-8",
    )
    (projects / "relayctx.md").write_text(
        "# RelayCTX\nRelayCTX handoff details and project context notes.\n",
        encoding="utf-8",
    )


def _scene_artifact(scene_type: str = "design_talk", scope: str = "project_context") -> dict[str, Any]:
    return {
        "scene_state": {"scene_type": scene_type, "confidence": 0.95, "stability": 0.9},
        "scene_policy": {"relaymem_retrieval_scope": scope},
        "persistence_block": scene_type in {"recovery", "formal_document", "medical_or_safety"},
        "persistence_block_reasons": [f"scene_type_is_{scene_type}"] if scene_type == "recovery" else [],
    }


def _artifact_for(
    *,
    store_root: Path,
    scene_type: str = "design_talk",
    scope: str = "project_context",
    token_budget: int | None = 800,
    relayint_intent_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    store = build_relaymem_store_diagnostics(
        root_path=str(store_root),
        store_enabled=True,
        retrieval_dry_run_only=True,
    )
    return build_relaymem_retrieval_dry_run_artifact(
        relayscn_scene_policy_artifact=_scene_artifact(scene_type, scope),
        relayint_intent_artifact=relayint_intent_artifact,
        messages=[{"role": "user", "content": "RelayMEM RelayCTX project context"}],
        token_budget=token_budget,
        store_diagnostics=store,
        max_candidates=4,
    )


def _write_config(path: Path, *, port: int, trace_path: Path, store_root: Path) -> None:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    cfg["backends"]["local_backend"]["base_url"] = f"http://127.0.0.1:{port}/v1"
    cfg["trace"] = {"enabled": True, "path": str(trace_path)}
    cfg["model_routes"]["relaylm-default"]["mode"] = "pass_through"
    cfg["memory"].update(
        {
            "store_enabled": True,
            "retrieval_dry_run_only": True,
            "root_path": str(store_root),
            "candidate_limit": 4,
            "token_budget_hint": 800,
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


def _last_trace_artifact(trace_path: Path) -> dict[str, Any]:
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
        "ctx_block_candidate",
        "store_diagnostics",
    }
    require(forbidden.isdisjoint(payload), payload)
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        require(forbidden.isdisjoint(metadata), payload)


def main() -> int:
    with tempfile.TemporaryDirectory() as store_td:
        store_root = Path(store_td)
        _build_store(store_root)

        artifact = _artifact_for(store_root=store_root)
        candidate = artifact["ctx_block_candidate"]
        require(artifact["ctx_block"] is None, artifact)
        require(artifact["apply_allowed"] is False, artifact)
        require(candidate["schema_version"] == "relaymem.ctx_block_candidate.v0", candidate)
        require(candidate["diagnostics_only"] is True, candidate)
        require(candidate["applied_to_ctx"] is False, candidate)
        require(len(candidate["entries"]) >= 1, candidate)
        require(all(entry["applied_to_ctx"] is False for entry in candidate["entries"]), candidate)
        require(any(entry["included"] is True for entry in candidate["entries"]), candidate)
        print("ok selected_mem_candidates produce diagnostics-only ctx_block_candidate entries")

        small_budget = _artifact_for(store_root=store_root, token_budget=1)
        small_candidate = small_budget["ctx_block_candidate"]
        require(small_candidate["budget"]["token_limit"] == 1, small_candidate)
        require(small_candidate["budget"]["truncated"] is True, small_candidate)
        require(any(entry["included"] is False for entry in small_candidate["entries"]), small_candidate)
        require(
            any(item["reason"] == "token_budget_exceeded" for item in small_candidate["blocked"]),
            small_candidate,
        )
        print("ok small token budget limits ctx_block_candidate entries")

        recovery = _artifact_for(
            store_root=store_root,
            scene_type="recovery",
            scope="current_context_only",
        )
        require(recovery["ctx_block_candidate"]["entries"] == [], recovery)
        require(recovery["ctx_block"] is None, recovery)
        print("ok recovery scene leaves ctx_block_candidate entries empty")

        for scene_type in ("formal_document", "medical_or_safety"):
            blocked = _artifact_for(store_root=store_root, scene_type=scene_type)
            require(blocked["ctx_block_candidate"]["entries"] == [], blocked)
            require(blocked["ctx_block"] is None, blocked)
        print("ok formal_document and medical_or_safety leave ctx_block_candidate entries empty")

        unresolved = _artifact_for(
            store_root=store_root,
            relayint_intent_artifact={"unresolved_reference_detected": True},
        )
        require(unresolved["ctx_block_candidate"]["entries"] == [], unresolved)
        require(unresolved["fallback_reason"] == "unresolved_reference_requires_confirmation", unresolved)
        print("ok unresolved reference leaves ctx_block_candidate entries empty")

        capture = _Capture()
        _BackendHandler.capture = capture
        server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
        port = int(server.server_address[1])
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as td:
                trace_path = Path(td) / "trace.jsonl"
                cfg_path = Path(td) / "cfg.yaml"
                _write_config(cfg_path, port=port, trace_path=trace_path, store_root=store_root)
                app = create_app(str(cfg_path))
                with TestClient(app) as client:
                    resp = client.post(
                        "/v1/chat/completions",
                        json=_scene_payload("design_talk", "RelayMEM ctx block candidate"),
                    )
                    require(resp.status_code == 200, resp.text)
                    traced = _last_trace_artifact(trace_path)
                    traced_candidate = traced.get("ctx_block_candidate")
                    require(isinstance(traced_candidate, dict), traced)
                    require(len(traced_candidate.get("entries", [])) >= 1, traced_candidate)
                    require(traced.get("ctx_block") is None, traced)
                    require(traced.get("apply_allowed") is False, traced)
                    _assert_no_backend_artifact(capture.last())
                    print("ok trace metadata includes ctx_block_candidate without backend mutation")
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
