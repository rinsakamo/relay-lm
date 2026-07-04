from __future__ import annotations

import json
import shutil
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

from relaylm.app import create_app, _relaymem_primary_recall_scope_allowed
from relaylm.relaymem_primary_recall import resolve_relaymem_character_store_root
from relaylm.relaymem_runtime_ctx import maybe_apply_relaymem_snippet_runtime_injection

from _relaylm_phase_i3_test_support import form_primary_memory

CHARACTER_ID = "default"
NAMESPACE = "character/default"
SNIPPET_SUMMARY = (
    "RelayMEM snippet runtime apply. "
    "SNIPPET_RUNTIME_APPLY_SENTINEL is bounded snippet evidence only."
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
        raw = self.rfile.read(int(self.headers.get("content-length", "0")))
        payload = json.loads(raw.decode("utf-8")) if raw else {}
        type(self).capture.add(payload)
        body = json.dumps(
            {
                "id": "chatcmpl-relaymem-snippet-runtime-apply-smoke",
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
    for relative in (
        "memory/sources/conversations",
        "memory/sources/communications",
        "memory/sources/corrections",
        "memory/mem/primary/sessions",
        "memory/mem/primary/scenes",
        "memory/mem/primary/relationships",
        "memory/mem/primary/projects",
        "memory/mem/secondary/projects",
        "memory/mem/secondary/concepts",
        "memory/mem/secondary/claims",
        "memory/mem/secondary/summaries",
        "memory/mem/secondary/relations",
    ):
        (root / relative).mkdir(parents=True, exist_ok=True)
    form_primary_memory(
        root,
        namespace=NAMESPACE,
        candidate_id="snippet_runtime_apply",
        title="RelayMEM snippet runtime apply",
        summary=SNIPPET_SUMMARY,
    )


def _configured_and_scoped_root(temp_dir: str) -> tuple[Path, Path]:
    configured_root = Path(temp_dir) / "memory-root"
    scoped_root = resolve_relaymem_character_store_root(str(configured_root), CHARACTER_ID)
    require(isinstance(scoped_root, str) and scoped_root, scoped_root)
    return configured_root, Path(scoped_root)


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


def _payload(scene_type: str = "design_talk", *, content: str = "RelayMEM snippet runtime apply") -> dict[str, Any]:
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
        with TestClient(app) as client:
            resp = client.post("/v1/chat/completions", json=payload)
            require(resp.status_code == 200, resp.text)
        require(payload == original, payload)
        lines = trace_path.read_text(encoding="utf-8").strip().splitlines()
        require(bool(lines), "trace is empty")
        metadata: dict[str, Any] | None = None
        for line in reversed(lines):
            record = json.loads(line)
            candidate = record.get("metadata") if isinstance(record, dict) else None
            if isinstance(candidate, dict) and candidate.get("event") == "backend_response":
                metadata = candidate
                break
        require(isinstance(metadata, dict), "backend_response trace record is missing")
        return capture.last(), metadata


def _snippet_context_messages(backend_payload: dict[str, Any]) -> list[tuple[int, dict[str, Any]]]:
    messages = backend_payload.get("messages")
    require(isinstance(messages, list), backend_payload)
    return [
        (index, message)
        for index, message in enumerate(messages)
        if isinstance(message, dict)
        and message.get("role") == "system"
        and isinstance(message.get("content"), str)
        and message["content"].startswith("[RelayMEM Snippet Context]")
    ]


def _metadata_context_messages(backend_payload: dict[str, Any]) -> list[dict[str, Any]]:
    messages = backend_payload.get("messages")
    require(isinstance(messages, list), backend_payload)
    return [
        message
        for message in messages
        if isinstance(message, dict)
        and message.get("role") == "system"
        and isinstance(message.get("content"), str)
        and message["content"].startswith("[RelayMEM Context]")
    ]


def _assert_default_false(root: Path, capture: _Capture, port: int) -> None:
    backend_payload, metadata = _post(
        port=port,
        store_root=root,
        payload=_payload(),
        capture=capture,
        snippet_runtime_injection_enabled=False,
        snippet_runtime_dry_run_only=True,
    )
    require(_snippet_context_messages(backend_payload) == [], backend_payload)
    result = metadata.get("runtime_snippet_injection_result")
    require(isinstance(result, dict), metadata)
    require(result["applied"] is False, result)
    require("snippet_runtime_injection_disabled" in result["blocked_reasons"], result)
    print("ok default snippet runtime injection gates keep backend metadata-only")


def _assert_all_gates_apply(root: Path, capture: _Capture, port: int) -> None:
    backend_payload, metadata = _post(
        port=port,
        store_root=root,
        payload=_payload(),
        capture=capture,
        snippet_runtime_injection_enabled=True,
        snippet_runtime_dry_run_only=False,
    )
    snippet_messages = _snippet_context_messages(backend_payload)
    require(len(snippet_messages) == 1, backend_payload)
    index, message = snippet_messages[0]
    require("SNIPPET_RUNTIME_APPLY_SENTINEL" in message["content"], message)
    require("[RelayMEM Snippet Context Candidate]" not in message["content"], message)
    messages = backend_payload["messages"]
    latest_user_index = max(
        idx for idx, item in enumerate(messages) if isinstance(item, dict) and item.get("role") == "user"
    )
    require(index < latest_user_index, backend_payload)
    require(_metadata_context_messages(backend_payload) == [], backend_payload)
    result = metadata.get("runtime_snippet_injection_result")
    require(isinstance(result, dict), metadata)
    require(result["applied"] is True, result)
    ctx_result = metadata.get("runtime_ctx_injection_result")
    require(isinstance(ctx_result, dict), metadata)
    require(ctx_result["applied"] is False, ctx_result)
    require(
        "skipped_because_snippet_runtime_injection_applied" in ctx_result["blocked_reasons"],
        ctx_result,
    )
    print("ok all snippet runtime gates insert snippet context before latest user")


def _assert_truncation_after_snippet(root: Path, capture: _Capture, port: int) -> None:
    payload = _payload(content="RelayMEM snippet runtime apply with truncation")
    payload["messages"] = [
        {"role": "user", "content": "older " * 400},
        {"role": "assistant", "content": "older answer " * 200},
        {"role": "user", "content": "RelayMEM snippet runtime apply with truncation"},
    ]
    backend_payload, metadata = _post(
        port=port,
        store_root=root,
        payload=payload,
        capture=capture,
        snippet_runtime_injection_enabled=True,
        snippet_runtime_dry_run_only=False,
        token_budget_truncation_enabled=True,
        token_budget=700,
    )
    require(_snippet_context_messages(backend_payload), backend_payload)
    messages = backend_payload.get("messages")
    require(isinstance(messages, list), backend_payload)
    require(
        all(
            not (isinstance(message, dict) and message.get("role") == "assistant")
            for message in messages
        ),
        backend_payload,
    )
    result = metadata.get("runtime_snippet_injection_result")
    require(isinstance(result, dict) and result["applied"] is True, result)
    print("ok snippet runtime injection runs before token budget truncation")


def _assert_direct_runtime_budget_guard() -> None:
    payload = {"messages": [{"role": "user", "content": "RelayMEM snippet runtime apply"}]}
    artifact = {
        "snippet_apply_decision": "eligible_but_not_applied",
        "ctx_block": None,
        "apply_allowed": False,
        "snippet_runtime_injection_plan": {
            "preview_text": (
                "[RelayMEM Snippet Context]\n"
                "---\n"
                "Snippet:\n"
                + ("strict runtime budget guard " * 80)
            ),
            "applied": False,
            "blocked_reasons": [],
        },
    }
    backend_payload, result = maybe_apply_relaymem_snippet_runtime_injection(
        payload=payload,
        relaymem_retrieval_artifact=artifact,
        ctx_block_apply_enabled=True,
        retrieval_dry_run_only=False,
        snippet_apply_enabled=True,
        snippet_dry_run_only=False,
        snippet_runtime_injection_enabled=True,
        snippet_runtime_dry_run_only=False,
        token_budget_truncation_enabled=True,
        token_budget=8,
        chars_per_token=4,
    )
    require(backend_payload == payload, backend_payload)
    require(result["applied"] is False, result)
    require(
        result["blocked_reasons"] == ["relaymem_snippet_context_would_break_token_budget"],
        result,
    )
    print("ok direct snippet runtime preserved budget guard remains strict")


def _assert_blocked_scenes_and_reference(root: Path, capture: _Capture, port: int) -> None:
    for scene_type in ("recovery", "formal_document", "medical_or_safety", "unknown"):
        backend_payload, metadata = _post(
            port=port,
            store_root=root,
            payload=_payload(scene_type=scene_type),
            capture=capture,
            snippet_runtime_injection_enabled=True,
            snippet_runtime_dry_run_only=False,
        )
        require(_snippet_context_messages(backend_payload) == [], (scene_type, backend_payload))
        result = metadata.get("runtime_snippet_injection_result")
        require(isinstance(result, dict), metadata)
        require(result["applied"] is False, result)
        require(
            any(str(reason).startswith("snippet_apply_decision:") for reason in result["blocked_reasons"]),
            result,
        )
    unresolved_payload = _payload(content="Which one was that RelayMEM snippet runtime apply")
    backend_payload, metadata = _post(
        port=port,
        store_root=root,
        payload=unresolved_payload,
        capture=capture,
        snippet_runtime_injection_enabled=True,
        snippet_runtime_dry_run_only=False,
    )
    require(_snippet_context_messages(backend_payload) == [], backend_payload)
    result = metadata.get("runtime_snippet_injection_result")
    require(isinstance(result, dict), metadata)
    require(result["applied"] is False, result)
    print("ok blocked scenes and unresolved references skip snippet runtime injection")


def _assert_incomplete_target_layout_fail_closed(
    root: Path,
    scoped_root: Path,
    capture: _Capture,
    port: int,
) -> None:
    secondary = scoped_root / "memory" / "mem" / "secondary"
    require(secondary.is_dir(), secondary)
    shutil.rmtree(secondary)
    blocked_source = scoped_root / "memory" / "sources" / "conversations" / "blocked.bin"
    blocked_source.parent.mkdir(parents=True, exist_ok=True)
    blocked_source.write_bytes(b"blocked-source")
    backend_payload, metadata = _post(
        port=port,
        store_root=root,
        payload=_payload(),
        capture=capture,
        snippet_runtime_injection_enabled=True,
        snippet_runtime_dry_run_only=False,
    )
    backend_text = json.dumps(backend_payload, ensure_ascii=False)
    require("SNIPPET_RUNTIME_APPLY_SENTINEL" not in backend_text, backend_payload)
    require(_snippet_context_messages(backend_payload) == [], backend_payload)
    require(_metadata_context_messages(backend_payload) == [], backend_payload)
    result = metadata.get("runtime_snippet_injection_result")
    require(isinstance(result, dict), metadata)
    require(result["applied"] is False, result)
    require(
        "snippet_apply_decision:blocked_no_candidates" in result["blocked_reasons"],
        result,
    )
    require(
        _relaymem_primary_recall_scope_allowed(
            {
                "fallback_reason": "memory_store_files_blocked",
                "root_present": True,
                "layout_compatibility": {
                    "target_primary_secondary_present": False,
                    "flat_store_compatibility_removed": True,
                },
            }
        )
        is False,
        "masked layout incompatibility allowed Primary recall",
    )
    print("ok incomplete target layout blocks primary recall bridge before runtime snippets")


def _assert_preview_null_blocks(root: Path, capture: _Capture, port: int) -> None:
    backend_payload, metadata = _post(
        port=port,
        store_root=root,
        payload=_payload(),
        capture=capture,
        snippet_runtime_injection_enabled=True,
        snippet_runtime_dry_run_only=False,
        snippet_apply_enabled=False,
    )
    require(_snippet_context_messages(backend_payload) == [], backend_payload)
    result = metadata.get("runtime_snippet_injection_result")
    require(isinstance(result, dict), metadata)
    require(result["applied"] is False, result)
    require("snippet_apply_disabled" in result["blocked_reasons"], result)
    print("ok snippet apply blocked or preview-null cases skip snippet runtime injection")


def main() -> int:
    capture = _Capture()
    _BackendHandler.capture = capture
    server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
    port = int(server.server_address[1])
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory() as td:
            root, scoped_root = _configured_and_scoped_root(td)
            _build_store(scoped_root)
            _assert_default_false(root, capture, port)
            _assert_all_gates_apply(root, capture, port)
            _assert_truncation_after_snippet(root, capture, port)
            _assert_direct_runtime_budget_guard()
            _assert_blocked_scenes_and_reference(root, capture, port)
            _assert_preview_null_blocks(root, capture, port)
        with tempfile.TemporaryDirectory() as td:
            root, scoped_root = _configured_and_scoped_root(td)
            _build_store(scoped_root)
            _assert_incomplete_target_layout_fail_closed(root, scoped_root, capture, port)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
