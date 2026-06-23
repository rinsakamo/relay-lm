from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / "docs/PROJECT_STATUS.md"
text = path.read_text(encoding="utf-8")
old = "  -> C2 one-job claim/rehydrate/execute adapter: complete\n  -> C1-0 protected source                      complete\n"
new = "  -> C2 one-job claim/rehydrate/execute adapter: complete\n  -> next-turn recall and scope isolation: next\n  -> C1-0 protected source                      complete\n"
if old not in text:
    raise SystemExit("PROJECT_STATUS Phase 6-C2 anchor not found")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
print("PROJECT_STATUS next-turn boundary aligned.")
