"""Temporary exact-source patch for M3e idempotent recovery acceptance."""
from pathlib import Path

path = Path("relaylm/relaymem_primary_correction.py")
body = path.read_text(encoding="utf-8")
old = '''    receipt = write_result.get("receipt")
    if not isinstance(receipt, Mapping) or write_result.get("durability_confirmed") is not True:
        raise PrimaryCorrectionError("store_unavailable")
'''
new = '''    receipt = write_result.get("receipt")
    publication_ready = isinstance(receipt, Mapping) and (
        write_result.get("durability_confirmed") is True
        or (
            write_result.get("status") == "already_applied"
            and write_result.get("idempotent_noop") is True
            and not write_result.get("blocked_reasons")
            and receipt.get("status") == "already_applied"
            and receipt.get("idempotent_noop") is True
        )
    )
    if not publication_ready:
        raise PrimaryCorrectionError("store_unavailable")
'''
if body.count(old) != 1:
    raise SystemExit("M3e publication acceptance block changed")
path.write_text(body.replace(old, new, 1), encoding="utf-8")
print("Phase I-3 M3e idempotent recovery acceptance patched")
