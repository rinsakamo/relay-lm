"""I-4C1 token binding, artifact integrity, and fail-closed security smoke."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

from _relaylm_phase_i4b_test_support import (
    CHARACTER,
    NAMESPACE,
    prepared_store,
    require,
)
from relaylm.relaymem_primary_current_state import resolve_primary_current_state
from relaylm.relaymem_primary_forget import (
    PrimaryForgetError,
    apply_primary_memory_forget_hidden_successor,
    preflight_primary_memory_forget,
)

NOW = datetime(2026, 6, 26, 0, 0, tzinfo=timezone.utc)
REASON = "通常検索から外すため"


def issue(root, memory_id, operation_id="phase-i4c1-security"):
    return preflight_primary_memory_forget(
        store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE,
        memory_id=memory_id, expected_revision=1,
        expected_lifecycle_state="active", reason=REASON,
        operation_id=operation_id, now=NOW,
    )["apply_token"]


def invoke(root, memory_id, token, **changes):
    values = {
        "store_root": str(root),
        "character_id": CHARACTER,
        "namespace": NAMESPACE,
        "memory_id": memory_id,
        "expected_revision": 1,
        "expected_lifecycle_state": "active",
        "reason": REASON,
        "operation_id": "phase-i4c1-security",
        "apply_token": token,
        "now": NOW,
    }
    values.update(changes)
    return apply_primary_memory_forget_hidden_successor(**values)


def expect(code, root, memory_id, token, **changes):
    try:
        invoke(root, memory_id, token, **changes)
    except PrimaryForgetError as exc:
        require(exc.code == code, (code, exc.code))
    else:
        raise AssertionError(f"expected {code}")


def token_binding() -> None:
    variants = [
        ("token_invalid", {"reason": "別の理由"}),
        ("token_invalid", {"character_id": CHARACTER + "-other"}),
        ("token_invalid", {"namespace": NAMESPACE + "-other"}),
        ("token_invalid", {"operation_id": "phase-i4c1-security-other"}),
        ("token_invalid", {"expected_revision": 2}),
        ("invalid_request", {"expected_lifecycle_state": "hidden"}),
    ]
    for code, changes in variants:
        with prepared_store() as (root, memory_id):
            token = issue(root, memory_id)
            expect(code, root, memory_id, token, **changes)
            state = resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=memory_id)
            require(state.current_revision == 1 and state.mutation_state == "none", state)

    with prepared_store() as (root, memory_id):
        token = issue(root, memory_id)
        expect("token_invalid", root, memory_id, token + "A")
        payload, signature = token.split(".")
        expect("token_invalid", root, memory_id, payload + "=." + signature)
        expect("token_invalid", root, memory_id, " " + token)
        expect("token_expired", root, memory_id, token, now=NOW + timedelta(minutes=5))


def corrupt_artifact() -> None:
    with prepared_store() as (root, memory_id):
        token = issue(root, memory_id)
        try:
            invoke(root, memory_id, token, fault_at="after_prepared_publication")
        except PrimaryForgetError as exc:
            require(exc.code == "reconciliation_required", exc.code)
        mutation_dir = root / "memory/mem/corrections/v0" / memory_id
        artifact = next(mutation_dir.glob("*.prepared.json"))
        value = json.loads(artifact.read_text(encoding="utf-8"))
        artifact.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        state = resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=memory_id)
        require(state.mutation_state == "corrupt", state)
        expect("target_corrupt", root, memory_id, token)

    with prepared_store() as (root, memory_id):
        token = issue(root, memory_id)
        try:
            invoke(root, memory_id, token, fault_at="after_prepared_publication")
        except PrimaryForgetError:
            pass
        artifact = next((root / "memory/mem/corrections/v0" / memory_id).glob("*.prepared.json"))
        raw = artifact.read_text(encoding="utf-8").rstrip("\n")
        artifact.write_text(raw[:-1] + ',"status":"prepared"}\n', encoding="utf-8")
        state = resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=memory_id)
        require(state.mutation_state == "corrupt", state)

    with prepared_store() as (root, memory_id):
        token = issue(root, memory_id)
        try:
            invoke(root, memory_id, token, fault_at="after_prepared_publication")
        except PrimaryForgetError:
            pass
        artifact = next((root / "memory/mem/corrections/v0" / memory_id).glob("*.prepared.json"))
        backup = artifact.with_suffix(".backup")
        artifact.rename(backup)
        artifact.symlink_to(backup.name)
        state = resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=memory_id)
        require(state.mutation_state == "corrupt", state)

    with prepared_store() as (root, memory_id):
        token = issue(root, memory_id)
        try:
            invoke(root, memory_id, token, fault_at="after_prepared_publication")
        except PrimaryForgetError:
            pass
        artifact = next((root / "memory/mem/corrections/v0" / memory_id).glob("*.prepared.json"))
        hardlink = artifact.with_name("extra.prepared.json")
        os.link(artifact, hardlink)
        state = resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=memory_id)
        require(state.mutation_state == "corrupt", state)


def corrupt_hidden_page() -> None:
    with prepared_store() as (root, memory_id):
        token = issue(root, memory_id)
        result = invoke(root, memory_id, token)
        require(result.lifecycle_state == "hidden", result)
        state = resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=memory_id)
        hidden = root / state.relative_path
        hidden.write_bytes(hidden.read_bytes().replace(b'"hidden"', b'"active"', 1))
        corrupt = resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=memory_id)
        require(corrupt.mutation_state == "corrupt", corrupt)
        require(corrupt.retrieval_eligible is False, corrupt)
        expect("target_corrupt", root, memory_id, token)


def main() -> None:
    token_binding()
    corrupt_artifact()
    corrupt_hidden_page()
    print("Phase I-4C1 Primary Forget security smoke passed")


if __name__ == "__main__":
    main()
