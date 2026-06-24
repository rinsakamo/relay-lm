"""Remove the obsolete post-M3g synthetic index fault hook."""
from pathlib import Path

path = Path("relaylm/relaymem_primary_correction.py")
body = path.read_text(encoding="utf-8")
old = '''    if fault_at == "after_index_apply":
        raise PrimaryCorrectionError("reconciliation_required")
'''
if body.count(old) != 1:
    raise SystemExit("synthetic index fault hook changed")
path.write_text(body.replace(old, "", 1), encoding="utf-8")
print("obsolete synthetic index fault hook removed")
