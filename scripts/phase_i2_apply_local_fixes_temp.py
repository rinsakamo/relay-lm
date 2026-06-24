from __future__ import annotations

import subprocess
import traceback
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = "scripts/phase_i2_apply_local_fixes_temp.py"
IMPLEMENTATION_COMMIT = "39b39a9017965303d1bbf14e6d610392d761655e"


def load_implementation() -> dict[str, Any]:
    unshallow = subprocess.run(("git", "fetch", "--unshallow", "origin"), cwd=ROOT)
    if unshallow.returncode != 0:
        subprocess.run(("git", "fetch", "origin"), cwd=ROOT, check=True)
    source = subprocess.check_output(
        ("git", "show", f"{IMPLEMENTATION_COMMIT}:{SCRIPT_PATH}"),
        cwd=ROOT,
        text=True,
    )
    source = source.replace(
        '    write(path, read(path).replace("{mockCharacters.map((character) => (", "{characters.map((character) => (")\n',
        '    write(path, read(path).replace("{mockCharacters.map((character) => (", "{characters.map((character) => ("))\n',
    )
    namespace: dict[str, Any] = {
        "__name__": "phase_i2_validation_implementation",
        "__file__": str(ROOT / SCRIPT_PATH),
    }
    exec(compile(source, SCRIPT_PATH, "exec"), namespace)
    return namespace


def push_diagnostic(detail: str) -> None:
    diagnostic = ROOT / "phase_i2_patch_failure_temp.txt"
    diagnostic.write_text(detail, encoding="utf-8")
    subprocess.run(("git", "config", "user.name", "github-actions"), cwd=ROOT, check=False)
    subprocess.run(("git", "config", "user.email", "actions@github.com"), cwd=ROOT, check=False)
    subprocess.run(("git", "add", str(diagnostic.relative_to(ROOT))), cwd=ROOT, check=False)
    subprocess.run(("git", "commit", "-m", "chore: capture Phase I2 patch failure"), cwd=ROOT, check=False)
    subprocess.run(
        ("git", "push", "origin", "HEAD:phase-i2-real-soul-lab-observation"),
        cwd=ROOT,
        check=False,
    )


def main() -> None:
    try:
        (ROOT / "phase_i2_patch_failure_temp.txt").unlink(missing_ok=True)
        load_implementation()["main"]()
    except BaseException:
        detail = traceback.format_exc()
        print(detail, flush=True)
        push_diagnostic(detail)
        raise


if __name__ == "__main__":
    main()
