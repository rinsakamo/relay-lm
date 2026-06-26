from pathlib import Path

path = Path(__file__).resolve().parents[1] / "scripts/relaylm_documentation_current_boundary_smoke.py"
body = path.read_text(encoding="utf-8")
old = '        "O1C is complete as one bounded production queue-lane adapter",\n'
new = '        "O1B and O1C are complete as bounded production lane adapters",\n'
if old not in body:
    raise SystemExit("combined O1A documentation anchor not found")
path.write_text(body.replace(old, new), encoding="utf-8")
print("combined O1A documentation anchor updated")
