"""End-to-end functional, restart, security, and leakage smoke for Phase I-2."""
from __future__ import annotations

import json
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

from fastapi.testclient import TestClient

from relaylm.relaymem_primary_recall import resolve_relaymem_character_store_root
from relaylm.relaymem_slp_one_queued_job_runner import (
    REQUEST_SCHEMA,
    RelayMEMSLPOneQueuedJobRunnerRequest,
    execute_one_queued_relaymem_slp_primary_job,
)
from relaylm.relaymem_slp_primary_worker_source_registry import RelayMEMSLPPrimaryWorkerSourceRegistry
from relaylm.soul_lab_app import create_app as create_lab_app
from relaylm.soul_lab_observation_store import (
    OUTCOME_RECEIPT_SCHEMA,
    stable_correlation,
    utc_now,
    write_outcome_receipt,
)
from relaylm_phase6c1_primary_worker_test_support import prepare_store
from relaylm_phase_i1_two_turn_primary_recall_smoke import (
    Backend,
    CHARACTER,
    MEMORY_CANARY,
    NAMESPACE,
    QUESTION,
    payload,
    primary_pages,
    read_queued,
    require,
    visible_text,
    write_config,
)


def assert_no_leak(value: object) -> None:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True)
    for forbidden in (
        "lease_token", "claim_owner", "lineage_fingerprint", "page_digest",
        "queue_root", "protected_source", "Traceback", "api_key",
    ):
        require(forbidden not in serialized, forbidden)


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Backend)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            queue = root / "queue"
            protected = root / "protected"
            store = root / "store"
            queue.mkdir()
            protected.mkdir()
            store.mkdir()

            scoped_value = resolve_relaymem_character_store_root(str(store), CHARACTER)
            require(scoped_value is not None, "character scope")
            scoped = Path(scoped_value)
            prepare_store(scoped)

            producer_config = root / "producer.yaml"
            write_config(
                producer_config, port=int(server.server_address[1]), queue=queue,
                protected=protected, store=store, enqueue_enabled=True,
            )
            with TestClient(create_lab_app(str(producer_config)), client=("127.0.0.1", 50000)) as client:
                first = client.post(
                    "/v1/chat/completions",
                    json=payload(
                        "relaylm-default",
                        f"私の 好きな飲み物 は {MEMORY_CANARY} です。覚えてください。",
                    ),
                )
            require(first.status_code == 200, first.text)
            queued = read_queued(queue)
            request = RelayMEMSLPOneQueuedJobRunnerRequest(
                schema_version=REQUEST_SCHEMA,
                runtime_private=True,
                content_included=False,
                queued_record=dict(queued),
                source_registry=RelayMEMSLPPrimaryWorkerSourceRegistry(),
                character_id=CHARACTER,
                queue_root=str(queue),
                protected_source_root=str(protected),
                store_root=str(scoped),
                claim_owner="phase-i2-worker",
                enabled=True,
                dry_run_only=False,
                apply_enabled=True,
                lease_duration_seconds=300,
            )
            worker = execute_one_queued_relaymem_slp_primary_job(request)
            require(worker.worker_status == "terminal_succeeded", worker.to_log_dict())
            require(len(primary_pages(scoped)) == 1, primary_pages(scoped))

            recall_config = root / "recall.yaml"
            write_config(
                recall_config, port=int(server.server_address[1]), queue=queue,
                protected=protected, store=store, enqueue_enabled=False,
            )
            with Backend.lock:
                Backend.payloads.clear()
            recall_app = create_lab_app(str(recall_config))
            with TestClient(recall_app, client=("127.0.0.1", 50000)) as client:
                second = client.post(
                    "/v1/chat/completions",
                    json=payload("relaylm-default", QUESTION),
                )
                require(second.status_code == 200, second.text)
                require(MEMORY_CANARY in visible_text(second), second.json())

                base = f"/lab/api/characters/{CHARACTER}"
                query = f"namespace={NAMESPACE}"
                latest_response = client.get(f"{base}/lab/last-run?{query}")
                recent_response = client.get(f"{base}/memory/recent?{query}&limit=20")
                held_response = client.get(f"{base}/memory/held?{query}&limit=20")
                used_response = client.get(f"{base}/lab/last-run/memory/used?{query}")
                for response in (latest_response, recent_response, held_response, used_response):
                    require(response.status_code == 200, response.text)
                    require(response.headers.get("cache-control") == "no-store", response.headers)
                    assert_no_leak(response.json())

                latest = latest_response.json()
                recent = recent_response.json()
                held = held_response.json()
                used = used_response.json()
                require(latest["schema"] == "relaylm.lab.last_run.v0", latest)
                require(latest["source"] == "relaylm_runtime", latest)
                require(latest["status"] == "completed", latest)
                require(latest["used_memory_count"] == 1, latest)
                require(recent["schema"] == "relaylm.lab.memory_recent.v0", recent)
                require(len(recent["items"]) == 1, recent)
                require(MEMORY_CANARY in recent["items"][0]["bounded_summary"], recent)
                require(held["items"] == [], held)
                require(used["schema"] == "relaylm.lab.memory_used.v0", used)
                require(used["backend_bound_included"] is True, used)
                require(used["response_generation_completed"] is True, used)
                require(len(used["items"]) == 1, used)
                require(MEMORY_CANARY in used["items"][0]["injected_summary"], used)

                wrong = client.get(f"/lab/api/characters/other/memory/recent?namespace={NAMESPACE}&limit=20")
                require(wrong.status_code == 200, wrong.text)
                require(wrong.json()["items"] == [], wrong.json())
                require(MEMORY_CANARY not in wrong.text, wrong.text)

                for method in (client.post, client.put, client.patch, client.delete):
                    refused = method(f"{base}/memory/recent?{query}", json={})
                    require(refused.status_code == 405, refused.text)

                remote = TestClient(recall_app, client=("192.0.2.10", 50000))
                refused = remote.get(f"{base}/lab/last-run?{query}")
                require(refused.status_code == 403, refused.text)

            for status in ("held", "blocked"):
                write_outcome_receipt(
                    str(scoped),
                    {
                        "schema": OUTCOME_RECEIPT_SCHEMA,
                        "runtime_private": True,
                        "read_model_only": True,
                        "run_id": "phase-i2-outcome-run",
                        "job_correlation_id": stable_correlation(f"job-{status}"),
                        "namespace": NAMESPACE,
                        "turn_index": 9,
                        "outcome_status": status,
                        "worker_status": "pipeline_held" if status == "held" else "terminal_failed",
                        "pipeline_status": status,
                        "title": f"{status} title",
                        "bounded_summary": f"{status} bounded summary",
                        "observed_at": utc_now(),
                        "reason_ids": [f"phase_i2_{status}_reason"],
                    },
                )

            corrupt_dir = scoped / ".relaylm-lab-observation-v0" / "outcomes"
            (corrupt_dir / "corrupt.json").write_text("{truncated", encoding="utf-8")

            restarted = create_lab_app(str(recall_config))
            with TestClient(restarted, client=("127.0.0.1", 50000)) as client:
                base = f"/lab/api/characters/{CHARACTER}"
                query = f"namespace={NAMESPACE}"
                recent = client.get(f"{base}/memory/recent?{query}&limit=1").json()
                held = client.get(f"{base}/memory/held?{query}&limit=20").json()
                used = client.get(f"{base}/lab/last-run/memory/used?{query}").json()
                require(len(recent["items"]) == 1, recent)
                require({item["status"] for item in held["items"]} == {"held", "blocked"}, held)
                require("observation_receipt_corrupt_ignored" in held["bounded_reason_ids"], held)
                require(len(used["items"]) == 1, used)
                assert_no_leak(held)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    print("Phase I-2 real SOUL Lab observation smoke passed")


if __name__ == "__main__":
    main()
