"""Bounds, expiry, payload conflict, and true concurrency smoke for Phase I-3."""
from __future__ import annotations

import json
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from relaylm.relaymem_primary_correction import (
    PrimaryCorrectionError,
    apply_primary_memory_correction,
    list_primary_memory_corrections,
    preflight_primary_memory_correction,
)
from relaylm.relaymem_primary_recall import resolve_relaymem_character_store_root
from relaylm.soul_lab_app import create_app
from relaylm_phase_i1_two_turn_primary_recall_smoke import CHARACTER, NAMESPACE
from _relaylm_phase_i3_test_support import form_primary_memory, require, write_config

REPO_ROOT = Path(__file__).resolve().parents[1]


def preflight_body(
    operation_id: str,
    *,
    title: str = "corrected title",
    summary: str = "corrected summary",
    reason: str = "explicit correction",
) -> dict[str, object]:
    return {
        "schema": "relaylm.lab.memory_correct_preflight_request.v0",
        "expected_revision": 1,
        "corrected_title": title,
        "corrected_summary": summary,
        "reason": reason,
        "operation_id": operation_id,
    }


def apply_body(operation_id: str, token: str) -> dict[str, object]:
    return {
        "schema": "relaylm.lab.memory_correct_apply_request.v0",
        "operation_id": operation_id,
        "apply_token": token,
        "expected_revision": 1,
    }


def main() -> None:
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
        memories = [
            form_primary_memory(
                scoped,
                namespace=NAMESPACE,
                candidate_id=f"phase-i3-validation-{index}",
                title=f"original {index}",
                summary=f"original summary {index}",
            )
            for index in range(4)
        ]
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
        query = f"?namespace={NAMESPACE}"

        with TestClient(app, client=("127.0.0.1", 50000)) as client:
            bounds_base = f"/lab/api/characters/{CHARACTER}/memory/{memories[0]}"
            maximum = client.post(
                f"{bounds_base}/correct/preflight{query}",
                json=preflight_body(
                    "maximum-bounds",
                    title="t" * 160,
                    summary="s" * 2048,
                    reason="r" * 512,
                ),
            )
            require(maximum.status_code == 200, maximum.text)
            require(len(maximum.json()["diff"]["after"]["title"]) == 160, maximum.json())
            require(len(maximum.json()["diff"]["after"]["summary"]) == 2048, maximum.json())

            for name, body in (
                ("title-too-long", preflight_body("title-too-long", title="t" * 161)),
                ("summary-too-long", preflight_body("summary-too-long", summary="s" * 2049)),
                ("reason-too-long", preflight_body("reason-too-long", reason="r" * 513)),
                ("control-character", preflight_body("control-character", summary="bad\u0001text")),
                ("unicode-separator", preflight_body("unicode-separator", summary="bad\u2028text")),
            ):
                response = client.post(
                    f"{bounds_base}/correct/preflight{query}", json=body
                )
                require(response.status_code == 422, (name, response.text))
                require(response.json() == {"detail": "invalid_request"}, (name, response.json()))

            huge = preflight_body("huge-body", summary="x" * 20_000)
            huge_response = client.post(
                f"{bounds_base}/correct/preflight{query}",
                content=json.dumps(huge),
                headers={"Content-Type": "application/json"},
            )
            require(huge_response.status_code == 422, huge_response.text)

            script_like = "<script>alert('text-only')</script>"
            script_response = client.post(
                f"{bounds_base}/correct/preflight{query}",
                json=preflight_body(
                    "script-like-text",
                    title=script_like,
                    summary="text containing <img src=x onerror=alert(1)>",
                ),
            )
            require(script_response.status_code == 200, script_response.text)
            require(
                script_response.json()["diff"]["after"]["title"] == script_like,
                script_response.json(),
            )

            expiry_base = f"/lab/api/characters/{CHARACTER}/memory/{memories[1]}"
            expiring = client.post(
                f"{expiry_base}/correct/preflight{query}",
                json=preflight_body("expired-token"),
            )
            require(expiring.status_code == 200, expiring.text)
            future = datetime.now(timezone.utc) + timedelta(minutes=10)
            with patch(
                "relaylm.relaymem_primary_correction._utc", return_value=future
            ):
                expired = client.post(
                    f"{expiry_base}/correct{query}",
                    json=apply_body("expired-token", expiring.json()["apply_token"]),
                )
            require(expired.status_code == 409, expired.text)
            require(expired.json() == {"detail": "token_expired"}, expired.json())

            conflict_base = f"/lab/api/characters/{CHARACTER}/memory/{memories[2]}"
            first = client.post(
                f"{conflict_base}/correct/preflight{query}",
                json=preflight_body("same-operation", summary="candidate A"),
            )
            second = client.post(
                f"{conflict_base}/correct/preflight{query}",
                json=preflight_body("same-operation", summary="candidate B"),
            )
            require(first.status_code == second.status_code == 200, (first.text, second.text))
            applied = client.post(
                f"{conflict_base}/correct{query}",
                json=apply_body("same-operation", first.json()["apply_token"]),
            )
            require(applied.status_code == 200, applied.text)
            conflicting = client.post(
                f"{conflict_base}/correct{query}",
                json=apply_body("same-operation", second.json()["apply_token"]),
            )
            require(conflicting.status_code == 409, conflicting.text)
            require(conflicting.json() == {"detail": "operation_conflict"}, conflicting.json())

        concurrent_id = memories[3]
        token_a = preflight_primary_memory_correction(
            store_root=str(scoped),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=concurrent_id,
            expected_revision=1,
            corrected_title="concurrent A",
            corrected_summary="concurrent candidate A",
            reason="concurrency verification A",
            operation_id="concurrent-a",
        )["apply_token"]
        token_b = preflight_primary_memory_correction(
            store_root=str(scoped),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=concurrent_id,
            expected_revision=1,
            corrected_title="concurrent B",
            corrected_summary="concurrent candidate B",
            reason="concurrency verification B",
            operation_id="concurrent-b",
        )["apply_token"]
        barrier = threading.Barrier(2)

        def apply_concurrent(operation_id: str, token: str) -> tuple[str, str]:
            barrier.wait(timeout=10)
            try:
                result = apply_primary_memory_correction(
                    store_root=str(scoped),
                    character_id=CHARACTER,
                    namespace=NAMESPACE,
                    memory_id=concurrent_id,
                    expected_revision=1,
                    operation_id=operation_id,
                    apply_token=token,
                )
            except PrimaryCorrectionError as error:
                return "error", error.code
            return "success", str(result["result_revision"])

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(
                executor.map(
                    lambda args: apply_concurrent(*args),
                    (("concurrent-a", str(token_a)), ("concurrent-b", str(token_b))),
                )
            )
        require(sum(kind == "success" for kind, _ in outcomes) == 1, outcomes)
        require(
            sum(code in {"stale_revision", "operation_conflict"} for kind, code in outcomes if kind == "error") == 1,
            outcomes,
        )
        history = list_primary_memory_corrections(
            store_root=str(scoped), namespace=NAMESPACE, memory_id=concurrent_id
        )
        require(history["current_revision"] == 2, history)
        require(history["correction_count"] == 1, history)

    print("Phase I-3 Primary MEM Correct validation smoke passed")


if __name__ == "__main__":
    main()
