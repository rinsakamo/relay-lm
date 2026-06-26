from pathlib import Path

path = Path(__file__).resolve().parents[1] / "scripts/relaylm_documentation_current_boundary_smoke.py"
body = path.read_text(encoding="utf-8")
old = '        "O1C is complete as one bounded production queue-lane adapter",\n'
new = '        "O1B and O1C are complete as bounded production lane adapters",\n'
if body.count(old) < 2:
    raise SystemExit("expected O1A and O1C documentation anchors not found")
path.write_text(body.replace(old, new, 1), encoding="utf-8")
print("combined O1A documentation anchor updated")
