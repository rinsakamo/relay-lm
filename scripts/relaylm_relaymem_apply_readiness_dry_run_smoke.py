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
                "id": "chatcmpl-relaymem-apply-readiness-smoke",
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


def _build_store(root: Path, *, with_page: bool = True) -> None:
    projects = root / "memory" / "mem" / "projects"
    projects.mkdir(parents=True)
    (root / "memory" / "mem" / "index.md").write_text("# Index\nRelayMEM\n", encoding="utf-8")
    (root / "memory" / "mem" / "log.md").write_text("# Log\n", encoding="utf-8")
    if with_page:
        (projects / "relaymem.md").write_text(
            "# RelayMEM\nRelayMEM ctx block apply readiness diagnostics candidate.\n",
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
    retrieval_dry_run_only: bool = True,
    ctx_block_apply_enabled: bool = False,
) -> dict[str, Any]:
    store = build_relaymem_store_diagnostics(
        root_path=str(store_root),
        store_enabled=True,
        retrieval_dry_run_only=retrieval_dry_run_only,
    )
    return build_relaymem_retrieval_dry_run_artifact(
        relayscn_scene_policy_artifact=_scene_artifact(scene_type, scope),
        relayint_intent_artifact=relayint_intent_artifact,
        messages=[{"role": "user", "content": "RelayMEM apply readiness"}],
        token_budget=token_budget,
        store_diagnostics=store,
        max_candidates=4,
        ctx_block_apply_enabled=ctx_block_apply_enabled,
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
            "ctx_block_apply_enabled": False,
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
        "ctx_block",
        "ctx_block_candidate",
        "apply_decision",
        "apply_blocked_reasons",
        "apply_preconditions",
        "apply_readiness_score",
    }
    require(forbidden.isdisjoint(payload), payload)
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        require(forbidden.isdisjoint(metadata), payload)


def _assert_apply_baseline(artifact: dict[str, Any]) -> None:
    require(artifact["ctx_block"] is None, artifact)
    require(artifact["apply_allowed"] is False, artifact)
    require(isinstance(artifact["apply_readiness_score"], float), artifact)
    require(isinstance(artifact["apply_blocked_reasons"], list), artifact)
    require(isinstance(artifact["apply_preconditions"], dict), artifact)


def main() -> int:
    with tempfile.TemporaryDirectory() as store_td:
        store_root = Path(store_td)
        _build_store(store_root)

        dry_run = _artifact_for(store_root=store_root)
        _assert_apply_baseline(dry_run)
        require(dry_run["apply_decision"] == "dry_run_only", dry_run)
        require("retrieval_dry_run_only" in dry_run["apply_blocked_reasons"], dry_run)
        print("ok retrieval_dry_run_only true keeps normal candidates dry_run_only")

        eligible = _artifact_for(
            store_root=store_root,
            retrieval_dry_run_only=False,
            ctx_block_apply_enabled=True,
        )
        _assert_apply_baseline(eligible)
        require(eligible["apply_decision"] == "eligible_but_not_applied", eligible)
        require("runtime_apply_not_implemented" in eligible["apply_blocked_reasons"], eligible)
        print("ok normal candidates can become eligible_but_not_applied without applying")

        recovery = _artifact_for(
            store_root=store_root,
            scene_type="recovery",
            scope="current_context_only",
            retrieval_dry_run_only=False,
            ctx_block_apply_enabled=True,
        )
        require(recovery["apply_decision"] == "blocked_scene_policy", recovery)
        require(recovery["ctx_block_candidate"]["entries"] == [], recovery)
        print("ok recovery apply readiness is blocked_scene_policy")

        for scene_type in ("formal_document", "medical_or_safety"):
            artifact = _artifact_for(
                store_root=store_root,
                scene_type=scene_type,
                retrieval_dry_run_only=False,
                ctx_block_apply_enabled=True,
            )
            require(artifact["apply_decision"] == "blocked_scene_policy", artifact)
            require(artifact["ctx_block_candidate"]["entries"] == [], artifact)
        print("ok formal_document and medical_or_safety apply readiness blocked by scene policy")

        unresolved = _artifact_for(
            store_root=store_root,
            relayint_intent_artifact={"unresolved_reference_detected": True},
            retrieval_dry_run_only=False,
            ctx_block_apply_enabled=True,
        )
        require(unresolved["apply_decision"] == "blocked_unresolved_reference", unresolved)
        require("unresolved_reference_requires_confirmation" in unresolved["apply_blocked_reasons"], unresolved)
        print("ok unresolved reference apply readiness is blocked_unresolved_reference")

        with tempfile.TemporaryDirectory() as empty_td:
            empty_root = Path(empty_td)
            _build_store(empty_root, with_page=False)
            no_candidates = _artifact_for(
                store_root=empty_root,
                retrieval_dry_run_only=False,
                ctx_block_apply_enabled=True,
            )
            require(no_candidates["apply_decision"] == "blocked_no_candidates", no_candidates)
            require(no_candidates["ctx_block_candidate"]["entries"] == [], no_candidates)
            print("ok no candidates apply readiness is blocked_no_candidates")

        truncated = _artifact_for(
            store_root=store_root,
            token_budget=1,
            retrieval_dry_run_only=False,
            ctx_block_apply_enabled=True,
        )
        require(truncated["apply_decision"] == "blocked_token_budget", truncated)
        require("token_budget_exceeded" in truncated["apply_blocked_reasons"], truncated)
        require(truncated["ctx_block_candidate"]["budget"]["truncated"] is True, truncated)
        print("ok small token budget apply readiness is blocked_token_budget")

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
                        json=_scene_payload("design_talk", "RelayMEM apply readiness"),
                    )
                    require(resp.status_code == 200, resp.text)
                    traced = _last_trace_artifact(trace_path)
                    require(traced["apply_decision"] == "dry_run_only", traced)
                    require(traced["ctx_block"] is None, traced)
                    require(traced["apply_allowed"] is False, traced)
                    _assert_no_backend_artifact(capture.last())
                    print("ok trace metadata includes apply_decision without backend mutation")
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
