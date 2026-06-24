#!/usr/bin/env python3
from pathlib import Path

path = Path("relaylm/relaymem_primary_recall.py")
body = path.read_text(encoding="utf-8")
old = '''        if store_reason == "memory_store_disabled":
            return store_reason
'''
new = '''        if (
            store_reason == "memory_store_disabled"
            and artifact_reason == "memory_store_not_configured"
        ):
            return store_reason
'''
if body.count(old) != 1:
    raise SystemExit(f"expected one projection reason precedence anchor, got {body.count(old)}")
path.write_text(body.replace(old, new, 1), encoding="utf-8")
