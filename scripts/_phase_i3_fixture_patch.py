"""Temporary exact-source correction for the Phase I-3 functional query fixture."""
from pathlib import Path

path = Path("scripts/relaylm_phase_i3_primary_mem_correct_smoke.py")
body = path.read_text(encoding="utf-8")
old = 'QUESTION = "好きな飲み物を教えてください。"'
new = 'QUESTION = "好きな飲み物 を教えてください。"'
if body.count(old) != 1:
    raise SystemExit("Phase I-3 functional question shape changed")
path.write_text(body.replace(old, new, 1), encoding="utf-8")
print("Phase I-3 functional query fixture corrected")
