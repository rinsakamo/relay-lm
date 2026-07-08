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

from _relaylm_phase_i3_test_support import form_primary_memory
from relaylm.app import create_app
from relaylm.relaymem_primary_recall import resolve_relaymem_character_store_root
from relaylm.relayrun_runtime_artifact import _relayrun_relayscn_node

NAMESPACE = "character/default"
CHARACTER_ID = "default"
SUMMARY = (
    "RelayRUN dry-run checkpoint candidate. "
    "Recover the current context using RelayMEM. "
    "RelayMEM snippet runtime candidate. "
    "RELAYRUN_SNIPPET_SENTINEL is bounded snippet evidence only."
)


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
    mem = root / "memory" / "mem"
    (root / "memory" / "sources" / "conversations").mkdir(parents=True, exist_ok=True)
    (mem / "primary" / "sessions").mkdir(parents=True, exist_ok=True)
    (mem / "primary" / "projects").mkdir(parents=True, exist_ok=True)
    (mem / "secondary" / "projects").mkdir(parents=True, exist_ok=True)
    form_primary_memory(
        root,
        namespace=NAMESPACE,
        candidate_id="relayrun-runtime-checkpoint",
        title="RelayRUN runtime checkpoint",
        summary=SUMMARY,
    )


def _configured_and_scoped_root(temp_dir: str) -> tuple[Path, Path]:
    configured_root = Path(temp_dir) / "memory-root"
    scoped = resolve_relaymem_character_store_root(str(configured_root), CHARACTER_ID)
    require(isinstance(scoped, str) and scoped, scoped)
    return configured_root, Path(scoped)


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


def _relayrun_projection(metadata: dict[str, Any]) -> dict[str, Any]:
    artifact = metadata.get("relayrun_artifact")
    require(isinstance(artifact, dict), metadata)
    return artifact


def _assert_relayrun_projection_common(
    artifact: dict[str, Any], headers: dict[str, str]
) -> None:
    require(artifact.get("schema_version") == "relayrun.runtime_checkpoint.v0", artifact)
    require(artifact.get("diagnostics_only") is True, artifact)
    require(artifact.get("content_free") is True, artifact)
    require(artifact.get("run_status") == "diagnostics_only", artifact)
    require(artifact.get("resume_mode") == "none", artifact)
    require(isinstance(artifact.get("run_id"), str) and artifact.get("run_id"), artifact)
    require(isinstance(artifact.get("blocked_reasons"), list), artifact)
    require(headers.get("x-relaylm-run-id") == artifact.get("run_id"), headers)
    require(headers.get("x-relaylm-run-status") == "diagnostics_only", headers)
    require(headers.get("x-relaylm-resume-mode") == "none", headers)


def _assert_projection_stays_minimal(artifact: dict[str, Any]) -> None:
    projection_text = json.dumps(artifact, ensure_ascii=False)
    forbidden_projection_tokens = (
        "checkpoint_persistence_plan",
        "checkpoint_writer_preflight",
        "resume_preflight",
        "recovery_transition_artifact",
        "waiting_user_contract",
        "recovery_apply_preflight",
        "recovery_response_draft",
        "visible_recovery_response_preflight",
        "recovery_response_generator",
        "output_relayscn_recovery_gate",
        "visible_recovery_apply_preflight",
        "user_action_contract",
        "backend_payload",
        "response_text",
    )
    for token in forbidden_projection_tokens:
        require(token not in projection_text, (token, artifact))


def _assert_projection_shows_recovery_detail(artifact: dict[str, Any]) -> None:
    require(artifact.get("diagnostics_only") is True, artifact)
    require(artifact.get("content_free") is True, artifact)
    recovery_transition_artifact = artifact.get("recovery_transition_artifact")
    require(isinstance(recovery_transition_artifact, dict), artifact)
    require(recovery_transition_artifact.get("diagnostics_only") is True, artifact)
    safety = recovery_transition_artifact.get("safety")
    require(isinstance(safety, dict), artifact)
    require(safety.get("contains_user_content") is False, artifact)
    require(safety.get("contains_backend_payload") is False, artifact)
    require(safety.get("contains_response_text") is False, artifact)


def _assert_backend_payload_not_polluted(backend_payload: dict[str, Any]) -> None:
    backend_text = json.dumps(backend_payload, ensure_ascii=False)
    forbidden_backend_tokens = (
        "relayrun_artifact",
        "relayrun.runtime_checkpoint.v0",
        "checkpoint_persistence_plan",
        "relayrun.checkpoint_persistence_plan.v0",
        "checkpoint_writer_preflight",
        "relayrun.checkpoint_writer_preflight.v0",
        "checkpoint_envelope",
        "resume_preflight",
        "relayrun.resume_preflight.v0",
        "recovery_transition_artifact",
        "relayrun.recovery_transition.v0",
    )
    for token in forbidden_backend_tokens:
        require(token not in backend_text, (token, backend_payload))


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
    artifact = _relayrun_projection(metadata)
    _assert_relayrun_projection_common(artifact, headers)
    _assert_projection_stays_minimal(artifact)
    allowed_blocked_reasons = {
        "relaymem_retrieval:snippet_apply_decision:blocked_no_candidates",
    }
    require(
        set(artifact.get("blocked_reasons") or []).issubset(allowed_blocked_reasons),
        artifact,
    )
    _assert_backend_payload_not_polluted(backend_payload)
    print("ok normal request emits content-free relayrun projection")
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
    artifact = _relayrun_projection(metadata)
    _assert_relayrun_projection_common(artifact, headers)
    # The recovery scene raises a genuine recovery-relevant relayint block
    # (ambiguous reference under context_repair mode), so the lazy helper is
    # expected to construct full recovery detail rather than stay minimal.
    _assert_projection_shows_recovery_detail(artifact)
    _assert_backend_payload_not_polluted(backend_payload)
    print("ok recovery scene surfaces full recovery detail via lazy helper")


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
    artifact = _relayrun_projection(metadata)
    _assert_relayrun_projection_common(artifact, headers)
    # An unresolved reference is a genuine recovery-relevant relayint block,
    # so the lazy helper is expected to construct full recovery detail.
    _assert_projection_shows_recovery_detail(artifact)
    _assert_backend_payload_not_polluted(backend_payload)
    print("ok unresolved reference surfaces full recovery detail via lazy helper")


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
    artifact = _relayrun_projection(metadata)
    _assert_relayrun_projection_common(artifact, headers)
    _assert_projection_stays_minimal(artifact)
    _assert_backend_payload_not_polluted(backend_payload)
    runtime_ctx = metadata.get("runtime_ctx_injection_result", {})
    runtime_snippet = metadata.get("runtime_snippet_injection_result", {})
    require(
        (
            isinstance(runtime_ctx, dict)
            and runtime_ctx.get("applied") is True
        )
        or (
            isinstance(runtime_snippet, dict)
            and runtime_snippet.get("applied") is True
        ),
        metadata,
    )
    print("ok snippet-bearing path keeps content-free relayrun projection")


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
        configured_root, scoped_root = _configured_and_scoped_root(td)
        _build_store(scoped_root)
        capture = _Capture()
        _BackendHandler.capture = capture
        server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            _assert_relayscn_persistence_block_design_talk_case()
            port = server.server_address[1]
            _assert_normal_case(configured_root, capture, port)
            _assert_recovery_case(configured_root, capture, port)
            _assert_unresolved_reference_case(configured_root, capture, port)
            _assert_snippet_enabled_case(configured_root, capture, port)
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
