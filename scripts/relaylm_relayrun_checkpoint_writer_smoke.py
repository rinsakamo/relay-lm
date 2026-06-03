from __future__ import annotations

import json
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

import yaml
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = Path(__file__).resolve().parent
for path in (REPO_ROOT, SCRIPTS_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from relaylm.app import create_app
import relaylm.relayrun as relayrun_module
from relaylm.relayrun import (
    build_relayrun_node,
    build_runtime_checkpoint_dry_run_artifact,
    write_relayrun_checkpoint_if_enabled,
)
from relaylm_relayrun_runtime_checkpoint_dry_run_smoke import (  # type: ignore[import-not-found]
    _BackendHandler,
    _Capture,
    _build_store,
)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _write_config(
    path: Path,
    *,
    port: int,
    trace_path: Path,
    store_root: Path,
    checkpoint_root: str,
    write_enabled: bool,
    dry_run_only: bool,
) -> None:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    cfg["backends"]["local_backend"]["base_url"] = f"http://127.0.0.1:{port}/v1"
    cfg["trace"] = {"enabled": True, "path": str(trace_path)}
    cfg["model_routes"]["relaylm-default"]["mode"] = "pass_through"
    cfg["relayrun_checkpoint_write_enabled"] = write_enabled
    cfg["relayrun_checkpoint_root"] = checkpoint_root
    cfg["relayrun_checkpoint_dry_run_only"] = dry_run_only
    cfg["memory"].update(
        {
            "root_path": str(store_root),
            "store_enabled": True,
            "retrieval_dry_run_only": False,
            "ctx_block_apply_enabled": True,
            "snippet_extraction_enabled": True,
            "snippet_dry_run_only": False,
            "snippet_apply_enabled": True,
            "snippet_runtime_injection_enabled": False,
            "snippet_runtime_dry_run_only": True,
            "candidate_limit": 3,
            "token_budget_hint": 800,
            "token_budget_truncation_enabled": False,
        }
    )
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")


def _payload(content: str = "RAW_USER_SHOULD_NOT_PERSIST") -> dict[str, Any]:
    return {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": content}],
        "metadata": {
            "scene_state": {
                "scene_type": "design_talk",
                "confidence": 0.95,
                "stability": 0.9,
            }
        },
        "stream": False,
    }


def _post(
    *,
    port: int,
    store_root: Path,
    checkpoint_root: str,
    write_enabled: bool,
    dry_run_only: bool,
    capture: _Capture,
) -> tuple[dict[str, Any], dict[str, Any], Path]:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as td:
        trace_path = Path(td) / "trace.jsonl"
        cfg_path = Path(td) / "cfg.yaml"
        _write_config(
            cfg_path,
            port=port,
            trace_path=trace_path,
            store_root=store_root,
            checkpoint_root=checkpoint_root,
            write_enabled=write_enabled,
            dry_run_only=dry_run_only,
        )
        app = create_app(str(cfg_path))
        payload = _payload()
        original = json.loads(json.dumps(payload))
        before_count = capture.count()
        with TestClient(app) as client:
            resp = client.post("/v1/chat/completions", json=payload)
            require(resp.status_code == 200, resp.text)
        require(payload == original, payload)
        require(capture.count() == before_count + 1, capture.count())
        record = json.loads(trace_path.read_text(encoding="utf-8").strip().splitlines()[-1])
        metadata = record.get("metadata", {})
        require(isinstance(metadata, dict), record)
        return capture.get(before_count), metadata, Path(td)


def _relayrun(metadata: dict[str, Any]) -> dict[str, Any]:
    artifact = metadata.get("relayrun_artifact")
    require(isinstance(artifact, dict), metadata)
    return artifact


def _assert_backend_payload_not_mutated(backend_payload: dict[str, Any]) -> None:
    backend_text = json.dumps(backend_payload, ensure_ascii=False)
    require("relayrun_artifact" not in backend_text, backend_payload)
    require("checkpoint_writer_preflight" not in backend_text, backend_payload)
    require("relayrun.checkpoint_envelope.v0" not in backend_text, backend_payload)


def _assert_no_forbidden_checkpoint_content(envelope: dict[str, Any], raw_text: str) -> None:
    forbidden_keys = {
        "backend_payload",
        "messages",
        "raw_messages",
        "raw_user_message",
        "response_text",
        "prompt",
        "prompt_text",
        "snippet_text",
        "page_body",
        "api_key",
    }

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                require(str(key) not in forbidden_keys, envelope)
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(envelope)
    require("RAW_USER_SHOULD_NOT_PERSIST" not in raw_text, raw_text)
    require("BACKEND_PAYLOAD_SHOULD_NOT_PERSIST" not in raw_text, raw_text)
    require("snippet_text" not in raw_text, raw_text)


def _assert_default_disabled(root: Path, capture: _Capture, port: int) -> None:
    checkpoint_root = (root / "default_disabled").relative_to(REPO_ROOT).as_posix()
    backend_payload, metadata, _ = _post(
        port=port,
        store_root=root / "store-default-disabled",
        checkpoint_root=checkpoint_root,
        write_enabled=False,
        dry_run_only=True,
        capture=capture,
    )
    artifact = _relayrun(metadata)
    preflight = artifact.get("checkpoint_writer_preflight")
    require(isinstance(preflight, dict), artifact)
    require(artifact.get("checkpoint_persisted") is False, artifact)
    require(artifact.get("checkpoint_write_attempted") is False, artifact)
    require("checkpoint_write_disabled" in preflight.get("blocked_reasons", []), artifact)
    require(not (root / "default_disabled").exists(), root)
    _assert_backend_payload_not_mutated(backend_payload)
    print("ok default disabled does not write checkpoint")


def _assert_enabled_dry_run(root: Path, capture: _Capture, port: int) -> None:
    checkpoint_root = (root / "enabled_dry_run").relative_to(REPO_ROOT).as_posix()
    backend_payload, metadata, _ = _post(
        port=port,
        store_root=root / "store-enabled-dry-run",
        checkpoint_root=checkpoint_root,
        write_enabled=True,
        dry_run_only=True,
        capture=capture,
    )
    artifact = _relayrun(metadata)
    preflight = artifact.get("checkpoint_writer_preflight")
    require(isinstance(preflight, dict), artifact)
    require(artifact.get("checkpoint_persisted") is False, artifact)
    require(artifact.get("checkpoint_write_attempted") is False, artifact)
    require("checkpoint_dry_run_only" in preflight.get("blocked_reasons", []), artifact)
    require(not (root / "enabled_dry_run").exists(), root)
    _assert_backend_payload_not_mutated(backend_payload)
    print("ok enabled dry-run-only does not write checkpoint")


def _assert_enabled_write(root: Path, capture: _Capture, port: int) -> None:
    checkpoint_root_abs = root / "enabled_write"
    checkpoint_root = checkpoint_root_abs.relative_to(REPO_ROOT).as_posix()
    backend_payload, metadata, _ = _post(
        port=port,
        store_root=root / "store-enabled-write",
        checkpoint_root=checkpoint_root,
        write_enabled=True,
        dry_run_only=False,
        capture=capture,
    )
    artifact = _relayrun(metadata)
    preflight = artifact.get("checkpoint_writer_preflight")
    require(isinstance(preflight, dict), artifact)
    require(artifact.get("checkpoint_persisted") is True, artifact)
    require(artifact.get("checkpoint_write_attempted") is True, artifact)
    require(artifact.get("content_free") is True, artifact)
    persisted_path = artifact.get("persisted_path")
    require(isinstance(persisted_path, str) and persisted_path, artifact)
    persisted = (REPO_ROOT / persisted_path).resolve()
    require(persisted.exists(), persisted)
    require(checkpoint_root_abs.resolve() in persisted.parents, persisted)
    raw_text = persisted.read_text(encoding="utf-8")
    envelope = json.loads(raw_text)
    require(envelope.get("schema_version") == "relayrun.checkpoint_envelope.v0", envelope)
    require(envelope.get("content_free") is True, envelope)
    require(envelope.get("checkpoint_persisted") is True, envelope)
    require(artifact.get("persisted_bytes") == len(raw_text.encode("utf-8")), artifact)
    _assert_no_forbidden_checkpoint_content(envelope, raw_text)
    _assert_backend_payload_not_mutated(backend_payload)
    require(metadata.get("relayrun_artifact", {}).get("persisted_path") == persisted_path, metadata)
    print("ok enabled writer persists content-free checkpoint envelope")
    print("ok trace metadata includes checkpoint writer result")


def _assert_unsafe_path_direct(root: Path) -> None:
    artifact = build_runtime_checkpoint_dry_run_artifact(
        request_id="request-unsafe",
        run_id="run-unsafe",
        route_model="relaylm-default",
        node_statuses=[build_relayrun_node(node_name="request_received", node_status="completed")],
        checkpoint_target_root="../unsafe-checkpoints",
    )
    result = write_relayrun_checkpoint_if_enabled(
        artifact,
        write_enabled=True,
        dry_run_only=False,
    )
    preflight = result.get("checkpoint_writer_preflight", {})
    require(result.get("checkpoint_persisted") is False, result)
    require("checkpoint_path_traversal_detected" in preflight.get("blocked_reasons", []), result)
    require(not (root.parent / "unsafe-checkpoints").exists(), root)
    print("ok unsafe traversal preflight blocks checkpoint write")


def _assert_existing_file_collision(root: Path) -> None:
    checkpoint_root = root / "collision"
    artifact = build_runtime_checkpoint_dry_run_artifact(
        request_id="request-collision",
        run_id="run-collision",
        route_model="relaylm-default",
        node_statuses=[build_relayrun_node(node_name="request_received", node_status="completed")],
        checkpoint_target_root=checkpoint_root.relative_to(REPO_ROOT).as_posix(),
    )
    plan = artifact.get("checkpoint_persistence_plan")
    require(isinstance(plan, dict), artifact)
    target = REPO_ROOT / str(plan.get("target_path_preview"))
    target.parent.mkdir(parents=True)
    target.write_text("existing\n", encoding="utf-8")
    result = write_relayrun_checkpoint_if_enabled(
        artifact,
        write_enabled=True,
        dry_run_only=False,
    )
    require(result.get("checkpoint_persisted") is False, result)
    require(result.get("checkpoint_write_attempted") is True, result)
    require(target.read_text(encoding="utf-8") == "existing\n", target.read_text(encoding="utf-8"))
    require(list(target.parent.glob(".*.tmp")) == [], list(target.parent.iterdir()))
    preflight = result.get("checkpoint_writer_preflight", {})
    require("checkpoint_file_exists" in preflight.get("blocked_reasons", []), result)
    print("ok existing checkpoint collision does not overwrite")


def _assert_final_link_race_no_overwrite(root: Path) -> None:
    checkpoint_root = root / "link-race"
    artifact = build_runtime_checkpoint_dry_run_artifact(
        request_id="request-link-race",
        run_id="run-link-race",
        route_model="relaylm-default",
        node_statuses=[build_relayrun_node(node_name="request_received", node_status="completed")],
        checkpoint_target_root=checkpoint_root.relative_to(REPO_ROOT).as_posix(),
    )
    plan = artifact.get("checkpoint_persistence_plan")
    require(isinstance(plan, dict), artifact)
    target = REPO_ROOT / str(plan.get("target_path_preview"))
    original_link = relayrun_module.os.link

    def racing_link(src: object, dst: object, *args: object, **kwargs: object) -> object:
        Path(dst).write_text("raced\n", encoding="utf-8")
        return original_link(src, dst, *args, **kwargs)

    relayrun_module.os.link = racing_link
    try:
        result = write_relayrun_checkpoint_if_enabled(
            artifact,
            write_enabled=True,
            dry_run_only=False,
        )
    finally:
        relayrun_module.os.link = original_link

    require(result.get("checkpoint_persisted") is False, result)
    require(result.get("checkpoint_write_attempted") is True, result)
    require(target.read_text(encoding="utf-8") == "raced\n", target.read_text(encoding="utf-8"))
    require(list(target.parent.glob(".*.tmp")) == [], list(target.parent.iterdir()))
    preflight = result.get("checkpoint_writer_preflight", {})
    require("checkpoint_file_exists" in preflight.get("blocked_reasons", []), result)
    print("ok raced final checkpoint creation does not overwrite")

def main() -> int:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as td:
        root = Path(td)
        store = root / "base-store"
        _build_store(store)
        capture = _Capture()
        _BackendHandler.capture = capture
        server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_address[1]
            _assert_default_disabled(root, capture, port)
            _assert_enabled_dry_run(root, capture, port)
            _assert_enabled_write(root, capture, port)
            _assert_unsafe_path_direct(root)
            _assert_existing_file_collision(root)
            _assert_final_link_race_no_overwrite(root)
        finally:
            server.shutdown()
            thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
