"""One-shot I-4C2 scanner split: governance chain vs ordinary M2 projection."""
from pathlib import Path

PATH = Path("relaylm/_relaymem_primary_current_state_impl.py")
body = PATH.read_text(encoding="utf-8")

replacements = (
    (
'''        applied.sort(key=lambda item: (int(item["result_revision"]), str(item["operation_key"])))
        prior_physical = logical
        prior_revision = 1
        seen_operations: set[str] = set()
        seen_operation_ids: set[str] = set()
        chain_ok = True
        for item in applied:
            operation_key = str(item["operation_key"])
            operation_id = str(item["operation_id"])
            if (
                operation_key in seen_operations
                or operation_id in seen_operation_ids
                or int(item["prior_revision"]) != prior_revision
                or int(item["result_revision"]) != prior_revision + 1
                or item["prior_physical_id"] != prior_physical
            ):
                chain_ok = False
                break
            seen_operations.add(operation_key)
            seen_operation_ids.add(operation_id)
            superseded.add(prior_physical)
            logical_by_physical[prior_physical] = logical
            prior_physical = str(item["result_physical_id"])
            logical_by_physical[prior_physical] = logical
            prior_revision += 1
''',
'''        applied.sort(key=lambda item: (int(item["result_revision"]), str(item["operation_key"])))
        governance_prior_physical = logical
        governance_prior_revision = 1
        seen_operations: set[str] = set()
        seen_operation_ids: set[str] = set()
        chain_ok = True
        terminal_hidden = False
        for item in applied:
            operation_key = str(item["operation_key"])
            operation_id = str(item["operation_id"])
            is_forget_tombstone = (
                item.get("schema_version") == "relaylm.mem.forget_tombstone.v0"
            )
            if (
                terminal_hidden
                or operation_key in seen_operations
                or operation_id in seen_operation_ids
                or int(item["prior_revision"]) != governance_prior_revision
                or int(item["result_revision"]) != governance_prior_revision + 1
                or item["prior_physical_id"] != governance_prior_physical
            ):
                chain_ok = False
                break
            seen_operations.add(operation_key)
            seen_operation_ids.add(operation_id)
            logical_by_physical[governance_prior_physical] = logical
            governance_prior_physical = str(item["result_physical_id"])
            logical_by_physical[governance_prior_physical] = logical
            governance_prior_revision += 1
            terminal_hidden = is_forget_tombstone
''',
    ),
    (
'''                pending.get("prior_physical_id") != prior_physical
                or pending.get("prior_revision") != prior_revision
                or pending.get("result_revision") != prior_revision + 1
''',
'''                pending.get("prior_physical_id") != governance_prior_physical
                or pending.get("prior_revision") != governance_prior_revision
                or pending.get("result_revision") != governance_prior_revision + 1
''',
    ),
    (
'''        current[logical] = (prior_physical, prior_revision)
        logical_by_physical.setdefault(logical, logical)
        receipts_by_logical[logical] = tuple(correction_applied)
''',
'''        # The combined chain above is governance/fence authority. Ordinary M2
        # currentness remains correction-only until Phase I-4D owns lifecycle
        # exclusion. A finalized Forget tombstone must not silently advance the
        # correction projection or supersede the last active physical page here.
        retrieval_physical = logical
        retrieval_revision = 1
        correction_applied.sort(
            key=lambda item: (int(item["result_revision"]), str(item["operation_key"]))
        )
        for item in correction_applied:
            superseded.add(retrieval_physical)
            logical_by_physical[retrieval_physical] = logical
            retrieval_physical = str(item["result_physical_id"])
            logical_by_physical[retrieval_physical] = logical
            retrieval_revision += 1
        current[logical] = (retrieval_physical, retrieval_revision)
        logical_by_physical.setdefault(logical, logical)
        receipts_by_logical[logical] = tuple(correction_applied)
''',
    ),
)
for old, new in replacements:
    if old not in body:
        if new in body:
            continue
        raise RuntimeError("unexpected I-4C2 current-state scanner drift")
    if body.count(old) != 1:
        raise RuntimeError("ambiguous I-4C2 current-state scanner text")
    body = body.replace(old, new)
PATH.write_text(body, encoding="utf-8")
