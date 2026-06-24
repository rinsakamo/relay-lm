"""Security, ordering, bounds, and corruption smoke for Phase I-2."""
from __future__ import annotations

import json
import os
import tempfile
from hashlib import sha256
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from relaylm import soul_lab_observation_store as observation_store
from relaylm.relaymem_primary_recall import resolve_relaymem_character_store_root
from relaylm.soul_lab_app import create_app
from relaylm.soul_lab_observation_projection import (
    build_lab_last_run_projection,
    build_lab_memory_held_projection,
    build_lab_memory_used_projection,
    resolve_lab_observation_scope,
)
from relaylm.soul_lab_observation_store import (
    OUTCOME_RECEIPT_SCHEMA,
    RUN_RECEIPT_SCHEMA,
    USED_RECEIPT_SCHEMA,
    stable_correlation,
    utc_now,
    write_outcome_receipt,
    write_run_receipt,
    write_used_receipt,
)
from relaylm_phase6c1_primary_worker_test_support import prepare_store
from relaylm_phase_i1_two_turn_primary_recall_smoke import (
    CHARACTER,
    NAMESPACE,
    OTHER_NAMESPACE,
    write_config,
)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def run_receipt(run_id: str, completed_at: str) -> dict[str, object]:
    return {
        "schema": RUN_RECEIPT_SCHEMA,
        "runtime_private": True,
        "read_model_only": True,
        "request_id": f"request-{run_id}",
        "run_id": run_id,
        "character_id": CHARACTER,
        "namespace": NAMESPACE,
        "started_at": "2026-06-24T08:00:00+00:00",
        "completed_at": completed_at,
        "duration_ms": 100,
        "response_mode": "non_stream",
        "http_status": 200,
        "relayrun_status": "completed",
        "relayctx_repack_status": "applied",
        "relayctx_unpack_status": "not_observed",
        "slp_status": "disabled",
        "recovery_required": False,
        "reason_ids": [],
    }


def used_receipt(run_id: str, count: int) -> dict[str, object]:
    items = [
        {
            "memory_id": sha256(f"memory-{index}".encode()).hexdigest(),
            "injected_summary": f"bounded injected summary {index}",
            "source_kind": "preference",
        }
        for index in range(count)
    ]
    return {
        "schema": USED_RECEIPT_SCHEMA,
        "runtime_private": True,
        "read_model_only": True,
        "request_id": f"request-{run_id}",
        "run_id": run_id,
        "character_id": CHARACTER,
        "namespace": NAMESPACE,
        "retrieval_attempted": True,
        "candidate_discovered": bool(items),
        "selected": bool(items),
        "relayctx_injection_performed": bool(items),
        "backend_bound_included": bool(items),
        "items": items,
        "captured_at": utc_now(),
        "reason_ids": [],
    }


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
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

        same_completion = "2026-06-24T08:10:00+00:00"
        write_run_receipt(str(scoped), run_receipt("run-a", same_completion))
        write_run_receipt(str(scoped), run_receipt("run-b", same_completion))
        # A later-looking local timestamp that is earlier in UTC must not win.
        write_run_receipt(
            str(scoped),
            run_receipt("run-c-offset", "2026-06-24T17:09:00+09:00"),
        )
        write_used_receipt(str(scoped), used_receipt("run-b", 16))
        # A used receipt without a completed run cannot become latest evidence.
        write_used_receipt(str(scoped), used_receipt("run-z-incomplete", 1))
        write_used_receipt(str(scoped), used_receipt("run-y-incomplete", 1))

        for index in range(55):
            status = "held" if index % 2 == 0 else "blocked"
            write_outcome_receipt(
                str(scoped),
                {
                    "schema": OUTCOME_RECEIPT_SCHEMA,
                    "runtime_private": True,
                    "read_model_only": True,
                    "run_id": "run-b",
                    "job_correlation_id": stable_correlation(f"job-{index}"),
                    "namespace": NAMESPACE,
                    "turn_index": index,
                    "outcome_status": status,
                    "worker_status": "pipeline_held" if status == "held" else "terminal_failed",
                    "pipeline_status": status,
                    "title": f"outcome {index}",
                    "bounded_summary": "x" * 512,
                    "observed_at": f"2026-06-24T08:{index % 60:02d}:00+00:00",
                    "reason_ids": [f"bounded_reason_{index}"],
                },
            )

        # Newer records from another namespace must not starve this scope.
        for index in range(3):
            write_outcome_receipt(
                str(scoped),
                {
                    "schema": OUTCOME_RECEIPT_SCHEMA,
                    "runtime_private": True,
                    "read_model_only": True,
                    "run_id": "other-namespace-flood",
                    "job_correlation_id": stable_correlation(f"other-job-{index}"),
                    "namespace": OTHER_NAMESPACE,
                    "turn_index": index,
                    "outcome_status": "held",
                    "worker_status": "pipeline_held",
                    "pipeline_status": "held",
                    "title": "other namespace",
                    "bounded_summary": "must not hide the requested namespace",
                    "observed_at": f"2099-01-01T00:0{index}:00+00:00",
                    "reason_ids": ["other_namespace_flood"],
                },
            )

        outcome_dir = scoped / ".relaylm-lab-observation-v0" / "outcomes"
        bad_envelope = {
            "schema": "relaylm.lab.observation_store.v0",
            "payload": {
                "schema": OUTCOME_RECEIPT_SCHEMA,
                "runtime_private": True,
            },
            "payload_digest": "0" * 64,
        }
        (outcome_dir / "digest-mismatch.json").write_text(
            json.dumps(bad_envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        (outcome_dir / "truncated.json").write_text("{", encoding="utf-8")
        symlink_created = False
        try:
            os.symlink(outcome_dir / "truncated.json", outcome_dir / "unsafe-link.json")
            symlink_created = True
        except (OSError, NotImplementedError):
            pass

        config_path = root / "config.yaml"
        write_config(
            config_path,
            port=9,
            queue=queue,
            protected=protected,
            store=store,
            enqueue_enabled=False,
        )
        app = create_app(str(config_path))
        scope = resolve_lab_observation_scope(
            app.state.relaylm_config,
            character_id=CHARACTER,
            namespace=NAMESPACE,
        )
        original_receipt_limit = observation_store._MAX_RECEIPTS_PER_KIND
        observation_store._MAX_RECEIPTS_PER_KIND = 2
        try:
            latest = build_lab_last_run_projection(scope)
            used = build_lab_memory_used_projection(scope)
            held_scoped = build_lab_memory_held_projection(scope, limit=2)
        finally:
            observation_store._MAX_RECEIPTS_PER_KIND = original_receipt_limit
        require(latest.run_id == "run-b", latest.model_dump())
        require(latest.status == "completed", latest.model_dump())
        require("observation_receipt_count_exceeded" in latest.bounded_reason_ids, latest.model_dump())
        require(used.run_id == "run-b", used.model_dump())
        require(len(used.items) == 16, used.model_dump())
        require(len(held_scoped.items) == 2, held_scoped.model_dump())
        require(all(item.run_id == "run-b" for item in held_scoped.items), held_scoped.model_dump())
        held = build_lab_memory_held_projection(scope, limit=50)
        require(len(held.items) == 50, len(held.items))
        require("observation_receipt_corrupt_ignored" in held.bounded_reason_ids, held.model_dump())
        require(len(json.dumps(held.model_dump(mode="json"), ensure_ascii=False).encode()) < 128 * 1024, "response bound")
        if symlink_created:
            require("observation_receipt_corrupt_ignored" in held.bounded_reason_ids, held.model_dump())

        with TestClient(app, client=("127.0.0.1", 50000)) as client:
            base = f"/lab/api/characters/{CHARACTER}"
            correct = client.get(f"{base}/lab/last-run?namespace={NAMESPACE}")
            require(correct.status_code == 200, correct.text)
            require(correct.headers["cache-control"] == "no-store", correct.headers)
            require(correct.json()["run_id"] == "run-b", correct.json())

            wrong_namespace = client.get(
                f"{base}/lab/last-run?namespace={OTHER_NAMESPACE}"
            )
            require(wrong_namespace.status_code == 200, wrong_namespace.text)
            require(wrong_namespace.json()["run_id"] is None, wrong_namespace.json())
            require("run-b" not in wrong_namespace.text, wrong_namespace.text)

            for method in ("POST", "PUT", "PATCH", "DELETE"):
                response = client.request(
                    method,
                    f"{base}/lab/last-run?namespace={NAMESPACE}",
                    json={"mutation": True},
                )
                require(response.status_code == 405, response.text)

            remote = TestClient(app, client=("192.0.2.10", 50000))
            spoofed = remote.get(
                f"{base}/lab/last-run?namespace={NAMESPACE}",
                headers={
                    "Host": "127.0.0.1",
                    "Origin": "http://127.0.0.1",
                    "X-Forwarded-For": "127.0.0.1",
                },
            )
            require(spoofed.status_code == 403, spoofed.text)
            require(remote.get("/healthz").status_code == 200, "health regression")
            require(remote.get("/v1/models").status_code == 200, "models regression")

        remote_raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        remote_raw["listen"] = {"host": "0.0.0.0", "port": 8090}
        remote_path = root / "remote.yaml"
        remote_path.write_text(yaml.safe_dump(remote_raw, sort_keys=False), encoding="utf-8")
        remote_config_app = create_app(str(remote_path))
        with TestClient(remote_config_app, client=("127.0.0.1", 50000)) as client:
            refused = client.get(
                f"/lab/api/characters/{CHARACTER}/lab/last-run?namespace={NAMESPACE}"
            )
            require(refused.status_code == 403, refused.text)

    print("Phase I-2 observation security smoke passed")


if __name__ == "__main__":
    main()
