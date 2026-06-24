"""Ordinary two-turn Primary MEM recall and restart smoke for Phase I-1."""
from __future__ import annotations

import json
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import yaml
from fastapi.testclient import TestClient

from relaylm.app import create_app
from relaylm.relaymem_primary_recall import resolve_relaymem_character_store_root
from relaylm.relaymem_slp_one_queued_job_runner import (
    REQUEST_SCHEMA,
    RelayMEMSLPOneQueuedJobRunnerRequest,
    execute_one_queued_relaymem_slp_primary_job,
)
from relaylm.relaymem_slp_primary_worker_source_registry import (
    RelayMEMSLPPrimaryWorkerSourceRegistry,
)
from relaylm_phase6c1_primary_worker_test_support import prepare_store

REPO_ROOT = Path(__file__).resolve().parents[1]
CHARACTER = "default"
OTHER_CHARACTER = "other"
NAMESPACE = "phase-i1-recall"
OTHER_NAMESPACE = "phase-i1-other"
MEMORY_CANARY = "紅茶"
QUESTION = "好きな飲み物 を教えてください。"


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


class Backend(BaseHTTPRequestHandler):
    payloads: list[dict[str, Any]] = []
    lock = threading.Lock()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/chat/completions":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        with type(self).lock:
            type(self).payloads.append(payload)
        messages = payload.get("messages", [])
        latest_user = next(
            (
                str(item.get("content", ""))
                for item in reversed(messages)
                if isinstance(item, dict) and item.get("role") == "user"
            ),
            "",
        )
        serialized = json.dumps(messages, ensure_ascii=False)
        if "覚えて" in latest_user:
            answer = f"好きな飲み物 は {MEMORY_CANARY} と覚えました。"
        elif (
            "[RelayMEM Snippet Context]" in serialized
            and MEMORY_CANARY in serialized
        ):
            answer = f"好きな飲み物は{MEMORY_CANARY}です。"
        else:
            answer = "記憶からは確認できません。"
        body = {
            "id": "chatcmpl-phase-i1",
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": answer},
                    "finish_reason": "stop",
                }
            ],
        }
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def write_config(
    path: Path,
    *,
    port: int,
    queue: Path,
    protected: Path,
    store: Path,
    enqueue_enabled: bool,
) -> None:
    cfg = yaml.safe_load(
        (REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8")
    )
    cfg["trace"] = {"enabled": False, "path": None}
    cfg["backends"]["local_backend"]["base_url"] = (
        f"http://127.0.0.1:{port}/v1"
    )
    base_route = cfg["model_routes"]["relaylm-default"]
    base_route.update(
        {
            "mode": "memory_light",
            "character_id": CHARACTER,
            "memory_namespace": NAMESPACE,
            "session_id": "phase-i1-session",
        }
    )
    cfg["characters"][OTHER_CHARACTER] = dict(cfg["characters"][CHARACTER])
    cfg["model_routes"]["relaylm-other-character"] = {
        **base_route,
        "character_id": OTHER_CHARACTER,
        "memory_namespace": NAMESPACE,
    }
    cfg["model_routes"]["relaylm-other-namespace"] = {
        **base_route,
        "character_id": CHARACTER,
        "memory_namespace": OTHER_NAMESPACE,
    }
    cfg["relayemo_enabled"] = False
    cfg["relaymem_slp_runtime_enqueue_enabled"] = enqueue_enabled
    cfg["relaymem_slp_runtime_enqueue_dry_run_only"] = not enqueue_enabled
    cfg["relaymem_slp_runtime_enqueue_apply_enabled"] = enqueue_enabled
    cfg["relaymem_slp_queue_root"] = str(queue.resolve())
    cfg["relaymem_slp_protected_source_root"] = str(protected.resolve())
    cfg["memory"].update(
        {
            "root_path": str(store.resolve()),
            "store_enabled": True,
            "retrieval_dry_run_only": False,
            "ctx_block_apply_enabled": True,
            "snippet_extraction_enabled": True,
            "snippet_dry_run_only": False,
            "snippet_apply_enabled": True,
            "snippet_runtime_injection_enabled": True,
            "snippet_runtime_dry_run_only": False,
            "candidate_limit": 8,
            "max_snippet_candidates": 3,
            "max_snippet_chars": 512,
            "snippet_budget": 512,
            "token_budget_truncation_enabled": False,
        }
    )
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")


def payload(
    model: str,
    text: str,
    *,
    scene_type: str = "design_talk",
) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [{"role": "user", "content": text}],
        "stream": False,
        "metadata": {
            "scene_state": {
                "schema_version": "relayscn.scene_state.v0",
                "scene_type": scene_type,
                "confidence": 0.99,
                "stability": 0.99,
                "signals": [],
            }
        },
    }


def read_queued(queue: Path) -> dict[str, object]:
    files = list(queue.glob("slp-dispatch-v0-*.json"))
    require(len(files) == 1, files)
    value = json.loads(files[0].read_text(encoding="utf-8"))
    require(type(value) is dict and value.get("state") == "queued", value)
    return value


def visible_text(response: object) -> str:
    body = response.json()
    return str(body["choices"][0]["message"]["content"])


def primary_pages(scoped: Path) -> list[Path]:
    return sorted(scoped.glob("memory/mem/primary/*/*.md"))


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Backend)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
            root = Path(directory)
            queue = root / "queue"
            protected = root / "protected"
            store = root / "store"
            queue.mkdir()
            protected.mkdir()
            store.mkdir()

            scoped_value = resolve_relaymem_character_store_root(
                str(store),
                CHARACTER,
            )
            other_scoped_value = resolve_relaymem_character_store_root(
                str(store),
                OTHER_CHARACTER,
            )
            require(
                scoped_value is not None and other_scoped_value is not None,
                "character scope",
            )
            scoped = Path(scoped_value)
            other_scoped = Path(other_scoped_value)
            prepare_store(scoped)
            prepare_store(other_scoped)

            producer_config = root / "producer.yaml"
            write_config(
                producer_config,
                port=int(server.server_address[1]),
                queue=queue,
                protected=protected,
                store=store,
                enqueue_enabled=True,
            )
            producer_app = create_app(str(producer_config))
            with TestClient(producer_app) as client:
                first = client.post(
                    "/v1/chat/completions",
                    json=payload(
                        "relaylm-default",
                        f"私の 好きな飲み物 は {MEMORY_CANARY} です。覚えてください。",
                    ),
                )
            require(first.status_code == 200, first.text)
            require(MEMORY_CANARY in visible_text(first), first.json())
            queued = read_queued(queue)

            # Simulate producer/process restart: C2 has no hot registry state.
            result = execute_one_queued_relaymem_slp_primary_job(
                RelayMEMSLPOneQueuedJobRunnerRequest(
                    schema_version=REQUEST_SCHEMA,
                    runtime_private=True,
                    content_included=False,
                    queued_record=dict(queued),
                    source_registry=RelayMEMSLPPrimaryWorkerSourceRegistry(),
                    character_id=CHARACTER,
                    queue_root=str(queue),
                    protected_source_root=str(protected),
                    store_root=str(scoped),
                    claim_owner="phase-i1-worker",
                    enabled=True,
                    dry_run_only=False,
                    apply_enabled=True,
                    lease_duration_seconds=300,
                )
            )
            require(result.status == "worker_completed", result.to_log_dict())
            require(result.worker_status == "terminal_succeeded", result.to_log_dict())
            require(result.restart_rehydrated, result.to_log_dict())
            pages_after_success = primary_pages(scoped)
            require(len(pages_after_success) == 1, pages_after_success)

            # Re-presenting the duplicate dispatch cannot create a second page.
            duplicate = execute_one_queued_relaymem_slp_primary_job(
                RelayMEMSLPOneQueuedJobRunnerRequest(
                    schema_version=REQUEST_SCHEMA,
                    runtime_private=True,
                    content_included=False,
                    queued_record=dict(queued),
                    source_registry=RelayMEMSLPPrimaryWorkerSourceRegistry(),
                    character_id=CHARACTER,
                    queue_root=str(queue),
                    protected_source_root=str(protected),
                    store_root=str(scoped),
                    claim_owner="phase-i1-duplicate-worker",
                    enabled=True,
                    dry_run_only=False,
                    apply_enabled=True,
                    lease_duration_seconds=300,
                )
            )
            require(duplicate.worker_invoked is False, duplicate.to_log_dict())
            require(primary_pages(scoped) == pages_after_success, primary_pages(scoped))

            recall_config = root / "recall.yaml"
            write_config(
                recall_config,
                port=int(server.server_address[1]),
                queue=queue,
                protected=protected,
                store=store,
                enqueue_enabled=False,
            )
            with Backend.lock:
                Backend.payloads.clear()

            # A fresh request runtime reads only the durable store.
            recall_app = create_app(str(recall_config))
            with TestClient(recall_app) as client:
                second = client.post(
                    "/v1/chat/completions",
                    json=payload("relaylm-default", QUESTION),
                )
                wrong_character = client.post(
                    "/v1/chat/completions",
                    json=payload("relaylm-other-character", QUESTION),
                )
                wrong_namespace = client.post(
                    "/v1/chat/completions",
                    json=payload("relaylm-other-namespace", QUESTION),
                )
                policy_block = client.post(
                    "/v1/chat/completions",
                    json=payload(
                        "relaylm-default",
                        QUESTION,
                        scene_type="formal_document",
                    ),
                )

            require(second.status_code == 200, second.text)
            require(MEMORY_CANARY in visible_text(second), second.json())
            for blocked in (wrong_character, wrong_namespace, policy_block):
                require(blocked.status_code == 200, blocked.text)
                require(
                    visible_text(blocked) == "記憶からは確認できません。",
                    blocked.json(),
                )

            with Backend.lock:
                payloads = list(Backend.payloads)
            require(len(payloads) == 4, len(payloads))
            serialized = [
                json.dumps(item.get("messages"), ensure_ascii=False)
                for item in payloads
            ]
            require(
                "[RelayMEM Snippet Context]" in serialized[0],
                "missing injected context",
            )
            require(MEMORY_CANARY in serialized[0], "missing memory evidence")
            for blocked_payload in serialized[1:]:
                require(
                    "[RelayMEM Snippet Context]" not in blocked_payload,
                    "scope/policy leak",
                )
                require(MEMORY_CANARY not in blocked_payload, "memory content leak")
            for forbidden in (
                "slp-dispatch-v0:",
                "lineage_fingerprint",
                "idempotency_key",
                "page_digest",
                "retry_not_before",
            ):
                require(forbidden not in serialized[0], forbidden)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    print("Phase I-1 two-turn Primary MEM recall smoke passed")


if __name__ == "__main__":
    main()
