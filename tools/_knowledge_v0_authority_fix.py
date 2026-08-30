from pathlib import Path

path = Path(".ai/authority/knowledge.yaml")
text = path.read_text(encoding="utf-8")
old = "qualification_inputs:\n- docs/reference/knowledge.md\n- docs/reference/character-directory.md\n- src/relaylm/knowledge.py\n"
new = "qualification_inputs:\n- docs/reference/knowledge.md\n- src/relaylm/knowledge.py\n"
count = text.count(old)
if count != 1:
    raise RuntimeError(f"expected one qualification-input ownership match, found {count}")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
