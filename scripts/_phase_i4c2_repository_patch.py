"""One-shot repository patch for I-4C2 scanner integration.

This script is executed once by a temporary branch-only workflow, then both the
script and workflow are removed in the same commit.  Exact replacement asserts
make drift fail closed.
"""
from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one replacement, found {count}")
    target.write_text(text.replace(old, new), encoding="utf-8")


def main() -> None:
    replace_once(
        "relaylm/relaymem_primary_forget_artifact.py",
        '''        elif schema == CORRECTION_PREPARED_SCHEMA:
''',
        '''        elif schema == "relaylm.mem.forget_tombstone.v0":
            from .relaymem_primary_forget_finalization_artifact import (
                validate_forget_tombstone,
            )

            if (
                not path.name.endswith(".tombstone.json")
                or not validate_forget_tombstone(value)
            ):
                corrupt = True
        elif schema == CORRECTION_PREPARED_SCHEMA:
''',
    )

    replace_once(
        "relaylm/relaymem_primary_mutation_coordinator.py",
        '''from .relaymem_primary_forget_artifact import (
    FORGET_PREPARED_SCHEMA,
    validate_forget_prepared,
)
''',
        '''from .relaymem_primary_forget_artifact import (
    FORGET_PREPARED_SCHEMA,
    validate_forget_prepared,
)
from .relaymem_primary_forget_finalization_artifact import (
    FORGET_TOMBSTONE_SCHEMA,
    validate_forget_tombstone,
)
''',
    )
    replace_once(
        "relaylm/relaymem_primary_mutation_coordinator.py",
        '''        expected_suffix = (
            ".prepared.json" if operation.state == "prepared" else ".applied.json"
        )
''',
        '''        expected_suffix = (
            ".prepared.json"
            if operation.state == "prepared"
            else ".tombstone.json"
            if operation.operation_kind == "forget"
            else ".applied.json"
        )
''',
    )
    replace_once(
        "relaylm/relaymem_primary_mutation_coordinator.py",
        '''    elif schema == FORGET_PREPARED_SCHEMA:
        if not validate_forget_prepared(value):
            return None
        kind = "forget"
        state = "prepared"
        binding = value.get("binding_digest")
    else:
        return None
''',
        '''    elif schema == FORGET_PREPARED_SCHEMA:
        if not validate_forget_prepared(value):
            return None
        kind = "forget"
        state = "prepared"
        binding = value.get("binding_digest")
    elif schema == FORGET_TOMBSTONE_SCHEMA:
        if not validate_forget_tombstone(value):
            return None
        kind = "forget"
        state = "applied"
        binding = value.get("binding_digest")
    else:
        return None
''',
    )

    replace_once(
        "relaylm/_relaymem_primary_current_state_impl.py",
        '''        prepared_by_operation: dict[str, dict[str, Any]] = {}
        applied: list[dict[str, Any]] = []
''',
        '''        prepared_by_operation: dict[str, dict[str, Any]] = {}
        applied: list[dict[str, Any]] = []
        correction_applied: list[dict[str, Any]] = []
''',
    )
    replace_once(
        "relaylm/_relaymem_primary_current_state_impl.py",
        '''            if path.name.endswith(".prepared.json"):
                value = _read_json(path)
                if not _valid_prepared(value, namespace=namespace, memory_id=logical):
                    invalid.add(logical)
                    continue
                operation_key = str(value["operation_key"])
                if operation_key in prepared_by_operation:
                    invalid.add(logical)
                    continue
                prepared_by_operation[operation_key] = value
            elif path.name.endswith(".applied.json"):
                value = _read_json(path)
                if not _valid_applied(value, namespace=namespace, memory_id=logical):
                    invalid.add(logical)
                    continue
                applied.append(value)
            else:
                invalid.add(logical)
''',
        '''            if path.name.endswith(".prepared.json"):
                value = _read_json(path)
                schema = value.get("schema_version") if isinstance(value, dict) else None
                if schema == CORRECTION_PREPARED_SCHEMA:
                    valid = _valid_prepared(
                        value, namespace=namespace, memory_id=logical
                    )
                elif schema == "relaylm.mem.forget_prepared.v0":
                    from .relaymem_primary_forget_artifact import (
                        validate_forget_prepared,
                    )

                    valid = validate_forget_prepared(value)
                    valid = bool(
                        valid
                        and value.get("namespace") == namespace
                        and value.get("memory_id") == logical
                    )
                else:
                    valid = False
                if not valid:
                    invalid.add(logical)
                    continue
                operation_key = str(value["operation_key"])
                if operation_key in prepared_by_operation:
                    invalid.add(logical)
                    continue
                prepared_by_operation[operation_key] = value
            elif path.name.endswith(".applied.json"):
                value = _read_json(path)
                if not _valid_applied(value, namespace=namespace, memory_id=logical):
                    invalid.add(logical)
                    continue
                applied.append(value)
                correction_applied.append(value)
            elif path.name.endswith(".tombstone.json"):
                value = _read_json(path)
                from .relaymem_primary_forget_finalization_artifact import (
                    validate_forget_tombstone,
                )

                if (
                    not validate_forget_tombstone(value)
                    or value.get("namespace") != namespace
                    or value.get("memory_id") != logical
                ):
                    invalid.add(logical)
                    continue
                applied.append(value)
            else:
                invalid.add(logical)
''',
    )
    replace_once(
        "relaylm/_relaymem_primary_current_state_impl.py",
        '''        receipts_by_logical[logical] = tuple(applied)
''',
        '''        receipts_by_logical[logical] = tuple(correction_applied)
''',
    )


if __name__ == "__main__":
    main()
