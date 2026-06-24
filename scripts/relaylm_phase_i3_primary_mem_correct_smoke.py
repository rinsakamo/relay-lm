"""Functional and retrieval-convergence smoke for Phase I-3."""
from __future__ import annotations

import json
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from relaylm.relaymem_primary_correction import (
    apply_primary_memory_correction,
    list_primary_memory_corrections,
    preflight_primary_memory_correction,
)
from relaylm.relaymem_primary_recall import resolve_relaymem_character_store_root
from relaylm.relaymem_slp_one_queued_job_runner import (
    REQUEST_SCHEMA,
    RelayMEMSLPOneQueuedJobRunnerRequest,
    execute_one_queued_relaymem_slp_primary_job,
)
from relaylm.relaymem_slp_primary_worker_source_registry import (
    RelayMEMSLPPrimaryWorkerSourceRegistry,
)
from relaylm.soul_lab_app import create_app
from relaylm.soul_lab_observation_projection import (
    build_lab_memory_used_projection,
    build_lab_recent_memory_projection,
    resolve_lab_observation_scope,
)
from relaylm_phase6c1_primary_worker_test_support import prepare_store
from relaylm_phase_i1_two_turn_primary_recall_smoke import (
    CHARACTER,
    NAMESPACE,
    payload,
    read_queued,
    visible_text,
    write_config,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
OLD = "紅茶"
NEW = "コーヒー"
QUESTION = "好きな飲み物を教えてください。"


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
        incoming = json.loads(self.rfile.read(length).decode("utf-8"))
        with type(self).lock:
            type(self).payloads.append(incoming)
        messages = incoming.get("messages", [])
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
            answer = f"好きな飲み物は{OLD}と覚えました。"
        elif "[RelayMEM Snippet Context]" in serialized and NEW in serialized:
            answer = f"好きな飲み物は{NEW}です。"
        elif "[RelayMEM Snippet Context]" in serialized and OLD in serialized:
            answer = f"好きな飲み物は{OLD}です。"
        else:
            answer = "記憶からは確認できません。"
        body = {
            "id": "chatcmpl-phase-i3",
            "object": "chat.completion",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": answer},
                "finish_reason": "stop",
            }],
        }
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


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
            scoped_value = resolve_relaymem_character_store_root(str(store), CHARACTER)
            require(scoped_value is not None, "scope")
            scoped = Path(scoped_value)
            prepare_store(scoped)

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
            with TestClient(producer_app, client=("127.0.0.1", 50000)) as client:
                first = client.post(
                    "/v1/chat/completions",
                    json=payload(
                        "relaylm-default",
                        f"私の好きな飲み物は{OLD}です。覚えてください。",
                    ),
                )
            require(first.status_code == 200, first.text)
            queued = read_queued(queue)
            worker = execute_one_queued_relaymem_slp_primary_job(
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
                    claim_owner="phase-i3-worker",
                    enabled=True,
                    dry_run_only=False,
                    apply_enabled=True,
                    lease_duration_seconds=300,
                )
            )
            require(worker.status == "worker_completed", worker.to_log_dict())
            require(worker.worker_status == "terminal_succeeded", worker.to_log_dict())

            recall_config = root / "recall.yaml"
            write_config(
                recall_config,
                port=int(server.server_address[1]),
                queue=queue,
                protected=protected,
                store=store,
                enqueue_enabled=False,
            )
            recall_app = create_app(str(recall_config))
            scope = resolve_lab_observation_scope(
                recall_app.state.relaylm_config,
                character_id=CHARACTER,
                namespace=NAMESPACE,
            )
            recent = build_lab_recent_memory_projection(scope, limit=20)
            require(len(recent.items) == 1, recent.model_dump())
            memory = recent.items[0]
            require(memory.revision == 1, memory.model_dump())
            memory_id = memory.memory_id

            with Backend.lock:
                Backend.payloads.clear()
            with TestClient(recall_app, client=("127.0.0.1", 50000)) as client:
                before = client.post(
                    "/v1/chat/completions",
                    json=payload("relaylm-default", QUESTION),
                )
            require(before.status_code == 200, before.text)
            require(OLD in visible_text(before), before.json())
            used_before = build_lab_memory_used_projection(scope)
            require(len(used_before.items) == 1, used_before.model_dump())
            require(used_before.items[0].injected_summary.find(OLD) >= 0, used_before.model_dump())

            preflight = preflight_primary_memory_correction(
                store_root=str(scoped),
                character_id=CHARACTER,
                namespace=NAMESPACE,
                memory_id=memory_id,
                expected_revision=1,
                corrected_title="好きな飲み物",
                corrected_summary=f"好きな飲み物は{NEW}です。",
                reason="ユーザーが記憶内容の誤りを明示的に訂正したため",
                operation_id="phase-i3-correct-op-1",
            )
            require(preflight["status"] == "ready", preflight)
            require(preflight["diff"]["summary_changed"] is True, preflight)
            applied = apply_primary_memory_correction(
                store_root=str(scoped),
                character_id=CHARACTER,
                namespace=NAMESPACE,
                memory_id=memory_id,
                expected_revision=1,
                operation_id="phase-i3-correct-op-1",
                apply_token=preflight["apply_token"],
            )
            require(applied["result_revision"] == 2, applied)
            require(applied["reconciled"] is True, applied)

            replay = apply_primary_memory_correction(
                store_root=str(scoped),
                character_id=CHARACTER,
                namespace=NAMESPACE,
                memory_id=memory_id,
                expected_revision=1,
                operation_id="phase-i3-correct-op-1",
                apply_token=preflight["apply_token"],
            )
            require(replay["idempotent_replay"] is True, replay)
            require(replay["correction_id"] == applied["correction_id"], replay)

            history = list_primary_memory_corrections(
                store_root=str(scoped),
                namespace=NAMESPACE,
                memory_id=memory_id,
            )
            require(history["current_revision"] == 2, history)
            require(history["correction_count"] == 1, history)
            require(len(list(scoped.glob("memory/mem/primary/*/*.md"))) == 2, "revision pages")

            current = build_lab_recent_memory_projection(scope, limit=20)
            require(len(current.items) == 1, current.model_dump())
            require(current.items[0].memory_id == memory_id, current.model_dump())
            require(current.items[0].revision == 2, current.model_dump())
            require(NEW in current.items[0].bounded_summary, current.model_dump())
            require(OLD not in current.items[0].bounded_summary, current.model_dump())

            # Historical evidence remains the exact old injected representation.
            historical = build_lab_memory_used_projection(scope)
            require(OLD in historical.items[0].injected_summary, historical.model_dump())
            require(NEW in str(historical.items[0].current_summary), historical.model_dump())
            require(historical.items[0].representation_changed is True, historical.model_dump())

            with Backend.lock:
                Backend.payloads.clear()
            restarted_app = create_app(str(recall_config))
            with TestClient(restarted_app, client=("127.0.0.1", 50000)) as client:
                after = client.post(
                    "/v1/chat/completions",
                    json=payload("relaylm-default", QUESTION),
                )
            require(after.status_code == 200, after.text)
            require(NEW in visible_text(after), after.json())
            require(OLD not in visible_text(after), after.json())
            with Backend.lock:
                backend_payload = Backend.payloads[-1]
            serialized = json.dumps(backend_payload.get("messages"), ensure_ascii=False)
            require(serialized.count("[RelayMEM Snippet Context]") == 1, serialized)
            require(NEW in serialized, "corrected memory missing")
            require(OLD not in serialized, "superseded memory leaked")
            for forbidden in (
                "correction_id", "prior_revision", "result_revision", "candidate_digest",
                "token_digest", "ユーザーが記憶内容の誤りを明示的に訂正したため",
            ):
                require(forbidden not in serialized, forbidden)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    print("Phase I-3 Primary MEM Correct functional smoke passed")


if __name__ == "__main__":
    main()
