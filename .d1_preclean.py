from pathlib import Path

root = Path(__file__).resolve().parent
keep_workflow = root / ".github/workflows/d1-completion-model-retirement.yml"
for path in (root / ".github/workflows").glob("d1-*.yml"):
    if path.resolve() != keep_workflow.resolve():
        path.unlink()
for path in root.glob(".d1*"):
    if path.name not in {".d1_completion_model_retirement.py", ".d1_preclean.py"} and path.is_file():
        path.unlink()
