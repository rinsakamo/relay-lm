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
from relaylm.app import _relayrun_relayscn_node


class _Capture:
    def __init__(self) -> None:
        self.payloads: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def add(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self.payloads.append(payload)

    def count(self) -> int:
        with self._lock:
            return len(self.payloads)

    def get(self, index: int) -> dict[str, Any]:
        with self._lock:
            return self.payloads[index]


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
                "id": "chatcmpl-relayrun-runtime-checkpoint-dry-run-smoke",
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
        "# RelayMEM\nRELAYRUN_SNIPPET_SENTINEL is bounded snippet evidence only.\n",
        encoding="utf-8",
    )


def _write_config(
    path: Path,
    *,
    port: int,
    trace_path: Path,
    store_root: Path,
    snippet_runtime_injection_enabled: bool = False,
    snippet_runtime_dry_run_only: bool = True,
) -> None:
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
            "snippet_runtime_injection_enabled": snippet_runtime_injection_enabled,
            "snippet_runtime_dry_run_only": snippet_runtime_dry_run_only,
            "snippet_budget": 512,
            "max_snippet_chars": 160,
            "max_snippet_candidates": 3,
            "candidate_limit": 3,
            "token_budget_hint": 800,
            "token_budget_truncation_enabled": False,
        }
    )
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")


def _payload(
    *,
    content: str,
    scene_type: str,
    confidence: float = 0.95,
    stability: float = 0.9,
) -> dict[str, Any]:
    return {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": content}],
        "metadata": {
            "scene_state": {
                "scene_type": scene_type,
                "confidence": confidence,
                "stability": stability,
            }
        },
        "stream": False,
    }


def _post(
    *,
    port: int,
    store_root: Path,
    payload: dict[str, Any],
    capture: _Capture,
    snippet_runtime_injection_enabled: bool = False,
    snippet_runtime_dry_run_only: bool = True,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    with tempfile.TemporaryDirectory() as td:
        trace_path = Path(td) / "trace.jsonl"
        cfg_path = Path(td) / "cfg.yaml"
        _write_config(
            cfg_path,
            port=port,
            trace_path=trace_path,
            store_root=store_root,
            snippet_runtime_injection_enabled=snippet_runtime_injection_enabled,
            snippet_runtime_dry_run_only=snippet_runtime_dry_run_only,
        )
        app = create_app(str(cfg_path))
        original = json.loads(json.dumps(payload))
        before_count = capture.count()
        with TestClient(app) as client:
            resp = client.post("/v1/chat/completions", json=payload)
            require(resp.status_code == 200, resp.text)
            headers = dict(resp.headers)
        after_count = capture.count()
        require(after_count == before_count + 1, (before_count, after_count, payload))
        require(payload == original, payload)
        record = json.loads(trace_path.read_text(encoding="utf-8").strip().splitlines()[-1])
        metadata = record.get("metadata", {})
        require(isinstance(metadata, dict), record)
        return capture.get(before_count), metadata, headers


def _relayrun_artifact(metadata: dict[str, Any]) -> dict[str, Any]:
    artifact = metadata.get("relayrun_artifact")
    require(isinstance(artifact, dict), metadata)
    return artifact


def _find_node(artifact: dict[str, Any], node_name: str) -> dict[str, Any]:
    nodes = artifact.get("node_statuses")
    require(isinstance(nodes, list), artifact)
    for node in nodes:
        if isinstance(node, dict) and node.get("node_name") == node_name:
            return node
    raise AssertionError((node_name, artifact))


def _assert_artifact_common(artifact: dict[str, Any], headers: dict[str, str]) -> None:
    require(artifact.get("schema_version") == "relayrun.runtime_checkpoint.v0", artifact)
    require(artifact.get("diagnostics_only") is True, artifact)
    require(artifact.get("applied") is False, artifact)
    require(isinstance(artifact.get("run_id"), str) and artifact.get("run_id"), artifact)
    require(artifact.get("resume_allowed") is False, artifact)
    require(artifact.get("resume_mode") == "none", artifact)
    require(artifact.get("checkpoint_persisted") is False, artifact)
    plan = artifact.get("checkpoint_persistence_plan")
    require(isinstance(plan, dict), artifact)
    require(plan.get("schema_version") == "relayrun.checkpoint_persistence_plan.v0", plan)
    require(plan.get("diagnostics_only") is True, plan)
    require(plan.get("write_allowed") is False, plan)
    require(plan.get("checkpoint_persisted") is False, plan)
    require(plan.get("run_id") == artifact.get("run_id"), plan)
    require(isinstance(plan.get("turn_id"), str) and plan.get("turn_id"), plan)
    target_path_preview = plan.get("target_path_preview")
    require(isinstance(target_path_preview, str), plan)
    require(str(plan.get("run_id")) in target_path_preview, plan)
    require(str(plan.get("turn_id")) in target_path_preview, plan)
    blocked_reasons = plan.get("blocked_reasons")
    require(isinstance(blocked_reasons, list), plan)
    require("checkpoint_persistence_not_implemented" in blocked_reasons, plan)
    require("checkpoint_write_disabled" in blocked_reasons, plan)
    require(plan.get("resume_allowed_after_persist") is False, plan)
    preflight = artifact.get("checkpoint_writer_preflight")
    require(isinstance(preflight, dict), artifact)
    require(preflight.get("schema_version") == "relayrun.checkpoint_writer_preflight.v0", preflight)
    require(preflight.get("diagnostics_only") is True, preflight)
    require(preflight.get("write_allowed") is False, preflight)
    require(preflight.get("preflight_passed") is False, preflight)
    require(preflight.get("checkpoint_write_attempted") is False, preflight)
    require(preflight.get("directory_creation_attempted") is False, preflight)
    require(preflight.get("target_root") == plan.get("target_root"), preflight)
    require(preflight.get("target_path_preview") == plan.get("target_path_preview"), preflight)
    path_safety = preflight.get("path_safety")
    require(isinstance(path_safety, dict), preflight)
    require(path_safety.get("root_relative") is True, preflight)
    require(path_safety.get("path_traversal_detected") is False, preflight)
    require(path_safety.get("absolute_path_detected") is False, preflight)
    content_policy = preflight.get("content_policy")
    require(isinstance(content_policy, dict), preflight)
    require(content_policy.get("content_free") is True, preflight)
    require(content_policy.get("backend_payload_included") is False, preflight)
    require(content_policy.get("response_text_included") is False, preflight)
    require(content_policy.get("raw_user_message_included") is False, preflight)
    preflight_blocked_reasons = preflight.get("blocked_reasons")
    require(isinstance(preflight_blocked_reasons, list), preflight)
    require("checkpoint_writer_not_implemented" in preflight_blocked_reasons, preflight)
    require("checkpoint_write_disabled" in preflight_blocked_reasons, preflight)
    future_writer_required_gates = preflight.get("future_writer_required_gates")
    require(isinstance(future_writer_required_gates, list), preflight)
    require("explicit_config_enabled" in future_writer_required_gates, preflight)
    require("safe_target_root" in future_writer_required_gates, preflight)
    require("content_free_payload" in future_writer_required_gates, preflight)
    require("atomic_write" in future_writer_required_gates, preflight)
    require("idempotent_run_turn_key" in future_writer_required_gates, preflight)
    require(artifact.get("recovery_transition_created") is False, artifact)
    require(artifact.get("stream_started") is False, artifact)
    require(artifact.get("first_token_sent") is False, artifact)
    require(headers.get("x-relaylm-run-id") == artifact.get("run_id"), headers)
    require(headers.get("x-relaylm-run-status") == "diagnostics_only", headers)
    require(headers.get("x-relaylm-resume-mode") == "none", headers)
    for node_name in (
        "request_received",
        "relayscn",
        "relayref",
        "relaymem_retrieval",
        "relaymem_runtime_ctx",
        "token_budget_truncation",
        "backend_forward",
    ):
        require(isinstance(_find_node(artifact, node_name), dict), artifact)


def _assert_backend_payload_not_polluted(backend_payload: dict[str, Any]) -> None:
    backend_text = json.dumps(backend_payload, ensure_ascii=False)
    require("relayrun_artifact" not in backend_text, backend_payload)
    require("relayrun.runtime_checkpoint.v0" not in backend_text, backend_payload)
    require("checkpoint_persistence_plan" not in backend_text, backend_payload)
    require("relayrun.checkpoint_persistence_plan.v0" not in backend_text, backend_payload)
    require("checkpoint_writer_preflight" not in backend_text, backend_payload)
    require("relayrun.checkpoint_writer_preflight.v0" not in backend_text, backend_payload)


def _assert_normal_case(root: Path, capture: _Capture, port: int) -> None:
    backend_payload, metadata, headers = _post(
        port=port,
        store_root=root,
        payload=_payload(
            content="RelayRUN dry-run checkpoint candidate",
            scene_type="design_talk",
        ),
        capture=capture,
    )
    artifact = _relayrun_artifact(metadata)
    _assert_artifact_common(artifact, headers)
    _assert_backend_payload_not_polluted(backend_payload)
    require(_find_node(artifact, "request_received")["node_status"] == "completed", artifact)
    require(_find_node(artifact, "relayscn")["node_status"] == "completed", artifact)
    require(_find_node(artifact, "relayref")["node_status"] == "completed", artifact)
    require(_find_node(artifact, "relaymem_retrieval")["node_status"] == "completed", artifact)
    require(_find_node(artifact, "relaymem_runtime_ctx")["node_status"] == "completed", artifact)
    require(_find_node(artifact, "token_budget_truncation")["node_status"] == "skipped", artifact)
    require(_find_node(artifact, "backend_forward")["node_status"] == "completed", artifact)
    print("ok normal request emits relayrun_artifact")
    print("ok normal request emits checkpoint_persistence_plan")
    print("ok normal request emits checkpoint_writer_preflight")
    print("ok backend payload not polluted by relayrun diagnostics")


def _assert_recovery_case(root: Path, capture: _Capture, port: int) -> None:
    backend_payload, metadata, headers = _post(
        port=port,
        store_root=root,
        payload=_payload(
            content="Recover the current context using RelayMEM.",
            scene_type="recovery",
        ),
        capture=capture,
        snippet_runtime_injection_enabled=True,
        snippet_runtime_dry_run_only=False,
    )
    artifact = _relayrun_artifact(metadata)
    _assert_artifact_common(artifact, headers)
    _assert_backend_payload_not_polluted(backend_payload)
    require(_find_node(artifact, "relayscn")["node_status"] == "blocked", artifact)
    require(_find_node(artifact, "relaymem_runtime_ctx")["node_status"] == "blocked", artifact)
    print("ok recovery scene still emits relayrun_artifact")
    print("ok recovery scene still emits checkpoint_persistence_plan")
    print("ok recovery scene still emits checkpoint_writer_preflight")


def _assert_unresolved_reference_case(root: Path, capture: _Capture, port: int) -> None:
    backend_payload, metadata, headers = _post(
        port=port,
        store_root=root,
        payload=_payload(
            content="それについて教えて",
            scene_type="design_talk",
        ),
        capture=capture,
        snippet_runtime_injection_enabled=True,
        snippet_runtime_dry_run_only=False,
    )
    artifact = _relayrun_artifact(metadata)
    _assert_artifact_common(artifact, headers)
    _assert_backend_payload_not_polluted(backend_payload)
    require(_find_node(artifact, "relayref")["node_status"] == "blocked", artifact)
    require(_find_node(artifact, "relaymem_runtime_ctx")["node_status"] == "blocked", artifact)
    print("ok unresolved reference still emits relayrun_artifact")
    print("ok unresolved reference still emits checkpoint_persistence_plan")
    print("ok unresolved reference still emits checkpoint_writer_preflight")


def _assert_snippet_enabled_case(root: Path, capture: _Capture, port: int) -> None:
    backend_payload, metadata, headers = _post(
        port=port,
        store_root=root,
        payload=_payload(
            content="RelayMEM snippet runtime candidate",
            scene_type="design_talk",
        ),
        capture=capture,
        snippet_runtime_injection_enabled=True,
        snippet_runtime_dry_run_only=False,
    )
    artifact = _relayrun_artifact(metadata)
    _assert_artifact_common(artifact, headers)
    _assert_backend_payload_not_polluted(backend_payload)
    require(
        metadata.get("runtime_snippet_injection_result", {}).get("applied") is True,
        metadata,
    )
    require(_find_node(artifact, "relaymem_runtime_ctx")["node_status"] == "completed", artifact)
    print("ok snippet-bearing path keeps relayrun node statuses intact")
    print("ok trace metadata includes relayrun_artifact")
    print("ok trace metadata includes checkpoint_persistence_plan")
    print("ok trace metadata includes checkpoint_writer_preflight")


def _assert_relayscn_persistence_block_design_talk_case() -> None:
    node = _relayrun_relayscn_node(
        {
            "schema_version": "relayscn.scene_policy_artifact.v0",
            "diagnostics_only": True,
            "scene_state": {
                "scene_type": "design_talk",
                "confidence": 0.4,
                "stability": 0.4,
            },
            "scene_policy": {
                "schema_version": "relayscn.scene_policy.v0",
                "persistence_block": True,
                "persistence_block_reasons": [
                    "confidence_below_threshold",
                    "stability_below_threshold",
                ],
            },
            "persistence_block": True,
            "persistence_block_reasons": [
                "confidence_below_threshold",
                "stability_below_threshold",
            ],
        }
    )
    require(node.get("node_status") == "blocked", node)
    blocked_reasons = node.get("blocked_reasons")
    require(isinstance(blocked_reasons, list), node)
    require("confidence_below_threshold" in blocked_reasons, node)
    require("stability_below_threshold" in blocked_reasons, node)
    print("ok relayscn persistence block marks design_talk node blocked")


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _build_store(root)
        capture = _Capture()
        _BackendHandler.capture = capture
        server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            _assert_relayscn_persistence_block_design_talk_case()
            port = server.server_address[1]
            _assert_normal_case(root, capture, port)
            _assert_recovery_case(root, capture, port)
            _assert_unresolved_reference_case(root, capture, port)
            _assert_snippet_enabled_case(root, capture, port)
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
