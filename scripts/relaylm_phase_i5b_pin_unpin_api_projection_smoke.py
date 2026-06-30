"""Phase I-5B Pin / Unpin API public projection smoke."""
from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from _relaylm_phase_i3_test_support import form_primary_memory, require, write_config
from relaylm.relaymem_primary_recall import resolve_relaymem_character_store_root
from relaylm.soul_lab_app import create_app
from relaylm_phase_i1_two_turn_primary_recall_smoke import CHARACTER, NAMESPACE

REPO_ROOT = Path(__file__).resolve().parents[1]
SUMMARY = "I5B_PIN_UNPIN_API_PROJECTION_CONTENT_CANARY"
PIN_REASON = "I5B_PIN_UNPIN_API_PIN_REASON_CANARY"
UNPIN_REASON = "I5B_PIN_UNPIN_API_UNPIN_REASON_CANARY"


PIN_EFFECT_KEYS = {
    "audit_evidence_retained",
    "future_priority_hint_contract",
    "ordinary_retrieval_deleted",
    "ordinary_retrieval_excluded",
    "physical_deletion",
    "semantic_content_changed",
}
UNPIN_EFFECT_KEYS = {
    "audit_evidence_retained",
    "future_priority_hint_removed_contract",
    "ordinary_retrieval_deleted",
    "ordinary_retrieval_excluded",
    "physical_deletion",
    "semantic_content_changed",
}


def preflight_body(kind: str, revision: int, operation_id: str) -> dict[str, object]:
    reason = PIN_REASON if kind == "pin" else UNPIN_REASON
    return {
        "schema": f"relaylm.lab.memory_{kind}_preflight_request.v0",
        "expected_revision": revision,
        "reason": reason,
        "operation_id": operation_id,
    }


def apply_body(kind: str, revision: int, operation_id: str, token: str) -> dict[str, object]:
    reason = PIN_REASON if kind == "pin" else UNPIN_REASON
    return {
        "schema": f"relaylm.lab.memory_{kind}_apply_request.v0",
        "expected_revision": revision,
        "reason": reason,
        "operation_id": operation_id,
        "apply_token": token,
    }


def assert_no_private_preflight_leak(text: str) -> None:
    for forbidden in (
        SUMMARY,
        PIN_REASON,
        UNPIN_REASON,
        "reason_digest",
        "token_digest",
        "current_physical_id",
        "store_root",
        "filesystem_path",
        "physical_id:",
    ):
        require(forbidden not in text, forbidden)


def assert_no_apply_token_leak(text: str, token: str) -> None:
    for forbidden in (token, "reason_digest", "token_digest", "current_physical_id", "store_root", "filesystem_path", "physical_id:"):
        require(forbidden not in text, forbidden)


def assert_preflight_projection(value: dict[str, object], *, kind: str, memory_id: str, revision: int) -> str:
    expected_target = "pinned" if kind == "pin" else "unpinned"
    expected_current = "unpinned" if kind == "pin" else "pinned"
    hint_key = "future_priority_hint_contract" if kind == "pin" else "future_priority_hint_removed_contract"
    forbidden_hint_key = "future_priority_hint_removed_contract" if kind == "pin" else "future_priority_hint_contract"
    expected_effect_keys = PIN_EFFECT_KEYS if kind == "pin" else UNPIN_EFFECT_KEYS

    require(value["schema"] == f"relaylm.lab.memory_{kind}_preflight.v0", value)
    require(value["status"] == "ready", value)
    require(value["operation_kind"] == kind, value)
    require(value["read_only"] is True, value)
    require(value["memory_id"] == memory_id, value)
    require(value["current_revision"] == revision, value)
    require(value["current_lifecycle_state"] == "active", value)
    require(value["current_mutation_state"] == "none", value)
    require(value["current_pin_state"] == expected_current, value)
    require(value["target_pin_state"] == expected_target, value)
    require(value["pin_state_contract_only"] is False, value)

    effects = value["effects"]
    require(isinstance(effects, dict), value)
    require(set(effects) == expected_effect_keys, effects)
    require(effects["audit_evidence_retained"] is True, effects)
    require(effects[hint_key] is True, effects)
    require(forbidden_hint_key not in effects, effects)
    require(effects["ordinary_retrieval_deleted"] is False, effects)
    require(effects["ordinary_retrieval_excluded"] is False, effects)
    require(effects["physical_deletion"] is False, effects)
    require(effects["semantic_content_changed"] is False, effects)

    token = value["apply_token"]
    require(isinstance(token, str) and token, value)
    require(isinstance(value["expires_at"], str) and value["expires_at"], value)
    return token


def assert_apply_projection(value: dict[str, object], *, kind: str, memory_id: str, revision: int) -> None:
    expected_target = "pinned" if kind == "pin" else "unpinned"
    require(value["schema"] == f"relaylm.lab.memory_{kind}_apply.v0", value)
    require(value["status"] == "applied", value)
    require(value["operation_kind"] == kind, value)
    require(value["memory_id"] == memory_id, value)
    require(value["current_revision"] == revision, value)
    require(value["target_pin_state"] == expected_target, value)
    require(value["priority_hint_enabled"] is (kind == "pin"), value)
    require(value["content_included"] is False, value)
    require(value["path_included"] is False, value)
    require(value["physical_id_included"] is False, value)
    require(value["reason_included"] is False, value)
    require(value["token_included"] is False, value)


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
        memory_id = form_primary_memory(
            scoped,
            namespace=NAMESPACE,
            candidate_id="i5b-api-pin-unpin-projection",
            title="pin unpin projection target",
            summary=SUMMARY,
        )

        config_path = root / "config.yaml"
        write_config(config_path, port=9, queue=queue, protected=protected, store=store, enqueue_enabled=False)
        app = create_app(str(config_path))
        with TestClient(app, client=("127.0.0.1", 50000)) as client:
            query = f"?namespace={NAMESPACE}"
            base = f"/lab/api/characters/{CHARACTER}/memory/{memory_id}"

            pin_preflight = client.post(f"{base}/pin/preflight{query}", json=preflight_body("pin", 1, "i5b-api-pin"))
            require(pin_preflight.status_code == 200, pin_preflight.text)
            require(pin_preflight.headers["cache-control"] == "no-store", pin_preflight.headers)
            pin_token = assert_preflight_projection(pin_preflight.json(), kind="pin", memory_id=memory_id, revision=1)
            assert_no_private_preflight_leak(pin_preflight.text)

            pinned = client.post(f"{base}/pin{query}", json=apply_body("pin", 1, "i5b-api-pin", pin_token))
            require(pinned.status_code == 200, pinned.text)
            assert_apply_projection(pinned.json(), kind="pin", memory_id=memory_id, revision=1)
            assert_no_apply_token_leak(pinned.text, pin_token)

            unpin_preflight = client.post(f"{base}/unpin/preflight{query}", json=preflight_body("unpin", 1, "i5b-api-unpin"))
            require(unpin_preflight.status_code == 200, unpin_preflight.text)
            require(unpin_preflight.headers["cache-control"] == "no-store", unpin_preflight.headers)
            unpin_token = assert_preflight_projection(unpin_preflight.json(), kind="unpin", memory_id=memory_id, revision=1)
            assert_no_private_preflight_leak(unpin_preflight.text)

            unpinned = client.post(f"{base}/unpin{query}", json=apply_body("unpin", 1, "i5b-api-unpin", unpin_token))
            require(unpinned.status_code == 200, unpinned.text)
            assert_apply_projection(unpinned.json(), kind="unpin", memory_id=memory_id, revision=1)
            assert_no_apply_token_leak(unpinned.text, unpin_token)

    print("Phase I-5B Pin/Unpin API projection smoke passed")


if __name__ == "__main__":
    main()
