"""SOUL Lab correction/forget route split regression smoke.

Confirms that extracting Primary MEM correction and forget route
registration out of ``soul_lab_app.py`` into
``soul_lab_memory_correction_routes.py`` / ``soul_lab_memory_forget_routes.py``
did not change route wiring, request/response contracts, loopback
enforcement, or cache headers.
"""
from __future__ import annotations

import importlib
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import ValidationError

from _relaylm_phase_i3_test_support import form_primary_memory, require, write_config
from relaylm.relaymem_primary_recall import resolve_relaymem_character_store_root
from relaylm.soul_lab_app import create_app
from relaylm.soul_lab_memory_correction import LabMemoryCorrectPreflightRequest
from relaylm.soul_lab_memory_forget import LabMemoryForgetPreflightRequest
from relaylm_phase_i1_two_turn_primary_recall_smoke import CHARACTER, NAMESPACE

REPO_ROOT = Path(__file__).resolve().parents[1]
SUMMARY = "SOUL_LAB_MEMORY_ROUTES_SPLIT_CONTENT_CANARY"
REASON = "SOUL_LAB_MEMORY_ROUTES_SPLIT_REASON_CANARY"

EXPECTED_ROUTE_PATHS = {
    "/lab/api/characters/{character_id}/memory/{memory_id}/correct/preflight",
    "/lab/api/characters/{character_id}/memory/{memory_id}/correct",
    "/lab/api/characters/{character_id}/memory/{memory_id}/corrections",
    "/lab/api/characters/{character_id}/memory/{memory_id}/forget/preflight",
    "/lab/api/characters/{character_id}/memory/{memory_id}/forget",
    "/lab/api/characters/{character_id}/memory/{memory_id}/forget-history",
    "/lab/api/characters/{character_id}/memory/{memory_id}/pin/preflight",
    "/lab/api/characters/{character_id}/memory/{memory_id}/pin",
    "/lab/api/characters/{character_id}/memory/{memory_id}/pin-history",
    "/lab/api/characters/{character_id}/memory/{memory_id}/unpin/preflight",
    "/lab/api/characters/{character_id}/memory/{memory_id}/unpin",
    "/lab/api/characters/{character_id}/memory/{memory_id}/unpin-history",
}


def check_extracted_modules_import_cleanly() -> None:
    for name in (
        "relaylm.soul_lab_memory_correction_routes",
        "relaylm.soul_lab_memory_forget_routes",
    ):
        sys.modules.pop(name, None)
        module = importlib.import_module(name)
        require(hasattr(module, "install_primary_memory_correction_routes") or hasattr(
            module, "install_primary_memory_forget_routes"
        ), name)


def check_schema_alias_contract() -> None:
    valid_correct = {
        "schema": "relaylm.lab.memory_correct_preflight_request.v0",
        "expected_revision": 1,
        "corrected_title": "Corrected title",
        "corrected_summary": "Corrected summary",
        "reason": REASON,
        "operation_id": "op-1",
    }
    parsed = LabMemoryCorrectPreflightRequest.model_validate(valid_correct)
    require(parsed.model_dump(by_alias=True)["schema"] == valid_correct["schema"], parsed)

    rejected = dict(valid_correct)
    rejected["schema_"] = rejected.pop("schema")
    try:
        LabMemoryCorrectPreflightRequest.model_validate(rejected)
    except ValidationError:
        pass
    else:
        raise AssertionError("internal schema_ key unexpectedly accepted as public input")

    valid_forget = {
        "schema": "relaylm.lab.memory_forget_preflight_request.v0",
        "expected_revision": 1,
        "expected_lifecycle_state": "active",
        "reason": REASON,
        "operation_id": "op-1",
    }
    parsed_forget = LabMemoryForgetPreflightRequest.model_validate(valid_forget)
    require(parsed_forget.model_dump(by_alias=True)["schema"] == valid_forget["schema"], parsed_forget)


def check_routes_and_behavior() -> None:
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
        memory_id = form_primary_memory(
            scoped,
            namespace=NAMESPACE,
            candidate_id="soul-lab-memory-routes-split",
            title="routes split target",
            summary=SUMMARY,
        )

        config_path = root / "config.yaml"
        write_config(config_path, port=9, queue=queue, protected=protected, store=store, enqueue_enabled=False)
        app = create_app(str(config_path))

        installed_paths = {
            route.path for route in app.routes if hasattr(route, "path")
        }
        missing = EXPECTED_ROUTE_PATHS - installed_paths
        require(not missing, missing)

        query = f"?namespace={NAMESPACE}"
        base = f"/lab/api/characters/{CHARACTER}/memory/{memory_id}"

        with TestClient(app, client=("127.0.0.1", 50000)) as client:
            preflight = client.post(
                f"{base}/correct/preflight{query}",
                json={
                    "schema": "relaylm.lab.memory_correct_preflight_request.v0",
                    "expected_revision": 1,
                    "corrected_title": "Corrected title",
                    "corrected_summary": "Corrected summary",
                    "reason": REASON,
                    "operation_id": "routes-split-correct",
                },
            )
            require(preflight.status_code == 200, preflight.text)
            require(preflight.headers["cache-control"] == "no-store", preflight.headers)

            corrections = client.get(f"{base}/corrections{query}")
            require(corrections.status_code == 200, corrections.text)
            require(corrections.headers["cache-control"] == "no-store", corrections.headers)

            forget_preflight = client.post(
                f"{base}/forget/preflight{query}",
                json={
                    "schema": "relaylm.lab.memory_forget_preflight_request.v0",
                    "expected_revision": 1,
                    "expected_lifecycle_state": "active",
                    "reason": REASON,
                    "operation_id": "routes-split-forget",
                },
            )
            require(forget_preflight.status_code == 200, forget_preflight.text)
            require(forget_preflight.headers["cache-control"] == "no-store", forget_preflight.headers)

            forget_history = client.get(f"{base}/forget-history{query}")
            require(forget_history.status_code == 200, forget_history.text)
            require(forget_history.headers["cache-control"] == "no-store", forget_history.headers)

        remote = TestClient(app, client=("192.0.2.10", 50000))
        remote_correct = remote.post(
            f"{base}/correct/preflight{query}",
            json={
                "schema": "relaylm.lab.memory_correct_preflight_request.v0",
                "expected_revision": 1,
                "corrected_title": "Corrected title",
                "corrected_summary": "Corrected summary",
                "reason": REASON,
                "operation_id": "routes-split-correct-remote",
            },
        )
        require(remote_correct.status_code == 403, remote_correct.text)

        remote_forget = remote.post(
            f"{base}/forget/preflight{query}",
            json={
                "schema": "relaylm.lab.memory_forget_preflight_request.v0",
                "expected_revision": 1,
                "expected_lifecycle_state": "active",
                "reason": REASON,
                "operation_id": "routes-split-forget-remote",
            },
        )
        require(remote_forget.status_code == 403, remote_forget.text)


def main() -> None:
    check_extracted_modules_import_cleanly()
    check_schema_alias_contract()
    check_routes_and_behavior()
    print("SOUL Lab memory routes split smoke passed")


if __name__ == "__main__":
    main()
