from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "apps" / "soul-lab"


def run(*args: str, cwd: Path = ROOT) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def main() -> None:
    run("npm", "install", "--no-audit", "--no-fund", "--package-lock=false", cwd=FRONTEND)
    run("npm", "run", "typecheck", cwd=FRONTEND)
    smoke_dir = FRONTEND / ".observation-smoke"
    shutil.rmtree(smoke_dir, ignore_errors=True)
    run(
        "npx", "tsc", "src/features/lab/observationApi.ts",
        "--target", "ES2022", "--module", "ES2022",
        "--moduleResolution", "Bundler", "--outDir", ".observation-smoke",
        "--skipLibCheck", cwd=FRONTEND,
    )
    run("node", "scripts/observationApiSmoke.mjs", cwd=FRONTEND)
    shutil.rmtree(smoke_dir, ignore_errors=True)
    run("npm", "run", "build", cwd=FRONTEND)
    if (FRONTEND / "package-lock.json").exists():
        raise RuntimeError("package-lock.json must not be generated")

    Path(__file__).unlink(missing_ok=True)
    run("git", "config", "user.name", "github-actions")
    run("git", "config", "user.email", "actions@github.com")
    run("git", "add", "-A")
    run("git", "commit", "-m", "test: verify lock-free SOUL Lab frontend")
    run("git", "push", "origin", "HEAD:phase-i2-real-soul-lab-observation")
    print("Phase I-2 lock-free frontend verification passed", flush=True)


if __name__ == "__main__":
    main()
