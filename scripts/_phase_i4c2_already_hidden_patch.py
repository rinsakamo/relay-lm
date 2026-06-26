"""One-shot I-4C2 finalized-hidden mapping fix."""
from pathlib import Path

PATH = Path("relaylm/relaymem_primary_forget_recovery.py")
OLD = '            if exc.code in {"target_not_active", "operation_conflict"}:\n'
NEW = '            if exc.code in {"target_not_active", "operation_conflict", "stale_revision"}:\n'

body = PATH.read_text(encoding="utf-8")
if body.count(OLD) != 1:
    raise RuntimeError("unexpected I-4C2 recovery drift")
PATH.write_text(body.replace(OLD, NEW), encoding="utf-8")
