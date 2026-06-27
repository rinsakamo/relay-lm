"""Phase I-4F end-to-end Forget product completion validation smoke."""
from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from _relaylm_phase_i3_test_support import form_primary_memory, require, write_config
from relaylm.relaymem_primary_current_state import resolve_primary_current_state
from relaylm.relaymem_primary_recall import resolve_relaymem_character_store_root
from relaylm.soul_lab_app import create_app
from relaylm.soul_lab_observation_store import (
    RUN_RECEIPT_SCHEMA,
    USED_RECEIPT_SCHEMA,
    write_run_receipt,
    write_used_receipt,
)
from relaylm_phase_i1_two_turn_primary_recall_smoke import CHARACTER, NAMESPACE
from relaylm_phase_i4d_fresh_conversation_smoke import main as fresh_conversation_main

REPO_ROOT = Path(__file__).resolve().parents[1]
SUMMARY = "I4F_PRODUCT_FORGET_MEMORY_CONTENT_CANARY"
REASON = "I4F_PRODUCT_FORGET_REASON_CANARY"
NOW = datetime(2026, 6, 27, 0, 0, tzinfo=timezone.utc).isoformat()


def preflight_body(revision: int, operation_id: str) -> dict[str, object]:
    return {
        "schema": "relaylm.lab.memory_forget_preflight_request.v0",
        "expected_revision": revision,
        "expected_lifecycle_state": "active",
        "reason": REASON,
        "operation_id": operation_id,
    }


def apply_body(revision: int, operation_id: str, token: str) -> dict[str, object]:
    return {
        "schema": "relaylm.lab.memory_forget_apply_request.v0",
        "expected_revision": revision,
        "expected_lifecycle_state": "active",
        "reason": REASON,
        "operation_id": operation_id,
        "apply_token": token,
    }


def assert_no_private_leak(text: str, *tokens: str) -> None:
    for forbidden in (
        REASON,
        "reason_digest",
        "token_digest",
        "token_claims",
        "physical_id",
        "store_root",
        "filesystem",
        "traceback",
        "tombstone_content",
        *tokens,
    ):
        if forbidden:
            require(forbidden not in text, forbidden)


def write_used_evidence(store_root: Path, memory_id: str) -> None:
    require(
        write_run_receipt(
            str(store_root),
            {
                "schema": RUN_RECEIPT_SCHEMA,
                "runtime_private": True,
                "read_model_only": True,
                "request_id": "i4f-request",
                "run_id": "i4f-run",
                "character_id": CHARACTER,
                "namespace": NAMESPACE,
                "started_at": NOW,
                "completed_at": NOW,
                "duration_ms": 0,
                "response_mode": "non_stream",
                "http_status": 200,
                "relayrun_status": "completed",
                "relayctx_repack_status": "applied",
                "relayctx_unpack_status": "completed",
                "slp_status": "disabled",
                "recovery_required": False,
                "reason_ids": [],
            },
        ),
        "run receipt",
    )
    require(
        write_used_receipt(
            str(store_root),
            {
                "schema": USED_RECEIPT_SCHEMA,
                "runtime_private": True,
                "read_model_only": True,
                "request_id": "i4f-request",
                "run_id": "i4f-run",
                "character_id": CHARACTER,
                "namespace": NAMESPACE,
                "retrieval_attempted": True,
                "candidate_discovered": True,
                "selected": True,
                "relayctx_injection_performed": True,
                "backend_bound_included": True,
                "items": [{"memory_id": memory_id, "injected_summary": SUMMARY, "source_kind": "preference"}],
                "captured_at": NOW,
                "reason_ids": [],
            },
        ),
        "used receipt",
    )


def lab_preflight_apply_refresh_history() -> None:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
        root = Path(directory)
        queue = root / "queue"
        protected = root / "protected"
        store = root / "store"
        queue.mkdir(); protected.mkdir(); store.mkdir()
        scoped_value = resolve_relaymem_character_store_root(str(store), CHARACTER)
        require(scoped_value is not None, "scope")
        scoped = Path(scoped_value)
        memory_id = form_primary_memory(scoped, namespace=NAMESPACE, candidate_id="i4f-product-forget", title="forget product target", summary=SUMMARY)
        write_used_evidence(scoped, memory_id)
        config_path = root / "config.yaml"
        write_config(config_path, port=9, queue=queue, protected=protected, store=store, enqueue_enabled=False)

        app = create_app(str(config_path))
        base = f"/lab/api/characters/{CHARACTER}/memory/{memory_id}"
        query = f"?namespace={NAMESPACE}"
        with TestClient(app, client=("127.0.0.1", 50000)) as client:
            preflight = client.post(f"{base}/forget/preflight{query}", json=preflight_body(1, "i4f-product-forget"))
            require(preflight.status_code == 200, preflight.text)
            require(preflight.headers["cache-control"] == "no-store", preflight.headers)
            token = preflight.json()["apply_token"]
            require(preflight.json()["effects"]["physical_deletion"] is False, preflight.json())
            assert_no_private_leak(preflight.text)

            applied = client.post(f"{base}/forget{query}", json=apply_body(1, "i4f-product-forget", token))
            require(applied.status_code == 200, applied.text)
            receipt = applied.json()
            require(receipt["status"] == "applied", receipt)
            require(receipt["lifecycle_state"] == "hidden", receipt)
            require(receipt["retrieval_eligible"] is False, receipt)
            assert_no_private_leak(applied.text, token)

        state = resolve_primary_current_state(scoped, namespace=NAMESPACE, memory_id=memory_id)
        require(state.lifecycle_state == "hidden", state)
        require(state.mutation_state == "none", state)
        require(state.retrieval_eligible is False, state)

        refreshed = create_app(str(config_path))
        with TestClient(refreshed, client=("127.0.0.1", 50001)) as client:
            history = client.get(f"{base}/forget-history{query}")
            require(history.status_code == 200, history.text)
            require(history.json()["current_lifecycle_state"] == "hidden", history.json())
            assert_no_private_leak(history.text, token)

            lifecycle = client.get(f"/lab/api/characters/{CHARACTER}/lab/last-run/memory/used-lifecycle{query}")
            require(lifecycle.status_code == 200, lifecycle.text)
            serialized = json.dumps(lifecycle.json(), ensure_ascii=False)
            require(SUMMARY in serialized, serialized)
            require('"current_lifecycle_state":"hidden"' in serialized.replace(" ", ""), serialized)
            require('"current_summary":null' in serialized.replace(" ", ""), serialized)
            assert_no_private_leak(lifecycle.text, token)


def main() -> None:
    lab_preflight_apply_refresh_history()
    fresh_conversation_main()
    print("Phase I-4F Forget product validation smoke passed")


if __name__ == "__main__":
    main()
