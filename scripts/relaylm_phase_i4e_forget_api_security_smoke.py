"""Phase I-4E loopback Forget API schema, scope, and leakage security smoke."""
from __future__ import annotations

import tempfile
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from _relaylm_phase_i3_test_support import form_primary_memory, require, write_config
import relaylm.soul_lab_app as lab_app_module
from relaylm._relaymem_primary_forget_impl import PrimaryForgetError
from relaylm.relaymem_primary_recall import resolve_relaymem_character_store_root
from relaylm.soul_lab_app import create_app
from relaylm_phase_i1_two_turn_primary_recall_smoke import (
    CHARACTER,
    NAMESPACE,
    OTHER_CHARACTER,
    OTHER_NAMESPACE,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SUMMARY = "I4E_SECURITY_MEMORY_CONTENT_CANARY"
REASON = "I4E_SECURITY_REASON_CANARY"


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


def assert_bounded(text: str, *tokens: str) -> None:
    for forbidden in (
        SUMMARY,
        REASON,
        "reason_digest",
        "token_digest",
        "physical_id",
        "store_root",
        "filesystem_path",
        "traceback",
        "tombstone_content",
        "raw_tombstone",
        *tokens,
    ):
        if forbidden:
            require(forbidden not in text, forbidden)


def main() -> None:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
        root = Path(directory)
        queue = root / "queue"; protected = root / "protected"; store = root / "store"
        queue.mkdir(); protected.mkdir(); store.mkdir()
        scoped_value = resolve_relaymem_character_store_root(str(store), CHARACTER)
        other_value = resolve_relaymem_character_store_root(str(store), OTHER_CHARACTER)
        require(scoped_value is not None and other_value is not None, "scope")
        scoped = Path(scoped_value)
        memory_a = form_primary_memory(scoped, namespace=NAMESPACE, candidate_id="i4e-security-a", title="A", summary=SUMMARY)
        memory_b = form_primary_memory(scoped, namespace=NAMESPACE, candidate_id="i4e-security-b", title="B", summary="safe B")

        config_path = root / "config.yaml"
        write_config(config_path, port=9, queue=queue, protected=protected, store=store, enqueue_enabled=False)
        app = create_app(str(config_path))
        with TestClient(app, client=("127.0.0.1", 50000)) as client:
            base = f"/lab/api/characters/{CHARACTER}/memory/{memory_a}"
            query = f"?namespace={NAMESPACE}"
            valid = client.post(f"{base}/forget/preflight{query}", json=preflight_body(1, "security-valid"))
            require(valid.status_code == 200, valid.text)
            require(valid.headers["cache-control"] == "no-store", valid.headers)
            require("access-control-allow-origin" not in valid.headers, valid.headers)
            token = valid.json()["apply_token"]
            assert_bounded(valid.text)

            missing_schema = preflight_body(1, "missing-schema")
            del missing_schema["schema"]
            response = client.post(f"{base}/forget/preflight{query}", json=missing_schema)
            require(response.status_code == 422, response.text)
            require(response.json() == {"detail": "invalid_request"}, response.json())

            unexpected = preflight_body(1, "unexpected")
            unexpected["filesystem_path"] = "/tmp/secret"
            response = client.post(f"{base}/forget/preflight{query}", json=unexpected)
            require(response.status_code == 422, response.text)
            require("/tmp/secret" not in response.text, response.text)

            form = client.post(f"{base}/forget/preflight{query}", data={"schema": "relaylm.lab.memory_forget_preflight_request.v0"})
            require(form.status_code == 415, form.text)
            huge = preflight_body(1, "huge")
            huge["reason"] = "x" * 20000
            too_large = client.post(f"{base}/forget/preflight{query}", json=huge)
            require(too_large.status_code in {422, 413}, too_large.text)
            require(client.get(f"{base}/forget{query}").status_code == 405, "GET mutation")

            no_token = client.post(f"{base}/forget{query}", json={
                "schema": "relaylm.lab.memory_forget_apply_request.v0",
                "expected_revision": 1,
                "expected_lifecycle_state": "active",
                "reason": REASON,
                "operation_id": "security-valid",
            })
            require(no_token.status_code == 422, no_token.text)
            assert_bounded(no_token.text, token)

            wrong_operation = client.post(f"{base}/forget{query}", json=apply_body(1, "different-operation", token))
            require(wrong_operation.status_code == 403, wrong_operation.text)
            wrong_memory = client.post(
                f"/lab/api/characters/{CHARACTER}/memory/{memory_b}/forget{query}",
                json=apply_body(1, "security-valid", token),
            )
            require(wrong_memory.status_code == 403, wrong_memory.text)
            wrong_character = client.post(
                f"/lab/api/characters/{OTHER_CHARACTER}/memory/{memory_a}/forget/preflight{query}",
                json=preflight_body(1, "wrong-character"),
            )
            require(wrong_character.status_code == 404, wrong_character.text)
            wrong_namespace = client.post(f"{base}/forget/preflight?namespace={OTHER_NAMESPACE}", json=preflight_body(1, "wrong-namespace"))
            require(wrong_namespace.status_code == 404, wrong_namespace.text)

            original_apply = lab_app_module.apply_primary_memory_forget
            def expired_apply(**kwargs):  # type: ignore[no-untyped-def]
                raise PrimaryForgetError("token_expired")
            lab_app_module.apply_primary_memory_forget = expired_apply
            try:
                expired = client.post(f"{base}/forget{query}", json=apply_body(1, "security-valid", token))
            finally:
                lab_app_module.apply_primary_memory_forget = original_apply
            require(expired.status_code == 409, expired.text)
            require(expired.json() == {"detail": "token_expired"}, expired.json())
            assert_bounded(expired.text, token)

            applied = client.post(f"{base}/forget{query}", json=apply_body(1, "security-valid", token))
            require(applied.status_code == 200, applied.text)
            assert_bounded(applied.text, token)
            history = client.get(f"{base}/forget-history{query}")
            require(history.status_code == 200, history.text)
            assert_bounded(history.text, token)
            hidden_preflight = client.post(f"{base}/forget/preflight{query}", json=preflight_body(2, "hidden-preflight"))
            require(hidden_preflight.status_code == 409, hidden_preflight.text)
            require(hidden_preflight.json()["detail"] in {"target_not_active", "already_hidden", "stale_revision"}, hidden_preflight.json())

        remote = TestClient(app, client=("192.0.2.10", 50000))
        spoofed = remote.post(
            f"/lab/api/characters/{CHARACTER}/memory/{memory_a}/forget/preflight?namespace={NAMESPACE}",
            json=preflight_body(2, "spoofed"),
            headers={"Host": "127.0.0.1", "Origin": "http://127.0.0.1", "X-Forwarded-For": "127.0.0.1"},
        )
        require(spoofed.status_code == 403, spoofed.text)

        remote_raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        remote_raw["listen"] = {"host": "0.0.0.0", "port": 8090}
        remote_path = root / "remote.yaml"
        remote_path.write_text(yaml.safe_dump(remote_raw, sort_keys=False), encoding="utf-8")
        remote_app = create_app(str(remote_path))
        with TestClient(remote_app, client=("127.0.0.1", 50000)) as client:
            refused = client.post(
                f"/lab/api/characters/{CHARACTER}/memory/{memory_a}/forget/preflight?namespace={NAMESPACE}",
                json=preflight_body(2, "remote-config"),
            )
            require(refused.status_code == 403, refused.text)

    print("Phase I-4E Forget API security smoke passed")


if __name__ == "__main__":
    main()
