"""Fresh ordinary request proof that a forgotten Primary never reaches backend."""
from __future__ import annotations

import json
import tempfile
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import yaml
from fastapi.testclient import TestClient

from _relaylm_phase_i3_test_support import form_primary_memory, require
from relaylm.app import create_app
from relaylm.relaymem_primary_forget import (
    apply_primary_memory_forget,
    preflight_primary_memory_forget,
)
from relaylm.relaymem_primary_recall import resolve_relaymem_character_store_root
from relaylm_phase6c1_primary_worker_test_support import prepare_store

REPO_ROOT = Path(__file__).resolve().parents[1]
CHARACTER = "default"
NAMESPACE = "phase-i4d-fresh"
CANARY = "I4D_FORGOTTEN_BACKEND_CANARY"
NOW = datetime(2026, 6, 27, 0, 0, tzinfo=timezone.utc)


class Backend(BaseHTTPRequestHandler):
    payloads: list[dict[str, Any]] = []
    lock = threading.Lock()

    def log_message(self, format: str, *args: object) -> None:
        return

    def do_POST(self) -> None:
        raw = self.rfile.read(int(self.headers.get("content-length", "0")))
        payload = json.loads(raw.decode("utf-8"))
        with type(self).lock:
            type(self).payloads.append(payload)
        body = json.dumps({
            "id": "chatcmpl-i4d",
            "object": "chat.completion",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}}],
        }).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def write_config(path: Path, *, port: int, store: Path) -> None:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    cfg["trace"] = {"enabled": False, "path": None}
    cfg["backends"]["local_backend"]["base_url"] = f"http://127.0.0.1:{port}/v1"
    cfg["model_routes"]["relaylm-default"].update({
        "mode": "memory_light", "character_id": CHARACTER,
        "memory_namespace": NAMESPACE, "session_id": "phase-i4d-fresh-session",
    })
    cfg["relayemo_enabled"] = False
    cfg["relaymem_slp_runtime_enqueue_enabled"] = False
    cfg["relaymem_slp_runtime_enqueue_dry_run_only"] = True
    cfg["relaymem_slp_runtime_enqueue_apply_enabled"] = False
    cfg["memory"].update({
        "root_path": str(store.resolve()), "store_enabled": True,
        "retrieval_dry_run_only": False, "ctx_block_apply_enabled": True,
        "snippet_extraction_enabled": True, "snippet_dry_run_only": False,
        "snippet_apply_enabled": True, "snippet_runtime_injection_enabled": True,
        "snippet_runtime_dry_run_only": False, "candidate_limit": 8,
        "max_snippet_candidates": 3, "max_snippet_chars": 512,
        "snippet_budget": 512, "token_budget_truncation_enabled": False,
    })
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")


def request(client: TestClient):
    return client.post("/v1/chat/completions", json={
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": "好きな飲み物 を教えてください。"}],
        "stream": False,
        "metadata": {"scene_state": {
            "schema_version": "relayscn.scene_state.v0", "scene_type": "design_talk",
            "confidence": 0.99, "stability": 0.99, "signals": [],
        }},
    })


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Backend)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
            root = Path(directory)
            store = root / "store"
            store.mkdir()
            scoped_value = resolve_relaymem_character_store_root(str(store), CHARACTER)
            require(scoped_value is not None, "scope")
            scoped = Path(scoped_value)
            prepare_store(scoped)
            memory_id = form_primary_memory(
                scoped, namespace=NAMESPACE, candidate_id="phase-i4d-fresh-primary",
                title="好きな飲み物", summary=f"好きな飲み物は紅茶です。{CANARY}",
            )
            cfg = root / "config.yaml"
            write_config(cfg, port=int(server.server_address[1]), store=store)

            with TestClient(create_app(str(cfg))) as client:
                first = request(client)
            require(first.status_code == 200, first.text)
            before = json.dumps(Backend.payloads[-1]["messages"], ensure_ascii=False)
            require(CANARY in before and "[RelayMEM Snippet Context]" in before, before)

            preflight = preflight_primary_memory_forget(
                store_root=str(scoped), character_id=CHARACTER, namespace=NAMESPACE,
                memory_id=memory_id, expected_revision=1,
                expected_lifecycle_state="active",
                reason="I4D fresh conversation forget",
                operation_id="i4d-fresh-forget", now=NOW,
            )
            apply_primary_memory_forget(
                store_root=str(scoped), character_id=CHARACTER, namespace=NAMESPACE,
                memory_id=memory_id, expected_revision=1,
                expected_lifecycle_state="active",
                reason="I4D fresh conversation forget",
                operation_id="i4d-fresh-forget",
                apply_token=str(preflight["apply_token"]), now=NOW,
            )
            with Backend.lock:
                Backend.payloads.clear()

            with TestClient(create_app(str(cfg))) as client:
                second = request(client)
            require(second.status_code == 200, second.text)
            after = json.dumps(Backend.payloads[-1]["messages"], ensure_ascii=False)
            require(CANARY not in after, after)
            require("[RelayMEM Snippet Context]" not in after, after)
            require("I4D fresh conversation forget" not in after, after)
            require(str(preflight["apply_token"]) not in after, after)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    print("Phase I-4D fresh-conversation backend exclusion smoke passed")


if __name__ == "__main__":
    main()
