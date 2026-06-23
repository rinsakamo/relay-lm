"""Sanitized CI runner for the Phase 6-C1-2 worker smokes."""
from __future__ import annotations

import runpy
import traceback
from pathlib import Path

SMOKES = (
    "scripts/relaylm_phase6c1_primary_worker_smoke.py",
    "scripts/relaylm_phase6c1_primary_worker_security_smoke.py",
    "scripts/relaylm_phase6c1_primary_worker_fault_smoke.py",
)
DIAGNOSTIC = Path("phase6c1-primary-worker-diagnostic.txt")


def main() -> int:
    for smoke in SMOKES:
        try:
            runpy.run_path(smoke, run_name="__main__")
        except SystemExit as exc:
            if exc.code in (None, 0):
                continue
            _write_diagnostic(smoke, exc)
            return 1
        except BaseException as exc:
            _write_diagnostic(smoke, exc)
            return 1
    return 0


def _write_diagnostic(smoke: str, exc: BaseException) -> None:
    frames = traceback.extract_tb(exc.__traceback__)
    lines = [
        f"smoke={Path(smoke).name}",
        f"exception_type={type(exc).__name__}",
    ]
    lines.extend(
        f"frame={Path(frame.filename).name}:{frame.lineno}:{frame.name}"
        for frame in frames[-10:]
    )
    DIAGNOSTIC.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
