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
                "id": "chatcmpl-relaymem-runtime-payload-diff-smoke",
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
        "# RelayMEM\nPAYLOAD_DIFF_SNIPPET_SENTINEL is bounded snippet evidence only.\n",
        encoding="utf-8",
    )


def _write_config(
    path: Path,
    *,
    port: int,
    trace_path: Path,
    store_root: Path,
    ctx_block_apply_enabled: bool = True,
    retrieval_dry_run_only: bool = False,
    snippet_apply_enabled: bool = True,
    snippet_dry_run_only: bool = False,
    snippet_runtime_injection_enabled: bool = False,
    snippet_runtime_dry_run_only: bool = True,
    token_budget_truncation_enabled: bool = False,
    token_budget: int | None = None,
    token_budget_hint: int = 800,
) -> None:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    cfg["backends"]["local_backend"]["base_url"] = f"http://127.0.0.1:{port}/v1"
    cfg["trace"] = {"enabled": True, "path": str(trace_path)}
    cfg["model_routes"]["relaylm-default"]["mode"] = "pass_through"
    cfg["memory"].update(
        {
            "root_path": str(store_root),
            "store_enabled": True,
            "retrieval_dry_run_only": retrieval_dry_run_only,
            "ctx_block_apply_enabled": ctx_block_apply_enabled,
            "snippet_extraction_enabled": True,
            "snippet_dry_run_only": snippet_dry_run_only,
            "snippet_apply_enabled": snippet_apply_enabled,
            "snippet_runtime_injection_enabled": snippet_runtime_injection_enabled,
            "snippet_runtime_dry_run_only": snippet_runtime_dry_run_only,
            "snippet_budget": 512,
            "max_snippet_chars": 160,
            "max_snippet_candidates": 3,
            "candidate_limit": 3,
            "token_budget_hint": token_budget_hint,
            "token_budget_truncation_enabled": token_budget_truncation_enabled,
        }
    )
    if token_budget is not None:
        cfg["memory"]["token_budget"] = token_budget
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")


def _payload(
    scene_type: str = "design_talk",
    *,
    content: str = "RelayMEM payload diff candidate",
) -> dict[str, Any]:
    return {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": content}],
        "metadata": {"scene_state": {"scene_type": scene_type}},
        "stream": False,
    }


def _post(
    *,
    port: int,
    store_root: Path,
    payload: dict[str, Any],
    capture: _Capture,
    **config_kwargs: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    with tempfile.TemporaryDirectory() as td:
        trace_path = Path(td) / "trace.jsonl"
        cfg_path = Path(td) / "cfg.yaml"
        _write_config(
            cfg_path,
            port=port,
            trace_path=trace_path,
            store_root=store_root,
            **config_kwargs,
        )
        app = create_app(str(cfg_path))
        original = json.loads(json.dumps(payload))
        before_count = capture.count()
        with TestClient(app) as client:
            resp = client.post("/v1/chat/completions", json=payload)
            require(resp.status_code == 200, resp.text)
        after_count = capture.count()
        require(after_count == before_count + 1, (before_count, after_count, payload))
        require(payload == original, payload)
        record = json.loads(trace_path.read_text(encoding="utf-8").strip().splitlines()[-1])
        metadata = record.get("metadata", {})
        require(isinstance(metadata, dict), record)
        return capture.get(before_count), metadata


def _messages(backend_payload: dict[str, Any]) -> list[dict[str, Any]]:
    messages = backend_payload.get("messages")
    require(isinstance(messages, list), backend_payload)
    require(all(isinstance(message, dict) for message in messages), backend_payload)
    return messages


def _heading_indexes(backend_payload: dict[str, Any], heading: str) -> list[int]:
    return [
        index
        for index, message in enumerate(_messages(backend_payload))
        if message.get("role") == "system"
        and isinstance(message.get("content"), str)
        and message["content"].startswith(heading)
    ]


def _latest_user_index(backend_payload: dict[str, Any]) -> int:
    indexes = [
        index
        for index, message in enumerate(_messages(backend_payload))
        if message.get("role") == "user"
    ]
    require(bool(indexes), backend_payload)
    return indexes[-1]


def _summary(case_name: str, backend_payload: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    messages = _messages(backend_payload)
    snippet_indexes = _heading_indexes(backend_payload, "[RelayMEM Snippet Context]")
    metadata_indexes = _heading_indexes(backend_payload, "[RelayMEM Context]")
    snippet_result = metadata.get("runtime_snippet_injection_result")
    ctx_result = metadata.get("runtime_ctx_injection_result")
    truncation = metadata.get("token_budget_truncation")
    require(isinstance(snippet_result, dict), metadata)
    require(isinstance(ctx_result, dict), metadata)
    summary = {
        "case": case_name,
        "backend_message_count": len(messages),
        "inserted_headings": [
            str(message.get("content", "")).splitlines()[0]
            for message in messages
            if message.get("role") == "system" and isinstance(message.get("content"), str)
        ],
        "snippet_context_applied": bool(snippet_indexes),
        "metadata_context_applied": bool(metadata_indexes),
        "runtime_snippet_injection_result.applied": snippet_result.get("applied"),
        "runtime_ctx_injection_result.applied": ctx_result.get("applied"),
        "token_budget_truncation.applied": (
            truncation.get("applied") if isinstance(truncation, dict) else None
        ),
        "trace_metadata_keys": sorted(metadata.keys()),
    }
    print("payload-diff-summary " + json.dumps(summary, sort_keys=True))
    return summary


def _assert_metadata_only_case(root: Path, capture: _Capture, port: int) -> None:
    backend_payload, metadata = _post(
        port=port,
        store_root=root,
        payload=_payload(),
        capture=capture,
        snippet_runtime_injection_enabled=False,
        snippet_runtime_dry_run_only=True,
    )
    summary = _summary("metadata_only_default", backend_payload, metadata)
    metadata_indexes = _heading_indexes(backend_payload, "[RelayMEM Context]")
    snippet_indexes = _heading_indexes(backend_payload, "[RelayMEM Snippet Context]")
    backend_text = json.dumps(backend_payload, ensure_ascii=False)
    require("PAYLOAD_DIFF_SNIPPET_SENTINEL" not in backend_text, backend_payload)
    require(len(metadata_indexes) == 1, backend_payload)
    require(len(snippet_indexes) == 0, backend_payload)
    require(summary["snippet_context_applied"] is False, summary)
    require(summary["metadata_context_applied"] is True, summary)
    require(summary["runtime_snippet_injection_result.applied"] is False, summary)
    require(summary["runtime_ctx_injection_result.applied"] is True, summary)


def _assert_snippet_enabled_case(root: Path, capture: _Capture, port: int) -> None:
    backend_payload, metadata = _post(
        port=port,
        store_root=root,
        payload=_payload(),
        capture=capture,
        snippet_runtime_injection_enabled=True,
        snippet_runtime_dry_run_only=False,
    )
    summary = _summary("snippet_runtime_enabled", backend_payload, metadata)
    snippet_indexes = _heading_indexes(backend_payload, "[RelayMEM Snippet Context]")
    require(len(snippet_indexes) == 1, backend_payload)
    require(snippet_indexes[0] == _latest_user_index(backend_payload) - 1, backend_payload)
    backend_text = json.dumps(backend_payload, ensure_ascii=False)
    require("PAYLOAD_DIFF_SNIPPET_SENTINEL" in backend_text, backend_payload)
    require(summary["snippet_context_applied"] is True, summary)
    require(summary["metadata_context_applied"] is False, summary)
    require(summary["runtime_snippet_injection_result.applied"] is True, summary)
    require(summary["runtime_ctx_injection_result.applied"] is False, summary)


def _assert_recovery_safety(root: Path, capture: _Capture, port: int) -> None:
    backend_payload, metadata = _post(
        port=port,
        store_root=root,
        payload=_payload(scene_type="recovery"),
        capture=capture,
        snippet_runtime_injection_enabled=True,
        snippet_runtime_dry_run_only=False,
    )
    summary = _summary("safety_recovery_scene", backend_payload, metadata)
    require(summary["snippet_context_applied"] is False, summary)
    require(summary["runtime_snippet_injection_result.applied"] is False, summary)


def _assert_unresolved_reference_safety(root: Path, capture: _Capture, port: int) -> None:
    backend_payload, metadata = _post(
        port=port,
        store_root=root,
        payload=_payload(content="Which one was that RelayMEM payload diff candidate"),
        capture=capture,
        snippet_runtime_injection_enabled=True,
        snippet_runtime_dry_run_only=False,
    )
    summary = _summary("safety_unresolved_reference", backend_payload, metadata)
    require(summary["snippet_context_applied"] is False, summary)
    require(summary["runtime_snippet_injection_result.applied"] is False, summary)


def _assert_preserved_budget_safety(root: Path, capture: _Capture, port: int) -> None:
    backend_payload, metadata = _post(
        port=port,
        store_root=root,
        payload=_payload(content="RelayMEM payload diff preserved budget"),
        capture=capture,
        snippet_runtime_injection_enabled=True,
        snippet_runtime_dry_run_only=False,
        token_budget_truncation_enabled=True,
        token_budget=25,
    )
    summary = _summary("safety_preserved_budget_overflow", backend_payload, metadata)
    backend_text = json.dumps(backend_payload, ensure_ascii=False)
    require("PAYLOAD_DIFF_SNIPPET_SENTINEL" not in backend_text, backend_payload)
    require(summary["snippet_context_applied"] is False, summary)
    snippet_result = metadata["runtime_snippet_injection_result"]
    require(
        "relaymem_snippet_context_would_break_token_budget"
        in snippet_result.get("blocked_reasons", []),
        snippet_result,
    )


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
            _assert_metadata_only_case(root, capture, port)
            _assert_snippet_enabled_case(root, capture, port)
            _assert_recovery_safety(root, capture, port)
            _assert_unresolved_reference_safety(root, capture, port)
            _assert_preserved_budget_safety(root, capture, port)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
