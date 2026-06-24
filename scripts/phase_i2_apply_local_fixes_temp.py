from __future__ import annotations

import subprocess
import traceback
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = "scripts/phase_i2_apply_local_fixes_temp.py"
IMPLEMENTATION_COMMIT = "2bf35e3bffc31243c41a5e8d736eaeca2eabd36e"


def bootstrap_history() -> None:
    subprocess.run(("git", "config", "user.name", "github-actions"), cwd=ROOT, check=True)
    subprocess.run(("git", "config", "user.email", "actions@github.com"), cwd=ROOT, check=True)
    unshallow = subprocess.run(("git", "fetch", "--unshallow", "origin"), cwd=ROOT)
    if unshallow.returncode != 0:
        subprocess.run(("git", "fetch", "origin"), cwd=ROOT, check=True)
    subprocess.run(("git", "fetch", "origin", "main"), cwd=ROOT, check=True)


def load_implementation() -> dict[str, Any]:
    source = subprocess.check_output(
        ("git", "show", f"{IMPLEMENTATION_COMMIT}:{SCRIPT_PATH}"),
        cwd=ROOT,
        text=True,
    )
    namespace: dict[str, Any] = {
        "__name__": "phase_i2_final_implementation",
        "__file__": str(ROOT / SCRIPT_PATH),
    }
    exec(compile(source, SCRIPT_PATH, "exec"), namespace)
    return namespace


def push_diagnostic(detail: str) -> None:
    subprocess.run(("git", "merge", "--abort"), cwd=ROOT, check=False)
    diagnostic = ROOT / "phase_i2_failure_temp.txt"
    diagnostic.write_text(detail, encoding="utf-8")
    subprocess.run(("git", "config", "user.name", "github-actions"), cwd=ROOT, check=False)
    subprocess.run(("git", "config", "user.email", "actions@github.com"), cwd=ROOT, check=False)
    subprocess.run(("git", "add", str(diagnostic.relative_to(ROOT))), cwd=ROOT, check=False)
    subprocess.run(("git", "commit", "-m", "chore: capture Phase I2 reconcile failure"), cwd=ROOT, check=False)
    subprocess.run(
        ("git", "push", "origin", "HEAD:phase-i2-real-soul-lab-observation"),
        cwd=ROOT,
        check=False,
    )


def main() -> None:
    try:
        bootstrap_history()
        impl = load_implementation()
        run = impl["run"]
        run("git", "merge", "--no-ff", "--no-edit", "-X", "ours", "origin/main")

        impl["harden_observation_code"]()
        impl["reconcile_documents"]()
        impl["cleanup"]()
        (ROOT / "phase_i2_failure_temp.txt").unlink(missing_ok=True)

        run("git", "add", "-A")
        if subprocess.run(("git", "diff", "--cached", "--quiet"), cwd=ROOT).returncode != 0:
            run("git", "commit", "-m", "fix: finalize Phase I2 observation integration")
        run("git", "push", "origin", "HEAD:phase-i2-real-soul-lab-observation")

        print("Phase I-2 branch reconciliation pushed; starting final validation", flush=True)
        impl["validate"]()
        print("Phase I-2 final validation passed", flush=True)
    except Exception:
        detail = traceback.format_exc()
        print(detail, flush=True)
        push_diagnostic(detail)
        raise


if __name__ == "__main__":
    main()
