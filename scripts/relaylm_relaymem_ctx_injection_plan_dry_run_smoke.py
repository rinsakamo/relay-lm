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
from relaylm.relaymem_store import build_relaymem_store_diagnostics


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
                "id": "chatcmpl-relaymem-ctx-injection-plan-smoke",
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
    mem = root / "memory" / "mem"
    (root / "memory" / "sources" / "conversations").mkdir(parents=True)
    (mem / "primary" / "sessions").mkdir(parents=True)
    (mem / "secondary" / "projects").mkdir(parents=True)
    (mem / "index.md").write_text("# Index\nRelayMEM\n", encoding="utf-8")
    (mem / "log.md").write_text("# Log\n", encoding="utf-8")
    if with_page:
        (mem / "secondary" / "projects" / "relaymem.md").write_text(
            "# RelayMEM\nRelayMEM ctx injection plan diagnostics candidate.\n",
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
    relayref_artifact: dict[str, Any] | None = None,
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
        relayref_artifact=relayref_artifact,
        messages=[{"role": "user", "content": "RelayMEM ctx injection plan"}],
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
            "scene_state": {"scene_type": scene_type, "confidence": 0.95, "stability": 0.9}
        },
        "stream": False,
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


def _content_free_projection(metadata: dict[str, Any]) -> dict[str, Any]:
    require("relaymem_retrieval_artifact" not in metadata, "full retrieval artifact leaked")
    projection = metadata.get("relaymem_primary_recall_projection")
    require(isinstance(projection, dict), metadata)
    require(projection.get("content_free") is True, projection)
    require(projection.get("content_included") is False, projection)
    require(projection.get("memory_text_included") is False, projection)
    require(projection.get("path_values_included") is False, projection)
    require(projection.get("backend_prompt_included") is False, projection)
    return projection


def _assert_no_backend_artifact(payload: dict[str, Any]) -> None:
    forbidden = {
        "relaymem_retrieval_artifact",
        "relaymem_primary_recall_projection",
        "ctx_block",
        "ctx_block_candidate",
        "ctx_injection_plan",
        "apply_decision",
    }
    require(forbidden.isdisjoint(payload), payload)
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        require(forbidden.isdisjoint(metadata), payload)


def _assert_plan_baseline(artifact: dict[str, Any]) -> dict[str, Any]:
    require(artifact["ctx_block"] is None, artifact)
    require(artifact["apply_allowed"] is False, artifact)
    plan = artifact["ctx_injection_plan"]
    require(plan["schema_version"] == "relaymem.ctx_injection_plan.v0", plan)
    require(plan["diagnostics_only"] is True, plan)
    require(plan["applied"] is False, plan)
    require(plan["payload_mutation_allowed"] is False, plan)
    require(plan["target"] == "backend_messages", plan)
    return plan


def _assert_plan_blocked(artifact: dict[str, Any], decision: str) -> None:
    plan = _assert_plan_baseline(artifact)
    require(artifact["apply_decision"] == decision, artifact)
    require(plan["preview_text"] is None, plan)
    require(plan["source_entries"] == [], plan)
    require(decision in plan["blocked_reasons"], plan)


def main() -> int:
    with tempfile.TemporaryDirectory() as store_td:
        store_root = Path(store_td)
        _build_store(store_root)

        dry_run = _artifact_for(store_root=store_root)
        plan = _assert_plan_baseline(dry_run)
        require(dry_run["apply_decision"] == "dry_run_only", dry_run)
        require(plan["preview_text"] and "[RelayMEM Context Candidate]" in plan["preview_text"], plan)
        require(plan["source_entries"], plan)
        require("runtime_ctx_injection_not_implemented" in plan["blocked_reasons"], plan)
        print("ok retrieval_dry_run_only plan emits preview but remains unapplied")

        eligible = _artifact_for(
            store_root=store_root,
            retrieval_dry_run_only=False,
            ctx_block_apply_enabled=True,
        )
        eligible_plan = _assert_plan_baseline(eligible)
        require(eligible["apply_decision"] == "eligible_but_not_applied", eligible)
        require(eligible_plan["preview_text"] and eligible_plan["source_entries"], eligible_plan)
        print("ok eligible_but_not_applied plan emits preview but remains unapplied")

        recovery = _artifact_for(
            store_root=store_root,
            scene_type="recovery",
            scope="current_context_only",
            retrieval_dry_run_only=False,
            ctx_block_apply_enabled=True,
        )
        _assert_plan_blocked(recovery, "blocked_scene_policy")
        print("ok recovery plan is blocked with empty preview")

        for scene_type in ("formal_document", "medical_or_safety"):
            artifact = _artifact_for(
                store_root=store_root,
                scene_type=scene_type,
                retrieval_dry_run_only=False,
                ctx_block_apply_enabled=True,
            )
            _assert_plan_blocked(artifact, "blocked_scene_policy")
        print("ok formal_document and medical_or_safety plans are blocked with empty preview")

        unresolved = _artifact_for(
            store_root=store_root,
            relayref_artifact={"unresolved_reference_detected": True},
            retrieval_dry_run_only=False,
            ctx_block_apply_enabled=True,
        )
        _assert_plan_blocked(unresolved, "blocked_unresolved_reference")
        print("ok unresolved reference plan is blocked with empty preview")

        with tempfile.TemporaryDirectory() as empty_td:
            empty_root = Path(empty_td)
            _build_store(empty_root, with_page=False)
            no_candidates = _artifact_for(
                store_root=empty_root,
                retrieval_dry_run_only=False,
                ctx_block_apply_enabled=True,
            )
            _assert_plan_blocked(no_candidates, "blocked_no_candidates")
            print("ok no candidates plan is blocked with empty preview")

        truncated = _artifact_for(
            store_root=store_root,
            token_budget=1,
            retrieval_dry_run_only=False,
            ctx_block_apply_enabled=True,
        )
        _assert_plan_blocked(truncated, "blocked_token_budget")
        print("ok small token budget plan is blocked with empty preview")

        capture = _Capture()
        _BackendHandler.capture = capture
        server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
        port = int(server.server_address[1])
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as td:
                configured_root = Path(td) / "memory-root"
                scoped = resolve_relaymem_character_store_root(str(configured_root), "default")
                require(isinstance(scoped, str), scoped)
                _build_store(Path(scoped))
                trace_path = Path(td) / "trace.jsonl"
                cfg_path = Path(td) / "cfg.yaml"
                _write_config(cfg_path, port=port, trace_path=trace_path, store_root=configured_root)
                app = create_app(str(cfg_path))
                with TestClient(app) as client:
                    resp = client.post(
                        "/v1/chat/completions",
                        json=_scene_payload("design_talk", "RelayMEM ctx injection plan"),
                    )
                    require(resp.status_code == 200, resp.text)
                    metadata = _last_backend_response_metadata(trace_path)
                    projection = _content_free_projection(metadata)
                    require(projection["selected_count"] == 0, projection)
                    require(projection["character_scope_resolved"] is True, projection)
                    require(projection["injection_performed"] is False, projection)
                    require("legacy_flat_store_compatibility" not in projection["blocked_reason_ids"], projection)
                    _assert_no_backend_artifact(capture.last_chat_payload())
                    print("ok trace exposes target-only content-free plan status without backend mutation")
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
