from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = ".:scripts"
    completed = subprocess.run(
        ("python", "scripts/relaylm_phase_i2_lab_observation_ci_runner.py"),
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output = ROOT / "phase_i2_test_output_temp.txt"
    output.write_text(completed.stdout, encoding="utf-8")
    subprocess.run(("git", "config", "user.name", "github-actions"), cwd=ROOT, check=True)
    subprocess.run(("git", "config", "user.email", "actions@github.com"), cwd=ROOT, check=True)
    subprocess.run(("git", "add", str(output.relative_to(ROOT))), cwd=ROOT, check=True)
    subprocess.run(("git", "commit", "-m", "chore: capture Phase I2 runner output"), cwd=ROOT, check=True)
    subprocess.run(
        ("git", "push", "origin", "HEAD:phase-i2-real-soul-lab-observation"),
        cwd=ROOT,
        check=True,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
