#!/usr/bin/env python3
from pathlib import Path

path = Path("scripts/relaylm_i4c1_handoff_cutover_guard.py")
text = path.read_text(encoding="utf-8")
old = '    r"(?![A-Za-z0-9_.-])"\n'
new = '    r"(?![A-Za-z0-9_-])"\n'
if text.count(old) != 1:
    raise SystemExit(f"expected one trailing-boundary pattern, found {text.count(old)}")
path.write_text(text.replace(old, new), encoding="utf-8")
