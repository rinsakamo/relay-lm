"""UI-B1A lifecycle visibility security and route-boundary smoke."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from _relaylm_phase_i4b_test_support import CHARACTER, NAMESPACE, require
from relaylm.relaymem_primary_recall import resolve_relaymem_character_store_root
from relaylm.soul_lab_app import create_app
from relaylm_phase6c1_primary_worker_test_support import prepare_store
from relaylm_phase_i1_two_turn_primary_recall_smoke import write_config

PRIVATE_CANARIES = (
    "好きな飲み物は紅茶です。",
    "claim-secret-token",
    "slp-job-v0:",
    "slp-dispatch-v0:",
    "Traceback",
    "config.yaml",
    "segment-isolation",
)


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        queue = root / "queue"
        protected = root / "protected"
        store = root / "store"
        durable = root / "durable"
        queue.mkdir()
        protected.mkdir()
        store.mkdir()
        durable.mkdir()
        scoped_value = resolve_relaymem_character_store_root(str(store), CHARACTER)
        require(scoped_value is not None, "scope")
        scoped = Path(scoped_value)
        prepare_store(scoped)

        config_path = root / "config.yaml"
        write_config(config_path, port=9, queue=queue, protected=protected, store=store, enqueue_enabled=False)
        cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        cfg["relaymem_slp_durable_finalization_root"] = str(durable.resolve())
        config_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")

        app = create_app(str(config_path))
        base = f"/lab/api/characters/{CHARACTER}/lab/lifecycle-visibility?namespace={NAMESPACE}"
        with TestClient(app, client=("127.0.0.1", 50000)) as client:
            response = client.get(base)
            require(response.status_code == 200, response.text)
            require(response.headers["cache-control"] == "no-store", response.headers)
            payload = response.json()
            require(payload["schema"] == "relaylm.lab.lifecycle_visibility.v0", payload)
            require(payload["read_only"] is True, payload)
            require(payload["mutation_controls_exposed"] is False, payload)
            require(payload["scheduler_controls_exposed"] is False, payload)
            require(payload["repair_controls_exposed"] is False, payload)
            require(payload["raw_content_included"] is False, payload)
            require(payload["raw_paths_included"] is False, payload)
            require(payload["raw_private_identifiers_included"] is False, payload)
            require(payload["durable_finalization"]["content_free"] is True, payload)
            require(payload["queue_worker"]["content_free"] is True, payload)
            require(payload["queue_worker"]["scheduler_controls_exposed"] is False, payload)
            require(payload["queue_worker"]["worker_controls_exposed"] is False, payload)
            require(payload["fresh_conversation"]["durable_memory_store_reset"] is False, payload)
            require(payload["fresh_conversation"]["home_transcript_is_durable_source"] is False, payload)
            serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
            for canary in PRIVATE_CANARIES:
                require(canary not in serialized, (canary, serialized))
            for method in ("POST", "PUT", "PATCH", "DELETE"):
                mutation = client.request(method, base, json={"run": True, "repair": True})
                require(mutation.status_code == 405, (method, mutation.text))

        remote = TestClient(app, client=("192.0.2.10", 50000))
        spoofed = remote.get(
            base,
            headers={
                "Host": "127.0.0.1",
                "Origin": "http://127.0.0.1",
                "X-Forwarded-For": "127.0.0.1",
            },
        )
        require(spoofed.status_code == 403, spoofed.text)
        require(remote.get("/healthz").status_code == 200, "health regression")
        require(remote.get("/v1/models").status_code == 200, "models regression")

    print("UI-B1A lifecycle visibility security smoke passed")


if __name__ == "__main__":
    main()
