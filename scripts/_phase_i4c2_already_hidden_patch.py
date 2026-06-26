"""One-shot I-4C2 finalized-hidden and applied timestamp fixes."""
from pathlib import Path

PATH = Path("relaylm/relaymem_primary_forget_recovery.py")
body = PATH.read_text(encoding="utf-8")

replacements = (
    (
        '            if exc.code in {"target_not_active", "operation_conflict"}:\n',
        '            if exc.code in {"target_not_active", "operation_conflict", "stale_revision"}:\n',
    ),
    (
        '''    # The final timestamp is derived from already-durable prepare evidence so an\n    # ambiguous tombstone publication can be rebuilt byte-for-byte on restart.\n    # It is audit metadata, never identity authority.\n    del now\n    tombstone = build_forget_tombstone(\n        prepared=prepared,\n        result_canonical_digest=str(prepared["successor_expected_canonical_digest"]),\n        applied_at=str(prepared["prepared_at"]),\n    )\n''',
        '''    # The timestamp is audit metadata, never identity authority. An ambiguous\n    # publication is resolved by rereading the no-clobber path before rebuilding.\n    tombstone = build_forget_tombstone(\n        prepared=prepared,\n        result_canonical_digest=str(prepared["successor_expected_canonical_digest"]),\n        applied_at=_iso(_utc(now)),\n    )\n''',
    ),
)
for old, new in replacements:
    if body.count(old) != 1:
        raise RuntimeError("unexpected I-4C2 recovery drift")
    body = body.replace(old, new)
PATH.write_text(body, encoding="utf-8")
