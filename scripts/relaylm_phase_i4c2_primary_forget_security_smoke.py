"""I-4C2 tombstone security, strict JSON, path, and error leakage smoke."""
from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from _relaylm_phase_i4b_test_support import CHARACTER, NAMESPACE, prepared_store, require
from relaylm.relaymem_primary_current_state import resolve_primary_current_state
from relaylm.relaymem_primary_forget import (
    PrimaryForgetError,
    apply_primary_memory_forget,
    preflight_primary_memory_forget,
    recover_primary_memory_forget,
)

NOW = datetime(2026, 6, 26, 0, 0, tzinfo=timezone.utc)
REASON = "I4C2_SECURITY_REASON_CANARY"
OPERATION = "phase-i4c2-security"


@contextmanager
def finalized_store() -> Iterator[tuple[Path, str, str, Path]]:
    with prepared_store() as (root, memory_id):
        token = str(
            preflight_primary_memory_forget(
                store_root=str(root),
                character_id=CHARACTER,
                namespace=NAMESPACE,
                memory_id=memory_id,
                expected_revision=1,
                expected_lifecycle_state="active",
                reason=REASON,
                operation_id=OPERATION,
                now=NOW,
            )["apply_token"]
        )
        result = apply_primary_memory_forget(
            store_root=str(root),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            expected_lifecycle_state="active",
            reason=REASON,
            operation_id=OPERATION,
            apply_token=token,
            now=NOW,
        )
        require(result.status == "applied", result)
        mutation_dir = root / "memory/mem/corrections/v0" / memory_id
        tombstones = list(mutation_dir.glob("*.tombstone.json"))
        require(len(tombstones) == 1, tombstones)
        yield root, memory_id, token, tombstones[0]


def require_corrupt(root: Path, memory_id: str) -> None:
    state = resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=memory_id)
    require(state.mutation_state == "corrupt", state)
    require(state.retrieval_eligible is False, state)
    try:
        recover_primary_memory_forget(
            store_root=str(root),
            namespace=NAMESPACE,
            memory_id=memory_id,
            operation_id=OPERATION,
            now=NOW,
        )
    except PrimaryForgetError as exc:
        require(exc.code == "target_corrupt", exc.code)
        require(str(exc) == "target_corrupt", str(exc))
        require(str(root) not in str(exc), str(exc))
    else:
        raise AssertionError("corrupt tombstone was accepted")


def rewrite(path: Path, payload: bytes) -> None:
    path.write_bytes(payload)


def tombstone_symlink() -> None:
    with finalized_store() as (root, memory_id, _token, path):
        copy = root / "tombstone-copy.json"
        copy.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(copy)
        require_corrupt(root, memory_id)


def tombstone_hardlink() -> None:
    with finalized_store() as (root, memory_id, _token, path):
        os.link(path, path.with_name("tombstone-hardlink-alias.json"))
        require_corrupt(root, memory_id)


def malformed_payloads() -> None:
    mutations = {
        "noncanonical": lambda raw: json.dumps(json.loads(raw), ensure_ascii=False, indent=2).encode("utf-8"),
        "duplicate": lambda raw: b'{"schema_version":"duplicate",' + raw.lstrip()[1:],
        "invalid_utf8": lambda _raw: b"\xff\xfe\x00",
        "oversized": lambda _raw: b"{" + b"x" * 40_000 + b"}",
        "unknown_field": lambda raw: _canonical_with_unknown(raw),
    }
    for name, transform in mutations.items():
        with finalized_store() as (root, memory_id, _token, path):
            raw = path.read_bytes()
            rewrite(path, transform(raw))
            require_corrupt(root, memory_id)
            require(name not in repr(resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=memory_id)), name)


def _canonical_with_unknown(raw: bytes) -> bytes:
    value = json.loads(raw.decode("utf-8"))
    value["unknown_field"] = "not-allowed"
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def wrong_scope_and_path() -> None:
    with finalized_store() as (root, memory_id, token, _path):
        codes = []
        for character_id, namespace in (
            (CHARACTER + "-wrong", NAMESPACE),
            (CHARACTER, NAMESPACE + "-wrong"),
        ):
            try:
                apply_primary_memory_forget(
                    store_root=str(root),
                    character_id=character_id,
                    namespace=namespace,
                    memory_id=memory_id,
                    expected_revision=1,
                    expected_lifecycle_state="active",
                    reason=REASON,
                    operation_id=OPERATION,
                    apply_token=token,
                    now=NOW,
                )
            except PrimaryForgetError as exc:
                codes.append(exc.code)
            else:
                raise AssertionError("wrong scope replay accepted")
        require(codes == ["operation_conflict", "operation_conflict"], codes)

        try:
            recover_primary_memory_forget(
                store_root=str(root),
                namespace=NAMESPACE,
                memory_id="../escape",
                operation_id=OPERATION,
                now=NOW,
            )
        except PrimaryForgetError as exc:
            require(exc.code == "target_not_found", exc.code)
        else:
            raise AssertionError("path escape accepted")


def mutation_dir_symlink() -> None:
    with prepared_store() as (root, memory_id):
        correction_root = root / "memory/mem/corrections/v0"
        correction_root.mkdir(parents=True, exist_ok=True)
        target = root / "outside-mutation-dir"
        target.mkdir()
        (correction_root / memory_id).symlink_to(target, target_is_directory=True)
        try:
            recover_primary_memory_forget(
                store_root=str(root),
                namespace=NAMESPACE,
                memory_id=memory_id,
                operation_id=OPERATION,
                now=NOW,
            )
        except PrimaryForgetError as exc:
            require(exc.code == "target_corrupt", exc.code)
        else:
            raise AssertionError("symlinked mutation directory accepted")


def main() -> None:
    tombstone_symlink()
    tombstone_hardlink()
    malformed_payloads()
    wrong_scope_and_path()
    mutation_dir_symlink()
    print("Phase I-4C2 Primary Forget security smoke passed")


if __name__ == "__main__":
    main()
