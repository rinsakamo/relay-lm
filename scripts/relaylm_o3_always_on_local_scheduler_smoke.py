#!/usr/bin/env python3
"""O3 always-on local scheduler CLI smoke."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "relaylm_o3_always_on_local_scheduler.py"

FORBIDDEN = (
    "job_id",
    "dispatch_idempotency_key",
    "lease_token",
    "claim_owner",
    "protected_source_body",
    "memory_content",
    "O3_PRIVATE_CANARY_68c872",
)


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _write_config(root: Path, *, invalid: bool = False) -> Path:
    path = root / ("invalid.yaml" if invalid else "config.yaml")
    body = """
backends:
  local:
    base_url: http://127.0.0.1:1234/v1
model_routes:
  relaylm-default:
    backend: local
"""
    if invalid:
        body += """
relaymem_local_scheduler_operational_controls_enabled: true
relaymem_local_scheduler_operational_controls_dry_run_only: true
relaymem_local_scheduler_operational_controls_apply_enabled: true
"""
    path.write_text(body.lstrip(), encoding="utf-8")
    return path


def _run(*args: str) -> tuple[int, dict[str, object], str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    stdout = completed.stdout.strip()
    require(stdout.startswith("{") and stdout.endswith("}"), (completed.returncode, stdout, completed.stderr))
    require(completed.stderr.strip() == "", completed.stderr)
    projection = json.loads(stdout)
    encoded = json.dumps(projection, ensure_ascii=True, sort_keys=True).lower()
    for token in FORBIDDEN:
        require(token.lower() not in encoded, encoded)
    return completed.returncode, projection, stdout


def main() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = _write_config(root)

        code, projection, stdout = _run("--config", str(config))
        require(code == 0, (code, stdout))
        require(projection["status"] == "disabled", projection)
        require(projection["rounds_attempted"] == 1, projection)

        code, projection, stdout = _run("--config", str(config), "--max-rounds", "1")
        require(code == 0, (code, stdout))
        require(projection["status"] == "disabled", projection)
        require(projection["rounds_attempted"] == 1, projection)

        code, projection, stdout = _run("--config", str(config), "--always-on")
        require(code == 0, (code, stdout))
        require(projection["status"] == "disabled", projection)
        require(projection["last_operational_status"] == "disabled", projection)

        invalid = _write_config(root, invalid=True)
        code, projection, stdout = _run("--config", str(invalid), "--max-rounds", "1")
        require(code != 0, (code, stdout))
        require(projection["status"] == "invalid_config", projection)
        require(projection["last_operational_status"] == "not_invoked", projection)

    print("O3 always-on local scheduler CLI smoke passed")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
