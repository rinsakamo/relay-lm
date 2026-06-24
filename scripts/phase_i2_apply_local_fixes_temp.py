from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = "scripts/phase_i2_apply_local_fixes_temp.py"


def load_previous_implementation() -> dict[str, Any]:
    source = subprocess.check_output(
        ("git", "show", f"HEAD^:{SCRIPT_PATH}"), cwd=ROOT, text=True
    )
    namespace: dict[str, Any] = {
        "__name__": "phase_i2_final_implementation",
        "__file__": str(ROOT / SCRIPT_PATH),
    }
    exec(compile(source, SCRIPT_PATH, "exec"), namespace)
    return namespace


def main() -> None:
    impl = load_previous_implementation()
    run = impl["run"]

    run("git", "config", "user.name", "github-actions")
    run("git", "config", "user.email", "actions@github.com")
    try:
        run("git", "fetch", "--unshallow", "origin")
    except subprocess.CalledProcessError:
        run("git", "fetch", "origin")
    run("git", "fetch", "origin", "main")
    run("git", "merge", "--no-ff", "--no-edit", "-X", "ours", "origin/main")

    impl["harden_observation_code"]()
    impl["reconcile_documents"]()
    impl["cleanup"]()

    run("git", "add", "-A")
    if subprocess.run(("git", "diff", "--cached", "--quiet"), cwd=ROOT).returncode != 0:
        run("git", "commit", "-m", "fix: finalize Phase I2 observation integration")
    run("git", "push", "origin", "HEAD:phase-i2-real-soul-lab-observation")

    print("Phase I-2 branch reconciliation pushed; starting final validation", flush=True)
    impl["validate"]()
    print("Phase I-2 final validation passed", flush=True)


if __name__ == "__main__":
    main()
