"""Phase I-7C loopback held governance API preflight smoke."""
from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from _relaylm_phase_i3_test_support import require, write_config
from relaylm.relaymem_held_governance import persist_held_candidate_evidence
from relaylm.relaymem_held_governance_contract import HELD_OUTCOME_CANDIDATE_SCHEMA
from relaylm.relaymem_primary_recall import resolve_relaymem_character_store_root
from relaylm.soul_lab_app import create_app
from relaylm_phase_i1_two_turn_primary_recall_smoke import CHARACTER, NAMESPACE

SHA_A = "a" * 64
CONTENT_CANARY = "I7C_CONTENT_CANARY"


def candidate(candidate_id: str) -> dict[str, object]:
    return {
        "schema_version": HELD_OUTCOME_CANDIDATE_SCHEMA,
        "runtime_private": True,
        "content_included": False,
        "candidate_id": candidate_id,
        "operation_id": "worker-op-api",
        "character_id": CHARACTER,
        "namespace": NAMESPACE,
        "scope": "primary_formation",
        "status": "held",
        "queue_state": "claimed",
        "source_authority": "primary_worker_outcome",
        "source_evidence_digest": SHA_A,
        "source_evidence_present": True,
        "source_evidence_corrupt": False,
        "source_evidence_ambiguous": False,
        "source_content_included": False,
        "related_primary_memory_id": None,
        "related_primary_expected_revision": None,
        "related_primary_physical_id": None,
    }


def preflight_body(operation_id: str) -> dict[str, object]:
    return {
        "schema": "relaylm.lab.held_governance_preflight_request.v0",
        "operation_id": operation_id,
        "reason": "bounded operator reason",
    }


def assert_safe(text: str) -> None:
    for forbidden in (
        CONTENT_CANARY,
        "source_evidence_digest",
        "candidate_digest",
        "reason_digest",
        "token_digest",
        "source_path",
        "protected_source",
        "Traceback",
    ):
        require(forbidden not in text, forbidden)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(dir=repo_root) as directory:
        root = Path(directory)
        queue = root / "queue"; protected = root / "protected"; store = root / "store"
        queue.mkdir(); protected.mkdir(); store.mkdir()
        scoped_value = resolve_relaymem_character_store_root(str(store), CHARACTER)
        require(scoped_value is not None, "scope")
        scoped = Path(scoped_value)
        persist_held_candidate_evidence(scoped, candidate("held-api-apply"))

        config_path = root / "config.yaml"
        write_config(config_path, port=9, queue=queue, protected=protected, store=store, enqueue_enabled=False)
        app = create_app(str(config_path))
        query = f"?namespace={NAMESPACE}"
        with TestClient(app, client=("127.0.0.1", 50000)) as client:
            base = f"/lab/api/characters/{CHARACTER}/held/held-api-apply"
            preflight = client.post(f"{base}/apply/preflight{query}", json=preflight_body("i7c-api-apply"))
            require(preflight.status_code == 200, preflight.text)
            require(preflight.headers["cache-control"] == "no-store", preflight.headers)
            body = preflight.json()
            require(body["schema"] == "relaylm.lab.held_governance_preflight.v0", body)
            require(body["status"] == "ready", body)
            require(body["content_free"] is True, body)
            require(body["runtime_private_evidence_omitted"] is True, body)
            require(body["queue_state_mutated"] is False, body)
            require(body["worker_started"] is False, body)
            require(isinstance(body["apply_token"], str), body)
            assert_safe(preflight.text)

            require(client.get("/healthz").status_code == 200, "health regression")
            require(client.get("/v1/models").status_code == 200, "models regression")

    print("Phase I-7C held governance API preflight smoke passed")


if __name__ == "__main__":
    main()
