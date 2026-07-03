"""Phase I-4E loopback Forget API functional smoke."""
from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from _relaylm_phase_i3_test_support import form_primary_memory, require, write_config
from relaylm.relaymem_primary_recall import resolve_relaymem_character_store_root
from relaylm.soul_lab_app import create_app
from relaylm.soul_lab_observation_store import RUN_RECEIPT_SCHEMA, USED_RECEIPT_SCHEMA, write_run_receipt, write_used_receipt
from relaylm_phase_i1_two_turn_primary_recall_smoke import CHARACTER, NAMESPACE

REPO_ROOT = Path(__file__).resolve().parents[1]
SUMMARY = "I4E_FORGET_API_MEMORY_CONTENT_CANARY"
REASON = "I4E_FORGET_API_REASON_CANARY"
NOW = datetime(2026, 6, 27, 0, 0, tzinfo=timezone.utc).isoformat()


def preflight_body(revision: int, operation_id: str, *, reason: str = REASON) -> dict[str, object]:
    return {
        "schema": "relaylm.lab.memory_forget_preflight_request.v0",
        "expected_revision": revision,
        "expected_lifecycle_state": "active",
        "reason": reason,
        "operation_id": operation_id,
    }


def apply_body(revision: int, operation_id: str, token: str, *, reason: str = REASON) -> dict[str, object]:
    return {
        "schema": "relaylm.lab.memory_forget_apply_request.v0",
        "expected_revision": revision,
        "expected_lifecycle_state": "active",
        "reason": reason,
        "operation_id": operation_id,
        "apply_token": token,
    }


def assert_no_mutation_leak(text: str, *tokens: str) -> None:
    for value in (
        SUMMARY, REASON, "reason_digest", "token_digest", "physical_id",
        "store_root", "filesystem", "tombstone_content", *tokens,
    ):
        if value:
            require(value not in text, value)


def assert_no_private_control_leak(text: str, *tokens: str) -> None:
    for value in (REASON, "reason_digest", "token_digest", "physical_id", "store_root", "filesystem", *tokens):
        if value:
            require(value not in text, value)


def write_used_evidence(store_root: Path, memory_id: str) -> None:
    require(write_run_receipt(str(store_root), {
        "schema": RUN_RECEIPT_SCHEMA, "runtime_private": True, "read_model_only": True,
        "request_id": "i4e-request", "run_id": "i4e-run", "character_id": CHARACTER,
        "namespace": NAMESPACE, "started_at": NOW, "completed_at": NOW, "duration_ms": 0,
        "response_mode": "non_stream", "http_status": 200, "relayrun_status": "completed",
        "relayctx_repack_status": "applied", "relayctx_unpack_status": "completed",
        "slp_status": "disabled", "recovery_required": False, "reason_ids": [],
    }), "run receipt")
    require(write_used_receipt(str(store_root), {
        "schema": USED_RECEIPT_SCHEMA, "runtime_private": True, "read_model_only": True,
        "request_id": "i4e-request", "run_id": "i4e-run", "character_id": CHARACTER,
        "namespace": NAMESPACE, "retrieval_attempted": True, "candidate_discovered": True,
        "selected": True, "relayctx_injection_performed": True, "backend_bound_included": True,
        "items": [{"memory_id": memory_id, "injected_summary": SUMMARY, "source_kind": "preference"}],
        "captured_at": NOW, "reason_ids": [],
    }), "used receipt")


def main() -> None:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
        root = Path(directory)
        queue = root / "queue"; protected = root / "protected"; store = root / "store"
        queue.mkdir(); protected.mkdir(); store.mkdir()
        scoped_value = resolve_relaymem_character_store_root(str(store), CHARACTER)
        require(scoped_value is not None, "scope")
        scoped = Path(scoped_value)
        memory_id = form_primary_memory(scoped, namespace=NAMESPACE, candidate_id="i4e-api-main", title="forget target", summary=SUMMARY)
        already_id = form_primary_memory(scoped, namespace=NAMESPACE, candidate_id="i4e-api-already", title="already", summary="already summary")
        write_used_evidence(scoped, memory_id)

        config_path = root / "config.yaml"
        write_config(config_path, port=9, queue=queue, protected=protected, store=store, enqueue_enabled=False)
        app = create_app(str(config_path))
        with TestClient(app, client=("127.0.0.1", 50000)) as client:
            query = f"?namespace={NAMESPACE}"
            base = f"/lab/api/characters/{CHARACTER}/memory/{memory_id}"
            preflight = client.post(f"{base}/forget/preflight{query}", json=preflight_body(1, "i4e-api-main"))
            require(preflight.status_code == 200, preflight.text)
            require(preflight.headers["cache-control"] == "no-store", preflight.headers)
            token = preflight.json()["apply_token"]
            require(preflight.json()["effects"]["ordinary_retrieval_excluded"] is True, preflight.json())
            require(preflight.json()["effects"]["relayctx_injection_excluded"] is True, preflight.json())
            require(preflight.json()["effects"]["physical_deletion"] is False, preflight.json())
            assert_no_mutation_leak(preflight.text)

            invalid = client.post(f"{base}/forget{query}", json=apply_body(1, "i4e-api-main", token + "x"))
            require(invalid.status_code == 403, invalid.text)
            require(invalid.json() == {"detail": "token_invalid"}, invalid.json())
            assert_no_mutation_leak(invalid.text, token)

            applied = client.post(f"{base}/forget{query}", json=apply_body(1, "i4e-api-main", token))
            require(applied.status_code == 200, applied.text)
            receipt = applied.json()
            require(receipt["schema"] == "relaylm.lab.memory_forget_apply.v0", receipt)
            require(receipt["lifecycle_state"] == "hidden", receipt)
            require(receipt["retrieval_eligible"] is False, receipt)
            require(receipt["ordinary_retrieval_excluded"] is True, receipt)
            require(receipt["relayctx_injection_excluded"] is True, receipt)
            require(receipt["audit_evidence_retained"] is True, receipt)
            assert_no_mutation_leak(applied.text, token)

            history = client.get(f"{base}/forget-history{query}")
            require(history.status_code == 200, history.text)
            history_json = history.json()
            require(history_json["schema"] == "relaylm.lab.memory_forget_history.v0", history_json)
            require(history_json["read_only"] is True, history_json)
            require(history_json["memory_id"] == memory_id, history_json)
            require(history_json["current_lifecycle_state"] == "hidden", history_json)
            require(history_json["current_revision"] == 2, history_json)
            require(history_json["forget_count"] >= 1, history_json)
            require(len(history_json["items"]) >= 1, history_json)
            item = history_json["items"][0]
            require(item["receipt_type"] == "forget_tombstone", item)
            require(item["operation_kind"] == "forget", item)
            require(item["prior_revision"] == 1, item)
            require(item["result_revision"] == 2, item)
            require(item["lifecycle_state"] == "hidden", item)
            require(item["retrieval_eligible"] is False, item)
            require(item["ordinary_retrieval_excluded"] is True, item)
            require(item["relayctx_injection_excluded"] is True, item)
            require(item["physical_deletion"] is False, item)
            require(item["audit_evidence_retained"] is True, item)
            require(item["tombstone_present"] is True, item)
            require(item["page_converged"] is True, item)
            require(item["index_converged"] is True, item)
            require(item["log_converged"] is True, item)
            assert_no_mutation_leak(history.text, token)

            recent = client.get(f"/lab/api/characters/{CHARACTER}/memory/recent{query}&limit=20")
            require(recent.status_code == 200, recent.text)
            require(all(item["memory_id"] != memory_id for item in recent.json()["items"]), recent.json())
            assert_no_private_control_leak(recent.text, token)

            recent_limited = client.get(f"/lab/api/characters/{CHARACTER}/memory/recent{query}&limit=1")
            require(recent_limited.status_code == 200, recent_limited.text)
            recent_limited_json = recent_limited.json()
            require(recent_limited_json["availability"] == "available", recent_limited_json)
            require(len(recent_limited_json["items"]) == 1, recent_limited_json)
            require(recent_limited_json["items"][0]["memory_id"] == already_id, recent_limited_json)
            assert_no_private_control_leak(recent_limited.text, token)

            lifecycle = client.get(f"/lab/api/characters/{CHARACTER}/lab/last-run/memory/used-lifecycle{query}")
            require(lifecycle.status_code == 200, lifecycle.text)
            item = lifecycle.json()["items"][0]
            require(item["memory_id"] == memory_id, item)
            require(item["current_lifecycle_state"] == "hidden", item)
            require(item["current_summary"] is None, item)
            require(SUMMARY in lifecycle.text, lifecycle.text)
            assert_no_private_control_leak(lifecycle.text, token)

            already_base = f"/lab/api/characters/{CHARACTER}/memory/{already_id}"
            a = client.post(f"{already_base}/forget/preflight{query}", json=preflight_body(1, "i4e-already-a"))
            b = client.post(f"{already_base}/forget/preflight{query}", json=preflight_body(1, "i4e-already-b", reason="second bounded reason"))
            require(a.status_code == b.status_code == 200, (a.text, b.text))
            winner = client.post(f"{already_base}/forget{query}", json=apply_body(1, "i4e-already-a", a.json()["apply_token"]))
            require(winner.status_code == 200, winner.text)
            loser = client.post(f"{already_base}/forget{query}", json=apply_body(1, "i4e-already-b", b.json()["apply_token"], reason="second bounded reason"))
            require(loser.status_code in {200, 409}, loser.text)
            if loser.status_code == 200:
                require(loser.json()["status"] == "already_hidden", loser.json())
            else:
                require(loser.json()["detail"] in {"stale_revision", "already_hidden", "operation_conflict"}, loser.json())
            already_history = client.get(f"{already_base}/forget-history{query}")
            require(already_history.status_code == 200, already_history.text)
            require(already_history.json()["current_lifecycle_state"] == "hidden", already_history.json())
            require(already_history.json()["forget_count"] == 1, already_history.json())
            require(len(already_history.json()["items"]) == 1, already_history.json())
            assert_no_mutation_leak(already_history.text, a.json()["apply_token"], b.json()["apply_token"])

            require(client.get("/healthz").status_code == 200, "health regression")
            require(client.get("/v1/models").status_code == 200, "models regression")

        remote = TestClient(app, client=("192.0.2.10", 50000))
        denied = remote.post(
            f"/lab/api/characters/{CHARACTER}/memory/{memory_id}/forget/preflight?namespace={NAMESPACE}",
            json=preflight_body(1, "remote"),
            headers={"Host": "127.0.0.1", "X-Forwarded-For": "127.0.0.1"},
        )
        require(denied.status_code == 403, denied.text)

    print("Phase I-4E Forget API functional smoke passed")


if __name__ == "__main__":
    main()
